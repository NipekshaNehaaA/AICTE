import base64
import hashlib
import hmac
import os
import secrets
import struct
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
import io
import json
import pyotp
import qrcode
from cryptography.fernet import Fernet
from fastapi import Request, Header, HTTPException, status
import jwt
from app.config import settings
from app.scoped_dal import RequestContext

def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256 password hashing with random salt."""
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000
    ).hex()
    return f"{salt}${pw_hash}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verifies a plain password against stored salt$hash."""
    try:
        salt, expected_hash = stored_hash.split("$")
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256", plain_password.encode("utf-8"), salt.encode("utf-8"), 100000
        ).hex()
        return hmac.compare_digest(expected_hash, computed_hash)
    except Exception:
        return False

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None, workspace: Optional[str] = None) -> str:
    from app.workspace import current_workspace_var
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    token_type = to_encode.get("type", "access")
    ws = to_encode.get("ws") or workspace or current_workspace_var.get() or "live"
    to_encode.update({"exp": expire, "type": token_type, "ws": ws})
    if "token_version" not in to_encode:
        to_encode["token_version"] = 0
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: Dict[str, Any], workspace: Optional[str] = None) -> str:
    from app.workspace import current_workspace_var
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    ws = to_encode.get("ws") or workspace or current_workspace_var.get() or "live"
    to_encode.update({"exp": expire, "type": "refresh", "ws": ws})
    if "token_version" not in to_encode:
        to_encode["token_version"] = 0
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str, require_role: bool = True) -> Dict[str, Any]:
    """
    Decodes and verifies a JWT token.
    Enforces pinned algorithm (settings.ALGORITHM), strictly rejects 'none' algorithm,
    and enforces token expiration.
    """
    try:
        # Pinned algorithm check on unverified header before signature verification
        unverified_header = jwt.get_unverified_header(token)
        alg = unverified_header.get("alg")
        if not alg or alg != settings.ALGORITHM or alg.lower() == "none":
            raise ValueError(f"Algorithm '{alg}' is not permitted. Only {settings.ALGORITHM} is accepted.")

        required_claims = ["exp", "sub"]
        if require_role:
            required_claims.append("role")

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"require": required_claims, "verify_exp": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired.")
    except jwt.PyJWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")

def get_mfa_cipher() -> Fernet:
    """Derives a deterministic 32-byte Fernet key for symmetric MFA secret encryption at rest."""
    key_env = settings.MFA_ENCRYPTION_KEY
    if key_env:
        key_bytes = hashlib.sha256(key_env.encode()).digest()
    else:
        key_bytes = hashlib.sha256((settings.SECRET_KEY + "_mfa_encryption_salt").encode()).digest()
    fernet_key = base64.urlsafe_b64encode(key_bytes)
    return Fernet(fernet_key)

def encrypt_mfa_secret(secret: str) -> str:
    """Encrypts a plaintext base32 TOTP secret for storage at rest."""
    if not secret:
        return secret
    cipher = get_mfa_cipher()
    return cipher.encrypt(secret.strip().encode()).decode()

def decrypt_mfa_secret(stored_secret: Optional[str]) -> Optional[str]:
    """Decrypts a stored TOTP secret, falling back gracefully if already plaintext."""
    if not stored_secret:
        return None
    try:
        cipher = get_mfa_cipher()
        return cipher.decrypt(stored_secret.encode()).decode()
    except Exception:
        # Fallback if stored in plaintext (e.g. from existing test fixtures)
        return stored_secret

def generate_totp_secret() -> str:
    """Generates a standard RFC 6238 base32 secret."""
    return pyotp.random_base32()

def generate_provisioning_uri(email: str, secret: str, issuer: str = "AICTE Approval Portal") -> str:
    """Generates an otpauth:// provisioning URI for authenticator apps."""
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(name=email, issuer_name=issuer)

def generate_qr_code_data_uri(provisioning_uri: str) -> str:
    """Generates server-side QR code data URI. Never logs the underlying secret."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=2,
    )
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def generate_recovery_codes(count: int = 8) -> List[str]:
    """Generates formatted single-use alphanumeric recovery codes (e.g. ABCD-1234)."""
    codes = []
    for _ in range(count):
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        codes.append(f"{part1}-{part2}")
    return codes

def hash_recovery_code(user_id: str, code: str) -> str:
    """Hashes a recovery code with user_id salt."""
    clean = code.strip().replace("-", "").replace(" ", "").upper()
    return hashlib.sha256(f"{user_id}:{clean}".encode()).hexdigest()

def verify_and_consume_recovery_code(user, raw_code: str) -> bool:
    """Validates recovery code and removes it (single-use guarantee)."""
    if not user.mfa_recovery_codes:
        return False
    try:
        stored_hashes = json.loads(user.mfa_recovery_codes)
        if not isinstance(stored_hashes, list):
            return False
        candidate_hash = hash_recovery_code(user.id, raw_code)
        if candidate_hash in stored_hashes:
            stored_hashes.remove(candidate_hash)
            user.mfa_recovery_codes = json.dumps(stored_hashes)
            return True
    except Exception:
        pass
    return False

def verify_totp_rfc6238(secret: str, code: str, window: int = 1) -> bool:
    """Standard RFC 6238 Time-based One-Time Password verification (30s window)."""
    if not secret or not code:
        return False
    try:
        clean_secret = secret.strip().replace(" ", "").upper()
        clean_code = str(code).strip().replace(" ", "")
        totp = pyotp.TOTP(clean_secret)
        return bool(totp.verify(clean_code, valid_window=window))
    except Exception:
        return False

def verify_mfa_code(user_secret: Optional[str], code: str) -> bool:
    """
    Validates MFA code.
    Accepts demo code '123456' ONLY IF settings.DEMO_MODE is True.
    When DEMO_MODE is False (production), '123456' is strictly rejected.
    """
    clean_code = code.replace(" ", "").strip()
    if clean_code == "123456":
        return bool(settings.DEMO_MODE)

    if not user_secret:
        return False

    decrypted = decrypt_mfa_secret(user_secret)
    if not decrypted or len(clean_code) != 6:
        return False

    return verify_totp_rfc6238(decrypted, clean_code)

# Brute-force in-memory attempt tracker for fast dev evaluation
_login_attempts: Dict[str, Dict[str, Any]] = {}

def check_account_lockout(email: str) -> Optional[str]:
    """Returns error message if account is locked out, else None."""
    now = datetime.utcnow()
    record = _login_attempts.get(email)
    if record and record.get("locked_until"):
        if now < record["locked_until"]:
            remaining = int((record["locked_until"] - now).total_seconds())
            return f"Account temporarily locked due to repeated failed logins. Try again in {remaining} seconds."
        else:
            # Lockout expired
            _login_attempts.pop(email, None)
    return None

def record_login_failure(email: str) -> bool:
    """Records a failed attempt. Returns True if account is now locked."""
    now = datetime.utcnow()
    record = _login_attempts.setdefault(email, {"attempts": 0, "locked_until": None})
    record["attempts"] += 1
    if record["attempts"] >= settings.MAX_LOGIN_ATTEMPTS:
        record["locked_until"] = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
        return True
    return False

def record_login_success(email: str):
    """Resets failed login tracker upon successful authentication."""
    _login_attempts.pop(email, None)

_rate_limits: Dict[str, List[float]] = {}

def check_rate_limit(key: str, max_requests: int = 5, window_seconds: int = 900) -> bool:
    """Sliding-window rate limiter per key (IP, email, or endpoint). Returns True if allowed, False if exceeded."""
    import time
    now = time.time()
    timestamps = _rate_limits.setdefault(key, [])
    _rate_limits[key] = [t for t in timestamps if now - t < window_seconds]
    if len(_rate_limits[key]) >= max_requests:
        return False
    _rate_limits[key].append(now)
    return True

def clear_rate_limits():
    """Resets all in-memory rate limits and login attempts."""
    _rate_limits.clear()
    _login_attempts.clear()

COMMON_BREACH_PASSWORDS = {
    "password", "password123", "password1234", "password12345", "password@123456",
    "password123456", "password@123", "p@ssword1234", "p@ssword12345",
    "123456789012", "1234567890123", "admin1234567", "administrator",
    "administrator123", "welcome12345", "welcome@12345", "aicte1234567",
    "aicte@123456", "demopassword", "demopassword@123", "admininitialpass@2026",
    "changeme1234", "qwertyuiop12", "qwertyuiop123", "letmein123456",
    "iloveyou12345", "sunshine12345", "princess12345", "football12345",
}

def validate_password_policy(password: str, email: str, current_password_hash: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    """
    Enforces statutory password policy:
    - Min 12 chars
    - Breach-list check
    - Not equal to email
    - Must differ from initial / current password
    """
    clean_pw = password.strip()
    if len(clean_pw) < 12:
        return False, "Password must be at least 12 characters in length."
    if current_password_hash and verify_password(clean_pw, current_password_hash):
        return False, "New password must differ from your current or initial password."
    if clean_pw.lower() == email.strip().lower():
        return False, "Password cannot be equal to your email address."
    if clean_pw.lower() in COMMON_BREACH_PASSWORDS:
        return False, "The chosen password is on a known breach list of common passwords. Please choose a stronger password."
    return True, None

def _clean_header_val(val: Any) -> Optional[str]:
    if val is None or not isinstance(val, str):
        return None
    val_clean = val.strip()
    return val_clean if val_clean else None

def get_request_context(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> RequestContext:
    """
    Security Core (APH & DPDP Compliance):
    Derives role, user ID, region_id, and institution_id ONLY from the verified JWT token.
    Completely removes reliance on x-user-* headers.
    Strictly rejects forged or unverified x-user-role / x-user-id headers.
    """
    auth_val = _clean_header_val(authorization)

    # Detect any spoofed / forged headers in incoming HTTP request
    role_header = None
    user_header = None
    region_header = None
    inst_header = None
    if request is not None and hasattr(request, "headers"):
        role_header = _clean_header_val(request.headers.get("x-user-role"))
        user_header = _clean_header_val(request.headers.get("x-user-id"))
        region_header = _clean_header_val(request.headers.get("x-region-id"))
        inst_header = _clean_header_val(request.headers.get("x-institution-id"))

    # Reject forged header privilege escalation attempts without a valid JWT
    if not auth_val:
        if role_header or user_header or region_header or inst_header:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Security Violation: Direct user role or identity headers are rejected. Identity must be derived solely from a verified JWT token.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
        )

    parts = auth_val.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'.",
        )

    token = parts[1]
    try:
        payload = decode_token(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )

    jwt_user_id = payload.get("sub")
    jwt_role = payload.get("role")
    jwt_region_id = payload.get("region_id")
    jwt_institution_id = payload.get("institution_id")
    jwt_ws = payload.get("ws", "live")

    if not jwt_user_id or not jwt_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: user ID and role are required.",
        )

    # Check X-Workspace header cross-contamination if provided
    if request is not None and hasattr(request, "headers"):
        header_ws = request.headers.get("x-workspace")
        if header_ws and header_ws.strip().lower() != jwt_ws.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Workspace Violation: Provided token is bound to '{jwt_ws}' workspace and cannot access '{header_ws}' workspace.",
            )

    from app.workspace import current_workspace_var
    current_workspace_var.set(jwt_ws)

    # DEFECT 5 guard: restricted password change token can ONLY access /auth/change-password
    if payload.get("must_change_password") or payload.get("scope") == "PASSWORD_CHANGE_REQUIRED" or payload.get("type") == "password_change_required":
        path = str(request.url.path) if request and hasattr(request, "url") else ""
        if not (path.endswith("/change-password") or path.endswith("/auth/change-password")):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before accessing other APIs."
            )

    # Reject forged header mismatch
    if role_header and role_header != jwt_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Violation: Forged x-user-role '{role_header}' does not match verified JWT role '{jwt_role}'. Request blocked.",
        )
    if user_header and user_header != jwt_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Security Violation: Forged x-user-id '{user_header}' does not match verified JWT user '{jwt_user_id}'. Request blocked.",
        )

    ip = "127.0.0.1"
    if request is not None and hasattr(request, "client") and request.client:
        ip = request.client.host

    return RequestContext(
        user_id=jwt_user_id,
        role=jwt_role,
        region_id=jwt_region_id,
        institution_id=jwt_institution_id,
        ip_address=ip,
        workspace=jwt_ws,
    )

