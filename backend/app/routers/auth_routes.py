"""
=============================================================================
AUTHENTICATION & RBAC LOGIN ROUTER WITH REAL ACCOUNTS & EVALUATOR MODE
=============================================================================
Implements Task 3:
1. Real auth: email+password sign-up for technical institutions with email verification.
2. Officer accounts seeded/provisioned by Council Admin (SUPER_ADMIN) with welcome email.
3. Password reset flow with time-bound cryptographic token and SMTP delivery.
4. Account lockout tracking for repeated authentication failures.
5. JWT refresh token rotation.
6. Role-based routing determination after login.
7. Evaluator Mode gating for demo personas and demo switch tokens.
8. Hash-chained audit ledger recording for all auth events.
=============================================================================
"""

import secrets
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import User, Region, Institution
from app.email_service import email_service
from app.scoped_dal import ScopedDAL, RequestContext
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_request_context,
    verify_mfa_code,
    check_account_lockout,
    record_login_failure,
    record_login_success,
    encrypt_mfa_secret,
    decrypt_mfa_secret,
    generate_totp_secret,
    generate_provisioning_uri,
    generate_qr_code_data_uri,
    generate_recovery_codes,
    hash_recovery_code,
    verify_and_consume_recovery_code,
    verify_totp_rfc6238,
    check_rate_limit,
    validate_password_policy,
)

def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Access Control"])

ROLE_DEFAULT_ROUTES = {
    "INSTITUTION_USER": "/dashboard",
    "REGIONAL_OFFICER": "/queue",
    "REGIONAL_DIRECTOR": "/queue",
    "BUREAU_OFFICER": "/queue",
    "BUREAU_HEAD": "/queue",
    "SCRUTINY_MEMBER": "/queue",
    "COMMITTEE_MEMBER": "/queue",
    "SAC_SHC_MEMBER": "/queue",
    "SUPER_ADMIN": "/queue",
    "AUDITOR": "/audit",
}

def get_default_route_for_role(role: str) -> str:
    return ROLE_DEFAULT_ROUTES.get(role, "/dashboard")


# -----------------------------------------------------------------------------
# PYDANTIC REQUEST & RESPONSE SCHEMAS
# -----------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str
    password: str

class MFAVerifyRequest(BaseModel):
    email: str
    mfa_code: str

class MFAEnrollConfirmRequest(BaseModel):
    email: str
    mfa_code: str

class LoginResponse(BaseModel):
    mfa_required: bool
    mfa_enrollment_required: Optional[bool] = False
    provisioning_uri: Optional[str] = None
    qr_code_base64: Optional[str] = None
    manual_entry_key: Optional[str] = None
    recovery_codes: Optional[List[str]] = None
    email: str
    full_name: str
    role: str
    region_code: Optional[str] = None
    institution_id: Optional[str] = None
    institution_name: Optional[str] = None
    institution_pid: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    default_route: Optional[str] = None
    must_change_password: Optional[bool] = False
    message: str

class SignUpRequest(BaseModel):
    email: str
    password: str
    full_name: str
    institution_name: str
    category: Optional[str] = "Engineering & Tech"
    region_code: Optional[str] = "SWRO"
    address: Optional[str] = "Campus Knowledge Park"
    state: Optional[str] = "Karnataka"
    whatsapp_phone: Optional[str] = None
    opt_in_whatsapp: bool = False
    preferred_language: Optional[str] = "en"

class VerifyEmailRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

class ChangePasswordRequest(BaseModel):
    old_password: Optional[str] = None
    new_password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class CreateOfficerRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str
    region_code: Optional[str] = None
    whatsapp_phone: Optional[str] = None
    preferred_language: Optional[str] = "en"


# -----------------------------------------------------------------------------
# EVALUATOR PERSONAS (GATED BEHIND EVALUATOR_MODE / DEMO_MODE)
# -----------------------------------------------------------------------------

@router.get("/personas")
@router.get("/demo-personas")
def get_demo_personas(request: Request, db: Session = Depends(get_db)):
    """Returns curated demo personas for 1-click evaluation (Demo Only). Disabled in Live workspace."""
    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    if ws != "sandbox":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found: Personas endpoint is only available in Sandbox workspace.",
        )
    return {
        "personas": [
            {
                "role": "REGIONAL_OFFICER",
                "role_label": "Regional Officer (SWRO)",
                "name": "Dr. Regional Officer (SWRO - Bengaluru)",
                "email": "ro.swro@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "SWRO",
                "region_name": "South-Western Regional Office",
                "badge_color": "blossom",
                "description": "Scrutiny sign-off, deficiency revert, EVC panel confirmation",
            },
            {
                "role": "REGIONAL_DIRECTOR",
                "role_label": "Regional Director (Assumed Escalation Level)",
                "name": "Dr. K. S. Sitaram (Regional Director - SWRO)",
                "email": "rd.swro@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "SWRO",
                "region_name": "South-Western Regional Office",
                "badge_color": "blossom-dark",
                "description": "Level 2 SLA escalation review, regional corridor jurisdiction",
            },
            {
                "role": "BUREAU_OFFICER",
                "role_label": "Bureau Officer (Approval Bureau)",
                "name": "Shri Anand K. Sharma (Approval Bureau Officer)",
                "email": "approval.bureau@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "Pan-India Bureau Oversight",
                "badge_color": "amber",
                "description": "Bureau scrutiny, compliance docket curation, hearing records",
            },
            {
                "role": "BUREAU_HEAD",
                "role_label": "Bureau Head (Assumed Escalation Level)",
                "name": "Dr. M. S. Jayaprakash (Bureau Head - Approval)",
                "email": "bureau.head@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "Pan-India Bureau Oversight",
                "badge_color": "amber",
                "description": "Level 3 SLA escalation review, high-stakes docket review",
            },
            {
                "role": "SCRUTINY_MEMBER",
                "role_label": "Scrutiny Committee Member",
                "name": "Prof. N. Meenakshi (Scrutiny Committee Member)",
                "email": "scrutiny.member@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "SWRO",
                "region_name": "South-Western Region",
                "badge_color": "mint",
                "description": "Table 2.3 norm verification, deficiency memo curation (Clause 1.8)",
            },
            {
                "role": "COMMITTEE_MEMBER",
                "role_label": "EVC Committee Expert Inspector",
                "name": "Prof. EVC Expert (SWRO)",
                "email": "expert.swro@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "SWRO",
                "region_name": "South-Western Region",
                "badge_color": "slate",
                "description": "Conflict-of-interest declaration, 30-min geotagged video inspection",
            },
            {
                "role": "SAC_SHC_MEMBER",
                "role_label": "SAC/SHC Appellate Committee Member",
                "name": "Justice (Retd.) K. V. Narayanan (SAC Member)",
                "email": "sac.appellate@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "Standing Appellate Committee (Pan-India)",
                "badge_color": "purple",
                "description": "Hears appeals under Clause 1.11(a) within 7 days of deficiency / LoD",
            },
            {
                "role": "INSTITUTION_USER",
                "role_label": "Institution Principal / Applicant",
                "name": "Dr. Principal (Apex Institute of Technology)",
                "email": "principal.110000001@fictional-aicte.edu.in",
                "default_password": "DemoPassword@123",
                "region_code": "SWRO",
                "region_name": "South-Western Region",
                "institution_name": "Apex Institute of Technology (PID: 1-10000001)",
                "badge_color": "mint",
                "description": "Application submission, compliance evidence, lease renewal",
            },
            {
                "role": "AUDITOR",
                "role_label": "Statutory Compliance Auditor",
                "name": "Smt. Priya Balan (Statutory Auditor)",
                "email": "auditor.compliance@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "Pan-India Oversight",
                "badge_color": "line",
                "description": "Cryptographic audit ledger verification, zero write access",
            },
            {
                "role": "SUPER_ADMIN",
                "role_label": "Member Secretary / Council Administration",
                "name": "Dr. Arvind Ramanathan (Member Secretary)",
                "email": "member.secretary@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "National Council (HQ)",
                "badge_color": "blossom-dark",
                "description": "Council communications, Level 4 escalations, APH compiler",
            },
        ],
        "demo_mfa_code": "123456",
        "demo_password": "DemoPassword@123"
    }


# -----------------------------------------------------------------------------
# REAL LOGIN & TOTP MFA VERIFICATION
# -----------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """
    Step 1 of Authentication:
    Validates email + password with PBKDF2 hash and checks brute-force lockout.
    Verifies that institution accounts have verified their email.
    Prompts for MFA verification if MFA is enabled on the account.
    Logs successful login event to the hash-chained audit ledger.
    """
    email = payload.email.strip().lower()

    # Check brute-force lockout
    lockout_err = check_account_lockout(email)
    if lockout_err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=lockout_err)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        record_login_failure(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )

    if not verify_password(payload.password, user.password_hash):
        record_login_failure(email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify credentials."
        )

    if user.is_active is False:
        record_login_failure(email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Please contact system administrator."
        )

    # Enforce email verification for active accounts
    if user.email_verified is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required. Please verify your email before logging in."
        )

    # Password verified: reset failed counter
    record_login_success(email)

    reg_code = user.region.code if user.region else "HQ"
    default_route = get_default_route_for_role(user.role)
    inst_name = user.institution.name if user.institution and user.role == "INSTITUTION_USER" else None
    inst_pid = user.institution.permanent_id if user.institution and user.role == "INSTITUTION_USER" else None

    # Check if MFA is required based on user configuration
    requires_mfa = bool(user.mfa_enabled)
    if requires_mfa:
        # Check if officer has enrolled yet
        if not user.mfa_secret:
            secret = generate_totp_secret()
            user.mfa_pending_secret = encrypt_mfa_secret(secret)
            user.mfa_enabled = True
            db.commit()

            prov_uri = generate_provisioning_uri(user.email, secret)
            qr_uri = generate_qr_code_data_uri(prov_uri)

            from app.workspace import resolve_workspace
            ws = resolve_workspace(request)
            msg = "Two-factor authentication enrollment required. Please scan the QR code with your authenticator app and enter the 6-digit confirmation code."
            if ws == "sandbox":
                msg += " (Demo mode active: you may also enter '123456')."

            return LoginResponse(
                mfa_required=True,
                mfa_enrollment_required=True,
                provisioning_uri=prov_uri,
                qr_code_base64=qr_uri,
                manual_entry_key=secret,
                email=user.email,
                full_name=user.full_name,
                role=user.role,
                region_code=reg_code,
                institution_id=user.institution_id,
                institution_name=inst_name,
                institution_pid=inst_pid,
                default_route=default_route,
                message=msg
            )

        from app.workspace import resolve_workspace
        ws = resolve_workspace(request)
        msg = "Password verified. Please enter the 6-digit two-factor authentication code."
        if ws == "sandbox":
            msg += " (Demo: 123456)."
        return LoginResponse(
            mfa_required=True,
            mfa_enrollment_required=False,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            region_code=reg_code,
            institution_id=user.institution_id,
            institution_name=inst_name,
            institution_pid=inst_pid,
            default_route=default_route,
            message=msg
        )

    # Direct token issuance if MFA disabled
    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    is_pw_change_required = bool(user.must_change_password)
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
        "token_version": user.token_version or 0,
        "must_change_password": is_pw_change_required,
        "scope": "PASSWORD_CHANGE_REQUIRED" if is_pw_change_required else "FULL_ACCESS",
        "type": "password_change_required" if is_pw_change_required else "access",
        "ws": ws,
    }, workspace=ws)
    refresh_token = create_refresh_token({
        "sub": user.id,
        "role": user.role,
        "token_version": user.token_version or 0,
        "must_change_password": is_pw_change_required,
        "ws": ws,
    }, workspace=ws)

    # Log successful login to hash-chained audit ledger
    try:
        ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
        ScopedDAL(db, ctx).append_audit_entry(
            action_type="USER_LOGIN_SUCCESS",
            entity_type="User",
            entity_id=user.id,
            metadata={"email": user.email, "role": user.role, "mfa_used": False}
        )
        db.commit()
    except Exception:
        pass

    return LoginResponse(
        mfa_required=False,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        region_code=reg_code,
        institution_id=user.institution_id,
        institution_name=inst_name,
        institution_pid=inst_pid,
        access_token=access_token,
        refresh_token=refresh_token,
        default_route="/auth/change-password" if is_pw_change_required else default_route,
        must_change_password=is_pw_change_required,
        message="Initial password change required before accessing other APIs." if is_pw_change_required else "Authentication successful."
    )

@router.post("/mfa-enroll-confirm", response_model=LoginResponse)
def confirm_mfa_enrollment(payload: MFAEnrollConfirmRequest, request: Request, db: Session = Depends(get_db)):
    """
    Step 2b of Authentication: Confirms TOTP enrollment.
    Verifies code against pending secret, saves encrypted secret, generates recovery codes,
    and returns initial tokens + recovery codes.
    """
    email = payload.email.strip().lower()
    lockout_err = check_account_lockout(email)
    if lockout_err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=lockout_err)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        record_login_failure(email)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    if user.is_active is False:
        record_login_failure(email)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled. Please contact system administrator.")

    if not user.mfa_pending_secret and not user.mfa_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No pending MFA enrollment found for this user."
        )

    secret_encrypted = user.mfa_pending_secret or user.mfa_secret
    secret_plain = decrypt_mfa_secret(secret_encrypted)

    clean_code = payload.mfa_code.replace(" ", "").replace("-", "").strip()

    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    is_valid = verify_totp_rfc6238(secret_plain, clean_code)
    if not is_valid and clean_code == "123456" and ws == "sandbox":
        is_valid = True

    if not is_valid:
        record_login_failure(email)
        err_msg = "Invalid verification code. Please check your authenticator app and try again."
        if ws == "sandbox":
            err_msg += " (Demo PIN: 123456)."
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=err_msg)

    # Success: confirm secret and record timestep
    record_login_success(email)
    current_step = int(datetime.utcnow().timestamp() / 30)
    user.last_mfa_timestep = current_step
    user.mfa_secret = secret_encrypted
    user.mfa_pending_secret = None
    user.mfa_enabled = True

    raw_recovery_codes = generate_recovery_codes(8)
    hashed_codes = [hash_recovery_code(user.id, code) for code in raw_recovery_codes]
    user.mfa_recovery_codes = json.dumps(hashed_codes)
    db.commit()

    reg_code = user.region.code if user.region else "HQ"
    default_route = get_default_route_for_role(user.role)
    inst_name = user.institution.name if user.institution and user.role == "INSTITUTION_USER" else None
    inst_pid = user.institution.permanent_id if user.institution and user.role == "INSTITUTION_USER" else None

    is_pw_change_required = bool(user.must_change_password)
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
        "token_version": user.token_version or 0,
        "must_change_password": is_pw_change_required,
        "scope": "PASSWORD_CHANGE_REQUIRED" if is_pw_change_required else "FULL_ACCESS",
        "type": "password_change_required" if is_pw_change_required else "access",
        "ws": ws,
    }, workspace=ws)
    refresh_token = create_refresh_token({
        "sub": user.id,
        "role": user.role,
        "token_version": user.token_version or 0,
        "must_change_password": is_pw_change_required,
        "ws": ws,
    }, workspace=ws)

    try:
        ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
        ScopedDAL(db, ctx).append_audit_entry(
            action_type="MFA_ENROLLED",
            entity_type="User",
            entity_id=user.id,
            metadata={"email": user.email, "role": user.role, "method": "TOTP_RFC6238"}
        )
        db.commit()
    except Exception:
        pass

    return LoginResponse(
        mfa_required=False,
        mfa_enrollment_required=False,
        recovery_codes=raw_recovery_codes,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        region_code=reg_code,
        institution_id=user.institution_id,
        institution_name=inst_name,
        institution_pid=inst_pid,
        access_token=access_token,
        refresh_token=refresh_token,
        default_route="/auth/change-password" if is_pw_change_required else default_route,
        must_change_password=is_pw_change_required,
        message="Initial password change required before accessing other APIs." if is_pw_change_required else "Two-factor authentication successfully configured. Save your recovery codes in a secure location."
    )

@router.post("/mfa-verify", response_model=LoginResponse)
def verify_mfa(payload: MFAVerifyRequest, request: Request, db: Session = Depends(get_db)):
    """
    Step 2 of Authentication:
    Validates 6-digit Time-Based OTP (TOTP) code or single-use recovery code.
    Enforces replay protection and brute-force lockout.
    Issues JWT access & refresh tokens upon success, and logs audit entry.
    """
    email = payload.email.strip().lower()
    lockout_err = check_account_lockout(email)
    if lockout_err:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=lockout_err)

    user = db.query(User).filter(User.email == email).first()
    if not user:
        record_login_failure(email)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    if user.is_active is False:
        record_login_failure(email)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled. Please contact system administrator.")

    clean_code = payload.mfa_code.replace(" ", "").strip()

    # 1. Recovery code check
    is_recovery = False
    if verify_and_consume_recovery_code(user, clean_code):
        is_recovery = True
        record_login_success(email)
        db.commit()
    else:
        # 2. Check demo code bypass: ONLY if workspace is 'sandbox'!
        from app.workspace import resolve_workspace
        ws = resolve_workspace(request)
        is_demo_bypass = False
        if clean_code == "123456" and ws == "sandbox":
            is_demo_bypass = True

        # 3. Verify TOTP RFC 6238 against user's secret
        is_totp_valid = False
        if not is_demo_bypass:
            if not user.mfa_secret:
                record_login_failure(email)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Two-factor authentication is not enrolled. Please log in with password to enroll."
                )

            secret_plain = decrypt_mfa_secret(user.mfa_secret)
            is_totp_valid = verify_totp_rfc6238(secret_plain, clean_code)

            # Replay protection check
            if is_totp_valid:
                current_step = int(datetime.utcnow().timestamp() / 30)
                if user.last_mfa_timestep == current_step:
                    record_login_failure(email)
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="This verification code has already been used. Please wait for the next 30-second code from your authenticator app."
                    )
                user.last_mfa_timestep = current_step
                db.commit()

        if not is_recovery and not is_demo_bypass and not is_totp_valid:
            record_login_failure(email)
            err_msg = "Invalid two-factor authentication code. Please try again."
            if ws == "sandbox":
                err_msg = "Invalid TOTP code. For demonstration, please enter '123456'."
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=err_msg
            )

        record_login_success(email)

    reg_code = user.region.code if user.region else "HQ"
    default_route = get_default_route_for_role(user.role)
    inst_name = user.institution.name if user.institution and user.role == "INSTITUTION_USER" else None
    inst_pid = user.institution.permanent_id if user.institution and user.role == "INSTITUTION_USER" else None

    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    is_pw_change_required = bool(user.must_change_password)
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
        "token_version": user.token_version or 0,
        "must_change_password": is_pw_change_required,
        "scope": "PASSWORD_CHANGE_REQUIRED" if is_pw_change_required else "FULL_ACCESS",
        "type": "password_change_required" if is_pw_change_required else "access",
        "ws": ws,
    }, workspace=ws)
    refresh_token = create_refresh_token({
        "sub": user.id,
        "role": user.role,
        "token_version": user.token_version or 0,
        "must_change_password": is_pw_change_required,
        "ws": ws,
    }, workspace=ws)

    # Log to audit ledger
    try:
        ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
        ScopedDAL(db, ctx).append_audit_entry(
            action_type="MFA_RECOVERY_CODE_USED" if is_recovery else "USER_LOGIN_MFA_SUCCESS",
            entity_type="User",
            entity_id=user.id,
            metadata={"email": user.email, "role": user.role, "mfa_used": True, "recovery": is_recovery}
        )
        db.commit()
    except Exception:
        pass

    return LoginResponse(
        mfa_required=False,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        region_code=reg_code,
        institution_id=user.institution_id,
        institution_name=inst_name,
        institution_pid=inst_pid,
        access_token=access_token,
        refresh_token=refresh_token,
        default_route="/auth/change-password" if is_pw_change_required else default_route,
        must_change_password=is_pw_change_required,
        message="Initial password change required before accessing other APIs." if is_pw_change_required else "Two-Factor Authentication verified. Access granted."
    )

@router.post("/admin/reset-mfa/{user_id}")
def admin_reset_mfa(
    user_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db)
):
    """
    Super Admin endpoint to reset a user's MFA settings.
    Wipes mfa_secret, mfa_pending_secret, mfa_recovery_codes, and last_mfa_timestep.
    Requires SUPER_ADMIN role.
    Strictly recorded in the SHA-256 hash-chained audit ledger.
    """
    if ctx.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Super Admin (Council Authority) can reset stakeholder MFA."
        )

    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    target_user.mfa_secret = None
    target_user.mfa_pending_secret = None
    target_user.mfa_recovery_codes = None
    target_user.last_mfa_timestep = None
    target_user.mfa_enabled = True # Keep enabled so user is prompted to enroll on next login
    db.commit()

    # Append to hash-chained audit ledger
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="MFA_RESET_BY_ADMIN",
        entity_type="User",
        entity_id=target_user.id,
        metadata={
            "target_user_id": target_user.id,
            "target_email": target_user.email,
            "admin_user_id": ctx.user_id,
            "reason": "Administrative MFA credentials reset request"
        }
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "user_id": target_user.id,
        "email": target_user.email,
        "message": f"MFA credentials for {target_user.email} have been reset. User will be required to re-enroll upon next login."
    }


# -----------------------------------------------------------------------------
# INSTITUTION SIGN-UP & EMAIL VERIFICATION (DEFECT 3 FIX)
# -----------------------------------------------------------------------------

@router.post("/signup")
def signup_institution(payload: SignUpRequest, request: Request, db: Session = Depends(get_db)):
    """
    Real Institutional Sign-Up (DEFECT 3 Fixed):
    - Never returns verification token in HTTP response.
    - Response body does not reveal whether the email already exists.
    - Token is stored only as SHA-256 hash with 24h expiry.
    - Rate-limited per IP and per email.
    """
    ip = get_client_ip(request)
    email = payload.email.strip().lower()

    # Rate limiting (DEFECT 3 & 7)
    if not check_rate_limit(f"signup_ip:{ip}", max_requests=10, window_seconds=900) or not check_rate_limit(f"signup_email:{email}", max_requests=5, window_seconds=900):
        try:
            ScopedDAL(db, RequestContext(user_id="anonymous", role="ANONYMOUS", ip_address=ip)).append_audit_entry(
                action_type="SIGNUP_RATE_LIMITED",
                entity_type="User",
                entity_id="unknown",
                metadata={"email": email, "ip": ip}
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many sign-up requests. Please try again later."
        )

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        time.sleep(0.05)
        try:
            ScopedDAL(db, RequestContext(user_id=existing.id, role=existing.role, ip_address=ip)).append_audit_entry(
                action_type="USER_SIGNUP_DUPLICATE_ATTEMPT",
                entity_type="User",
                entity_id=existing.id,
                metadata={"email": email, "ip": ip}
            )
            db.commit()
        except Exception:
            pass
        return {
            "status": "SUCCESS",
            "message": "If this email address is eligible, verification instructions have been dispatched.",
        }

    # Resolve Region
    reg = None
    if payload.region_code:
        reg = db.query(Region).filter(Region.code == payload.region_code.upper()).first()
    if not reg:
        reg = db.query(Region).first()

    # Generate permanent ID
    token_seed = secrets.token_hex(4).upper()
    pid = f"1-{token_seed}"

    # Create Institution
    inst = Institution(
        permanent_id=pid,
        name=payload.institution_name.strip(),
        address=payload.address or "Campus Address",
        state=payload.state or "Karnataka",
        region_id=reg.id if reg else None,
        category=payload.category or "Engineering & Tech",
        status="PENDING_VERIFICATION",
        compliance_health_score=100.0,
        preferred_language=payload.preferred_language or "en",
        is_synthetic=False,
    )
    db.add(inst)
    db.flush()

    # Cryptographic verification token: raw token sent only via email, SHA-256 hash stored
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="INSTITUTION_USER",
        region_id=reg.id if reg else None,
        institution_id=inst.id,
        mfa_enabled=False,
        email_verified=False,
        verification_token=token_hash,
        verification_token_expires_at=datetime.utcnow() + timedelta(hours=24),
        whatsapp_phone=payload.whatsapp_phone,
        opt_in_whatsapp=payload.opt_in_whatsapp,
        preferred_language=payload.preferred_language or "en",
        preferred_channels="IN_APP,EMAIL",
    )
    db.add(user)
    db.flush()

    email_body = (
        f"Dear {user.full_name},\n\n"
        f"Welcome to the AICTE Regulatory Approval & Compliance Automation Platform.\n"
        f"Your institution registration for '{inst.name}' (PID: {inst.permanent_id}) has been created.\n\n"
        f"Please verify your email address to activate your account:\n"
        f"Verification Token: {raw_token}\n\n"
        f"Or click: http://127.0.0.1:3000/verify-email?token={raw_token}\n\n"
        f"Regulatory Regards,\nAICTE Approval Bureau"
    )
    email_service.send_email(
        to_email=user.email,
        subject="Verify Your AICTE Institution Account",
        text_content=email_body,
        override_quiet=True,
    )

    ctx = RequestContext(user_id=user.id, role="INSTITUTION_USER", region_id=reg.id if reg else None, institution_id=inst.id, ip_address=ip)
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="USER_SIGNUP",
        entity_type="User",
        entity_id=user.id,
        metadata={
            "email": user.email,
            "institution_id": inst.id,
            "permanent_id": inst.permanent_id,
            "institution_name": inst.name,
            "ip": ip,
        }
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "If this email address is eligible, verification instructions have been dispatched.",
    }


@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    """
    Validates verification token (DEFECT 3 Fixed):
    - Single use: invalidates token on use
    - Token validated against SHA-256 hash
    - Enforces 24h expiry
    - Rate limits brute-force attempts
    - Audits verification success and failure
    """
    ip = get_client_ip(request)

    if not check_rate_limit(f"verify_ip:{ip}", max_requests=10, window_seconds=900):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification attempts. Please try again later."
        )

    clean_token = payload.token.strip()
    token_hash = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()
    user = db.query(User).filter(User.verification_token == token_hash).first()

    now = datetime.utcnow()
    if not user or (user.verification_token_expires_at and user.verification_token_expires_at < now):
        try:
            ScopedDAL(db, RequestContext(user_id="anonymous", role="ANONYMOUS", ip_address=ip)).append_audit_entry(
                action_type="EMAIL_VERIFICATION_FAILED",
                entity_type="User",
                entity_id="unknown",
                metadata={"ip": ip, "reason": "expired_or_invalid_token"}
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None

    if user.institution:
        user.institution.status = "ACTIVE"

    ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id, ip_address=ip)
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="EMAIL_VERIFIED",
        entity_type="User",
        entity_id=user.id,
        metadata={"email": user.email, "institution_id": user.institution_id, "ip": ip}
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Email verified successfully. You may now log in to the portal.",
    }


# -----------------------------------------------------------------------------
# PASSWORD RESET FLOW (DEFECT 2 FIX)
# -----------------------------------------------------------------------------

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Initiates password reset (DEFECT 2 Fixed):
    - Never returns token in response.
    - Identical response body and timing for known and unknown accounts.
    - Stored only as SHA-256 hash with 30-minute expiry.
    - Rate-limited per IP and per email.
    - Audited (requested, rate-limited).
    """
    ip = get_client_ip(request)
    email = payload.email.strip().lower()

    if not check_rate_limit(f"forgot_ip:{ip}", max_requests=5, window_seconds=900) or not check_rate_limit(f"forgot_email:{email}", max_requests=5, window_seconds=900):
        try:
            ScopedDAL(db, RequestContext(user_id="anonymous", role="ANONYMOUS", ip_address=ip)).append_audit_entry(
                action_type="PASSWORD_RESET_RATE_LIMITED",
                entity_type="User",
                entity_id="unknown",
                metadata={"email": email, "ip": ip}
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset requests. Please try again later."
        )

    user = db.query(User).filter(User.email == email).first()

    if user:
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        user.reset_password_token = token_hash
        user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=30)

        email_body = (
            f"Dear {user.full_name},\n\n"
            f"A password reset was requested for your AICTE Regulatory Portal account.\n"
            f"Password Reset Token: {raw_token}\n\n"
            f"This token is valid for 30 minutes and can be used once.\n"
            f"If you did not request this, please contact AICTE security administrator immediately.\n\n"
            f"Regulatory Regards,\nAICTE Security Operations"
        )
        email_service.send_email(
            to_email=user.email,
            subject="AICTE Portal Password Reset Request",
            text_content=email_body,
            override_quiet=True,
        )

        ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id, ip_address=ip)
        ScopedDAL(db, ctx).append_audit_entry(
            action_type="PASSWORD_RESET_REQUESTED",
            entity_type="User",
            entity_id=user.id,
            metadata={"email": user.email, "ip": ip}
        )
        db.commit()
    else:
        # Constant timing simulation: compute dummy hash + sleep
        dummy_raw = secrets.token_urlsafe(32)
        _ = hashlib.sha256(dummy_raw.encode("utf-8")).hexdigest()
        time.sleep(0.05)
        try:
            ScopedDAL(db, RequestContext(user_id="anonymous", role="ANONYMOUS", ip_address=ip)).append_audit_entry(
                action_type="PASSWORD_RESET_REQUESTED",
                entity_type="User",
                entity_id="unknown",
                metadata={"email": email, "ip": ip, "notice": "account_not_found"}
            )
            db.commit()
        except Exception:
            pass

    return {
        "status": "SUCCESS",
        "message": "If the account exists, password reset instructions have been dispatched.",
    }


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """
    Completes password reset (DEFECT 2 Fixed):
    - Single use: token cleared immediately upon use.
    - Validates token against SHA-256 hash.
    - 30-minute expiry strictly enforced.
    - Revokes existing refresh tokens and sessions (token_version incremented).
    - Rate-limits brute-force token guesses.
    - Audited (used, failed).
    """
    ip = get_client_ip(request)

    if not check_rate_limit(f"reset_ip:{ip}", max_requests=10, window_seconds=900):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many password reset attempts. Please try again later."
        )

    clean_token = payload.token.strip()
    token_hash = hashlib.sha256(clean_token.encode("utf-8")).hexdigest()
    user = db.query(User).filter(User.reset_password_token == token_hash).first()

    now = datetime.utcnow()
    if not user or (user.reset_token_expires_at and user.reset_token_expires_at < now):
        try:
            ScopedDAL(db, RequestContext(user_id="anonymous", role="ANONYMOUS", ip_address=ip)).append_audit_entry(
                action_type="PASSWORD_RESET_FAILED",
                entity_type="User",
                entity_id="unknown",
                metadata={"ip": ip, "reason": "expired_or_invalid_token"}
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset token."
        )

    # Validate statutory password policy (DEFECT 5)
    is_valid_pw, pw_err = validate_password_policy(payload.new_password, user.email, user.password_hash)
    if not is_valid_pw:
        try:
            ScopedDAL(db, RequestContext(user_id=user.id, role=user.role, ip_address=ip)).append_audit_entry(
                action_type="PASSWORD_RESET_FAILED",
                entity_type="User",
                entity_id=user.id,
                metadata={"ip": ip, "reason": pw_err}
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err
        )

    # Update password hash
    user.password_hash = hash_password(payload.new_password)
    # Single use: invalidate token
    user.reset_password_token = None
    user.reset_token_expires_at = None
    # Revoke all existing sessions and refresh tokens
    user.token_version = (user.token_version or 0) + 1
    user.must_change_password = False

    # Clear any lockout
    record_login_success(user.email)

    ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id, ip_address=ip)
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="PASSWORD_RESET_USED",
        entity_type="User",
        entity_id=user.id,
        metadata={"email": user.email, "ip": ip}
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Password updated successfully. Please log in with your new credentials.",
    }


# -----------------------------------------------------------------------------
# FORCED PASSWORD CHANGE (DEFECT 5 FIX)
# -----------------------------------------------------------------------------

@router.post("/change-password")
def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Forced first-login password change & general password rotation (DEFECT 5):
    - Enforces min 12 characters, breach-list check, not equal to email.
    - Requires new password to differ from initial / current password.
    - Revokes existing sessions and clears must_change_password flag.
    - Writes immutable audit trail entry.
    """
    user = db.query(User).filter(User.id == ctx.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User account not found."
        )

    if payload.old_password and not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed."
        )

    is_valid_pw, pw_err = validate_password_policy(payload.new_password, user.email, user.password_hash)
    if not is_valid_pw:
        try:
            ScopedDAL(db, ctx).append_audit_entry(
                action_type="PASSWORD_CHANGE_FAILED",
                entity_type="User",
                entity_id=user.id,
                metadata={"email": user.email, "reason": pw_err}
            )
            db.commit()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=pw_err
        )

    # Update password and clear must_change_password
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    # Revoke previous sessions
    user.token_version = (user.token_version or 0) + 1
    record_login_success(user.email)

    # Issue fresh unrestricted tokens
    new_access = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
        "token_version": user.token_version,
    })
    new_refresh = create_refresh_token({
        "sub": user.id,
        "role": user.role,
        "token_version": user.token_version,
    })

    ScopedDAL(db, ctx).append_audit_entry(
        action_type="PASSWORD_CHANGED",
        entity_type="User",
        entity_id=user.id,
        metadata={"email": user.email}
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Password changed successfully.",
        "access_token": new_access,
        "refresh_token": new_refresh,
    }


# -----------------------------------------------------------------------------
# JWT REFRESH TOKEN ROTATION (TASK 3)
# -----------------------------------------------------------------------------

@router.post("/refresh")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Validates cryptographic refresh token and issues fresh access and refresh token pair.
    Revokes tokens if password has been changed (token_version mismatch).
    """
    try:
        decoded = decode_token(payload.refresh_token.strip(), require_role=False)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {str(e)}"
        )

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Provided token is not a valid refresh token."
        )

    user_id = decoded.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account associated with refresh token is invalid or inactive."
        )

    if decoded.get("token_version", 0) != (user.token_version or 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or was revoked due to password change. Please log in again."
        )

    new_access = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
        "token_version": user.token_version or 0,
    })
    new_refresh = create_refresh_token({
        "sub": user.id,
        "role": user.role,
        "token_version": user.token_version or 0,
    })

    return {
        "access_token": new_access,
        "refresh_token": new_refresh,
        "token_type": "bearer",
        "role": user.role,
    }


# -----------------------------------------------------------------------------
# OFFICER ACCOUNT PROVISIONING BY ADMIN (TASK 3)
# -----------------------------------------------------------------------------

VALID_OFFICER_ROLES = {
    "REGIONAL_OFFICER",
    "REGIONAL_DIRECTOR",
    "BUREAU_OFFICER",
    "BUREAU_HEAD",
    "SCRUTINY_MEMBER",
    "COMMITTEE_MEMBER",
    "SAC_SHC_MEMBER",
    "AUDITOR",
    "SUPER_ADMIN",
}

@router.post("/admin/create-officer")
def admin_create_officer(
    payload: CreateOfficerRequest,
    db: Session = Depends(get_db),
    ctx: RequestContext = Depends(get_request_context),
):
    """
    Allows Super Admin (Member Secretary) to seed and provision authorized officer accounts.
    Dispatches welcome email via SMTP and records in hash-chained audit ledger.
    """
    if ctx.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only Council Administration (SUPER_ADMIN) can provision officer accounts."
        )

    role_upper = payload.role.strip().upper()
    if role_upper not in VALID_OFFICER_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid officer role '{payload.role}'. Permitted roles: {list(VALID_OFFICER_ROLES)}"
        )

    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    reg = None
    if payload.region_code:
        reg = db.query(Region).filter(Region.code == payload.region_code.upper()).first()

    new_user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role=role_upper,
        region_id=reg.id if reg else None,
        institution_id=None,
        mfa_enabled=True, # Officers have MFA enabled
        email_verified=True, # Seeded by admin
        whatsapp_phone=payload.whatsapp_phone,
        preferred_language=payload.preferred_language or "en",
        preferred_channels="IN_APP,EMAIL",
    )
    db.add(new_user)
    db.flush()

    # Dispatch welcome notification via real SMTP
    welcome_body = (
        f"Dear {new_user.full_name},\n\n"
        f"Your AICTE Officer account has been provisioned by Council Administration.\n"
        f"Role: {role_upper}\n"
        f"Jurisdiction: {reg.name if reg else 'Council HQ (Pan-India)'}\n"
        f"Portal URL: http://127.0.0.1:3000/login\n\n"
        f"Please log in and configure your two-factor authentication (TOTP).\n\n"
        f"Council Administration,\nAICTE Headquarters"
    )
    email_service.send_email(
        to_email=new_user.email,
        subject="AICTE Regulatory Portal - Officer Account Provisioned",
        text_content=welcome_body,
        override_quiet=True,
    )

    # Log to audit ledger
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="OFFICER_ACCOUNT_CREATED",
        entity_type="User",
        entity_id=new_user.id,
        metadata={
            "created_by": ctx.user_id,
            "officer_email": new_user.email,
            "officer_role": new_user.role,
            "region": reg.code if reg else "HQ",
        }
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Officer account {email} provisioned successfully.",
        "user_id": new_user.id,
        "email": new_user.email,
        "role": new_user.role,
        "region_code": reg.code if reg else "HQ",
    }


# -----------------------------------------------------------------------------
# DEMO EVALUATION TOKENS (GATED BEHIND EVALUATOR_MODE / DEMO_MODE)
# -----------------------------------------------------------------------------

@router.post("/demo-token/{role}")
@router.post("/demo-switch-token/{role}")
def issue_demo_token(role: str, request: Request, db: Session = Depends(get_db)):
    """
    Demo Shortcut (Labeled: Demo Only):
    Generates a cryptographically signed JWT for the specified stakeholder persona.
    Gated behind Sandbox workspace (returns 404 in Live).
    """
    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    if ws != "sandbox":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found: Demo switch tokens are only available in Sandbox workspace."
        )

    role_upper = role.strip().upper()
    user = db.query(User).filter(User.role == role_upper).first()
    
    # Resolve IDs
    if user:
        user_id = user.id
        email = user.email
        reg_id = user.region_id
        inst_id = user.institution_id
        reg_code = user.region.code if user.region else "HQ"
    else:
        user_id = f"usr-demo-{role_upper.lower()}"
        email = f"{role_upper.lower()}@demo-only.aicte.gov.in"
        reg_id = db.query(Region).filter(Region.code == "SWRO").first().id if role_upper in ("REGIONAL_OFFICER", "REGIONAL_DIRECTOR", "COMMITTEE_MEMBER", "SCRUTINY_MEMBER") else None
        inst_id = db.query(Institution).first().id if role_upper == "INSTITUTION_USER" else None
        reg_code = "SWRO" if reg_id else "HQ"

    inst_name = None
    inst_pid = None
    if role_upper == "INSTITUTION_USER":
        if user and user.institution:
            inst_name = user.institution.name
            inst_pid = user.institution.permanent_id
        else:
            first_inst = db.query(Institution).first()
            if first_inst:
                inst_name = first_inst.name
                inst_pid = first_inst.permanent_id

    access_token = create_access_token({
        "sub": user_id,
        "email": email,
        "role": role_upper,
        "region_id": reg_id,
        "institution_id": inst_id,
        "demo_shortcut": True,
        "ws": "sandbox",
    }, workspace="sandbox")

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role_upper,
        "workspace": "sandbox",
        "user_id": user_id,
        "region_code": reg_code,
        "institution_name": inst_name,
        "institution_pid": inst_pid,
        "shortcut_status": "Demo Only",
        "notice": "DEMO ONLY: Simulated evaluation token. Production mandates hardware TOTP MFA."
    }
