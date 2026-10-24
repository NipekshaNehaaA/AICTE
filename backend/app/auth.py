import base64
import hashlib
import hmac
import os
import secrets
import struct
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
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

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(data: Dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
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

def verify_totp_rfc6238(secret: str, code: str, window: int = 1) -> bool:
    """Standard RFC 6238 Time-based One-Time Password verification (30s window)."""
    try:
        clean_secret = secret.strip().upper()
        missing_padding = len(clean_secret) % 8
        if missing_padding:
            clean_secret += "=" * (8 - missing_padding)
        key = base64.b32decode(clean_secret, casefold=True)
        current_step = int(datetime.utcnow().timestamp() / 30)
        for offset in range(-window, window + 1):
            time_bytes = struct.pack(">Q", current_step + offset)
            h = hmac.new(key, time_bytes, hashlib.sha1).digest()
            o = h[19] & 0x0F
            token_int = (struct.unpack(">I", h[o : o + 4])[0] & 0x7FFFFFFF) % 1000000
            if f"{token_int:06d}" == code:
                return True
        return False
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

    if not user_secret or len(clean_code) != 6:
        return False

    return verify_totp_rfc6238(user_secret, clean_code)

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

    if not jwt_user_id or not jwt_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token claims: user ID and role are required.",
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
    )

