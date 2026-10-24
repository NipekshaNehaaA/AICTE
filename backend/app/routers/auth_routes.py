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
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, status
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
)

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

class LoginResponse(BaseModel):
    mfa_required: bool
    email: str
    full_name: str
    role: str
    region_code: Optional[str] = None
    institution_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    default_route: Optional[str] = None
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
def get_demo_personas(db: Session = Depends(get_db)):
    """Returns curated demo personas for 1-click evaluation (Demo Only). Disabled if Evaluator / Demo Mode is False."""
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="1-click demo personas are disabled in production mode. Please enable Evaluator Mode.",
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
def login(payload: LoginRequest, db: Session = Depends(get_db)):
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

    # If MFA is enabled, mandate Step 2
    if user.mfa_enabled:
        return LoginResponse(
            mfa_required=True,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            region_code=reg_code,
            institution_id=user.institution_id,
            default_route=default_route,
            message="Password verified. Please enter the 6-digit TOTP code (Demo: 123456)."
        )

    # Direct token issuance if MFA disabled
    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
    })
    refresh_token = create_refresh_token({"sub": user.id, "role": user.role})

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
        access_token=access_token,
        refresh_token=refresh_token,
        default_route=default_route,
        message="Authentication successful."
    )

@router.post("/mfa-verify", response_model=LoginResponse)
def verify_mfa(payload: MFAVerifyRequest, db: Session = Depends(get_db)):
    """
    Step 2 of Authentication:
    Validates 6-digit Time-Based OTP (TOTP) code (Demo code: 123456).
    Issues JWT access & refresh tokens upon success, and logs audit entry.
    """
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    if not verify_mfa_code(user.mfa_secret, payload.mfa_code.strip()):
        if not settings.DEMO_MODE:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid TOTP code. Evaluator Mode is currently OFF (production mode). Please toggle 'Evaluator Mode: ON' at the top right to use demo PIN '123456'."
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code. For demonstration, please enter '123456'."
        )

    reg_code = user.region.code if user.region else "HQ"
    default_route = get_default_route_for_role(user.role)

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
    })
    refresh_token = create_refresh_token({"sub": user.id, "role": user.role})

    # Log MFA login to hash-chained audit ledger
    try:
        ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
        ScopedDAL(db, ctx).append_audit_entry(
            action_type="USER_LOGIN_MFA_SUCCESS",
            entity_type="User",
            entity_id=user.id,
            metadata={"email": user.email, "role": user.role, "mfa_used": True}
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
        access_token=access_token,
        refresh_token=refresh_token,
        default_route=default_route,
        message="Two-Factor Authentication verified. Access granted."
    )


# -----------------------------------------------------------------------------
# INSTITUTION SIGN-UP & EMAIL VERIFICATION (TASK 3)
# -----------------------------------------------------------------------------

@router.post("/signup")
def signup_institution(payload: SignUpRequest, db: Session = Depends(get_db)):
    """
    Real Institutional Sign-Up:
    1. Validates unique email address.
    2. Provisions new Institution record (status: PENDING_VERIFICATION).
    3. Provisions new User account (role: INSTITUTION_USER, email_verified: False).
    4. Generates cryptographic verification token and sends verification email via SMTP.
    5. Records immutable audit entry in hash-chained ledger.
    """
    email = payload.email.strip().lower()
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address is already registered."
        )

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

    # Generate cryptographic verification token
    verification_token = secrets.token_urlsafe(32)

    # Create User
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        role="INSTITUTION_USER",
        region_id=reg.id if reg else None,
        institution_id=inst.id,
        mfa_enabled=False,
        email_verified=False,
        verification_token=verification_token,
        whatsapp_phone=payload.whatsapp_phone,
        opt_in_whatsapp=payload.opt_in_whatsapp,
        preferred_language=payload.preferred_language or "en",
        preferred_channels="IN_APP,EMAIL",
    )
    db.add(user)
    db.flush()

    # Send verification email via real SMTP
    email_body = (
        f"Dear {user.full_name},\n\n"
        f"Welcome to the AICTE Regulatory Approval & Compliance Automation Platform.\n"
        f"Your institution registration for '{inst.name}' (PID: {inst.permanent_id}) has been created.\n\n"
        f"Please verify your email address to activate your account:\n"
        f"Verification Token: {verification_token}\n\n"
        f"Or click: http://127.0.0.1:3000/verify-email?token={verification_token}\n\n"
        f"Regulatory Regards,\nAICTE Approval Bureau"
    )
    email_service.send_email(
        to_email=user.email,
        subject="Verify Your AICTE Institution Account",
        text_content=email_body,
        override_quiet=True,
    )

    # Log to audit ledger
    ctx = RequestContext(user_id=user.id, role="INSTITUTION_USER", region_id=reg.id if reg else None, institution_id=inst.id)
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="USER_SIGNUP",
        entity_type="User",
        entity_id=user.id,
        metadata={
            "email": user.email,
            "institution_id": inst.id,
            "permanent_id": inst.permanent_id,
            "institution_name": inst.name,
        }
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Institution registered successfully. A verification link has been sent to your email.",
        "email": user.email,
        "institution_id": inst.id,
        "permanent_id": inst.permanent_id,
        "verification_token": verification_token,
    }

@router.post("/verify-email")
def verify_email(payload: VerifyEmailRequest, db: Session = Depends(get_db)):
    """
    Validates cryptographic verification token, activates user and institution accounts.
    """
    clean_token = payload.token.strip()
    user = db.query(User).filter(User.verification_token == clean_token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    user.email_verified = True
    user.verification_token = None

    if user.institution:
        user.institution.status = "ACTIVE"

    # Log audit entry
    ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="EMAIL_VERIFIED",
        entity_type="User",
        entity_id=user.id,
        metadata={"email": user.email, "institution_id": user.institution_id}
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Email verified successfully. You may now log in to the portal.",
        "email": user.email,
    }


# -----------------------------------------------------------------------------
# PASSWORD RESET FLOW (FORGOT / RESET) (TASK 3)
# -----------------------------------------------------------------------------

@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiates password reset:
    Generates time-bound token (1 hour) and dispatches reset instructions via SMTP.
    """
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    
    reset_token = None
    if user:
        reset_token = secrets.token_urlsafe(32)
        user.reset_password_token = reset_token
        user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
        
        email_body = (
            f"Dear {user.full_name},\n\n"
            f"A password reset was requested for your AICTE Regulatory Portal account.\n"
            f"Password Reset Token: {reset_token}\n\n"
            f"This token is valid for 60 minutes.\n"
            f"If you did not request this, please contact AICTE security administrator immediately.\n\n"
            f"Regulatory Regards,\nAICTE Security Operations"
        )
        email_service.send_email(
            to_email=user.email,
            subject="AICTE Portal Password Reset Request",
            text_content=email_body,
            override_quiet=True,
        )

        ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
        ScopedDAL(db, ctx).append_audit_entry(
            action_type="PASSWORD_RESET_REQUESTED",
            entity_type="User",
            entity_id=user.id,
            metadata={"email": user.email}
        )
        db.commit()

    return {
        "status": "SUCCESS",
        "message": "If the account exists, password reset instructions have been dispatched.",
        "reset_token": reset_token, # included for dev/automated test verification
    }

@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Completes password reset: validates token, expiry, updates PBKDF2 hash, and clears lockout.
    """
    clean_token = payload.token.strip()
    user = db.query(User).filter(User.reset_password_token == clean_token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unrecognized password reset token."
        )

    if user.reset_token_expires_at and user.reset_token_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired. Please request a fresh reset link."
        )

    # Update password hash
    user.password_hash = hash_password(payload.new_password)
    user.reset_password_token = None
    user.reset_token_expires_at = None

    # Clear any lockout
    record_login_success(user.email)

    ctx = RequestContext(user_id=user.id, role=user.role, region_id=user.region_id, institution_id=user.institution_id)
    ScopedDAL(db, ctx).append_audit_entry(
        action_type="PASSWORD_RESET_SUCCESS",
        entity_type="User",
        entity_id=user.id,
        metadata={"email": user.email}
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "message": "Password updated successfully. Please log in with your new credentials.",
    }


# -----------------------------------------------------------------------------
# JWT REFRESH TOKEN ROTATION (TASK 3)
# -----------------------------------------------------------------------------

@router.post("/refresh")
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    Validates cryptographic refresh token and issues fresh access and refresh token pair.
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

    new_access = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
    })
    new_refresh = create_refresh_token({"sub": user.id, "role": user.role})

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
def issue_demo_token(role: str, db: Session = Depends(get_db)):
    """
    Demo Shortcut (Labeled: Demo Only):
    Generates a cryptographically signed JWT for the specified stakeholder persona.
    Gated behind EVALUATOR_MODE / DEMO_MODE flag.
    """
    if not settings.DEMO_MODE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Role switching and demo tokens are disabled in production mode (DEMO_MODE=False)."
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

    access_token = create_access_token({
        "sub": user_id,
        "email": email,
        "role": role_upper,
        "region_id": reg_id,
        "institution_id": inst_id,
        "demo_shortcut": True,
    })

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": role_upper,
        "user_id": user_id,
        "region_code": reg_code,
        "shortcut_status": "Demo Only",
        "notice": "DEMO ONLY: Simulated evaluation token. Production mandates hardware TOTP MFA."
    }
