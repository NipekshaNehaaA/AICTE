"""
=============================================================================
AUTHENTICATION & RBAC LOGIN ROUTER
=============================================================================
Implements JWT token issuance, PBKDF2 password verification,
Two-Factor Authentication (TOTP MFA), and Brute-Force lockout protection.
=============================================================================
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Region, Institution
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_mfa_code,
    check_account_lockout,
    record_login_failure,
    record_login_success,
)

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication & Access Control"])

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
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    message: str

@router.get("/personas")
def get_demo_personas(db: Session = Depends(get_db)):
    """Returns curated demo personas for 1-click evaluation."""
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
                "role": "BUREAU_OFFICER",
                "role_label": "Bureau Officer (HQ Approval Bureau)",
                "name": "Shri Anand Sharma (Director, Approval Bureau)",
                "email": "approval.bureau@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "Pan-India Bureau Oversight",
                "badge_color": "amber",
                "description": "Level 3 escalation handler, SAC/SHC hearing records",
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
                "role": "COMMITTEE_MEMBER",
                "role_label": "EVC Committee Expert Inspector",
                "name": "Prof. EVC Expert (SWRO)",
                "email": "expert.swro@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "SWRO",
                "region_name": "South-Western Region",
                "badge_color": "slate",
                "description": "Conflict of interest declaration, geotagged report submission",
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
                "role_label": "Member Secretary / Approving Authority",
                "name": "Prof. Rajive Kumar (Member Secretary)",
                "email": "member.secretary@aicte-india.org",
                "default_password": "DemoPassword@123",
                "region_code": "HQ",
                "region_name": "National Council (HQ)",
                "badge_color": "blossom-dark",
                "description": "Final council orders, Level 4 escalations, APH compiler",
            },
        ],
        "demo_mfa_code": "123456",
        "demo_password": "DemoPassword@123"
    }

@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Step 1 of Authentication:
    Validates email + password with PBKDF2 hash and checks brute-force lockout.
    Prompts for MFA verification if MFA is enabled on the account.
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

    # Password verified: reset failed counter
    record_login_success(email)

    reg_code = user.region.code if user.region else "HQ"

    # If MFA is enabled, mandate Step 2
    if user.mfa_enabled:
        return LoginResponse(
            mfa_required=True,
            email=user.email,
            full_name=user.full_name,
            role=user.role,
            region_code=reg_code,
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
    refresh_token = create_refresh_token({"sub": user.id})

    return LoginResponse(
        mfa_required=False,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        region_code=reg_code,
        access_token=access_token,
        refresh_token=refresh_token,
        message="Authentication successful."
    )

@router.post("/mfa-verify", response_model=LoginResponse)
def verify_mfa(payload: MFAVerifyRequest, db: Session = Depends(get_db)):
    """
    Step 2 of Authentication:
    Validates 6-digit Time-Based OTP (TOTP) code (Demo code: 123456).
    Issues JWT access & refresh tokens upon success.
    """
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User account not found.")

    if not verify_mfa_code(user.mfa_secret, payload.mfa_code.strip()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code. For demonstration, please enter '123456'."
        )

    reg_code = user.region.code if user.region else "HQ"

    access_token = create_access_token({
        "sub": user.id,
        "email": user.email,
        "role": user.role,
        "region_id": user.region_id,
        "institution_id": user.institution_id,
    })
    refresh_token = create_refresh_token({"sub": user.id})

    return LoginResponse(
        mfa_required=False,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        region_code=reg_code,
        access_token=access_token,
        refresh_token=refresh_token,
        message="Two-Factor Authentication verified. Access granted."
    )
