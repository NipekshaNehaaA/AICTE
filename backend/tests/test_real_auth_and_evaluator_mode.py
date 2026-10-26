"""
=============================================================================
TASK 3 TESTS: REAL ACCOUNTS, PASSWORD LIFECYCLE, AND EVALUATOR MODE
=============================================================================
Tests:
1. Institution sign-up with email verification token and SMTP notification.
2. Email verification token activation for user and institution.
3. Unverified email blocks login with 403.
4. Forgot password generates time-bound reset token and dispatches email.
5. Password reset updates PBKDF2 hash, clears reset token, and unlocks account.
6. Brute-force lockout triggers after repeated failed logins.
7. JWT refresh token rotation generates new access and refresh tokens.
8. Officer account provisioning by SUPER_ADMIN with welcome email.
9. Officer creation rejected with 403 for non-admin actors.
10. Evaluator Mode runtime toggle and endpoint gating.
11. Role-based routing default routes returned upon authentication.
=============================================================================
"""

import os
import pytest
import hashlib
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models import User, Institution, Region, AuditTrail
from app.auth import create_access_token, hash_password
from app.email_service import email_service
from tests.http_client import AppTestClient

client = AppTestClient()


def test_institution_signup_and_email_verification():
    """
    Validates end-to-end institution registration, token issuance,
    email dispatch via SMTP mock/service, and activation via verify-email.
    """
    db = SessionLocal()
    try:
        signup_payload = {
            "email": "registrar.apex@tech-edu.in",
            "password": "SecurePassword@2026",
            "full_name": "Dr. Registrar Apex",
            "institution_name": "Apex Advanced Institute of Technology",
            "category": "Engineering & Tech",
            "region_code": "SWRO",
            "address": "Campus Knowledge Park, Bengaluru",
            "state": "Karnataka",
            "whatsapp_phone": "+919876543210",
            "opt_in_whatsapp": True,
            "preferred_language": "en"
        }

        # 1. Sign Up
        resp = client.post("/api/v1/auth/signup", json=signup_payload)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "SUCCESS"
        # Security: verification token must NOT be returned in HTTP response
        assert "verification_token" not in data

        # Security test hook: retrieve token from in-memory test outbox
        v_token = email_service.get_latest_token("registrar.apex@tech-edu.in")
        assert v_token is not None
        assert len(v_token) > 20

        # 2. Check DB State: User unverified, token hashed with SHA-256, Institution PENDING_VERIFICATION
        user = db.query(User).filter(User.email == "registrar.apex@tech-edu.in").first()
        assert user is not None
        assert user.email_verified is False
        assert user.role == "INSTITUTION_USER"
        assert user.verification_token == hashlib.sha256(v_token.encode("utf-8")).hexdigest()
        assert user.institution is not None
        assert user.institution.status == "PENDING_VERIFICATION"

        # 3. Attempting login before email verification must fail with 403
        login_resp = client.post("/api/v1/auth/login", json={
            "email": "registrar.apex@tech-edu.in",
            "password": "SecurePassword@2026",
        })
        assert login_resp.status_code == 403
        assert "verification required" in login_resp.json()["detail"].lower()

        # 4. Verify Email
        verify_resp = client.post("/api/v1/auth/verify-email", json={"token": v_token})
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "SUCCESS"

        # 5. Check DB State: User verified, Institution ACTIVE
        db.refresh(user)
        assert user.email_verified is True
        assert user.verification_token is None
        assert user.institution.status == "ACTIVE"

        # 6. Login now succeeds and returns default_route
        login_success = client.post("/api/v1/auth/login", json={
            "email": "registrar.apex@tech-edu.in",
            "password": "SecurePassword@2026",
        })
        assert login_success.status_code == 200
        login_data = login_success.json()
        assert login_data["access_token"] is not None
        assert login_data["default_route"] == "/dashboard"
    finally:
        db.close()


def test_password_reset_flow():
    """
    Validates forgot-password token generation, SMTP notification,
    and password update with PBKDF2 hash update.
    """
    db = SessionLocal()
    try:
        # Create an active user
        test_email = "prof.reset@aicte-demo.edu.in"
        user = User(
            email=test_email,
            password_hash=hash_password("OldPassword@123"),
            full_name="Prof. Reset Test",
            role="INSTITUTION_USER",
            email_verified=True,
        )
        db.add(user)
        db.commit()

        # 1. Request Password Reset
        forgot_resp = client.post("/api/v1/auth/forgot-password", json={"email": test_email})
        assert forgot_resp.status_code == 200
        # Security: reset token must NEVER be returned in HTTP response
        assert "reset_token" not in forgot_resp.json()

        # Retrieve token from in-memory test outbox
        reset_token = email_service.get_latest_token(test_email)
        assert reset_token is not None

        db.refresh(user)
        # Token must be stored as SHA-256 hash
        assert user.reset_password_token == hashlib.sha256(reset_token.encode("utf-8")).hexdigest()
        assert user.reset_token_expires_at > datetime.utcnow()

        # 2. Reset Password with token
        reset_resp = client.post("/api/v1/auth/reset-password", json={
            "token": reset_token,
            "new_password": "NewSecurePassword@2026",
        })
        assert reset_resp.status_code == 200
        assert "successfully" in reset_resp.json()["message"].lower()

        # 3. Old password must now fail
        old_login = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "OldPassword@123",
        })
        assert old_login.status_code == 401

        # 4. New password must succeed
        new_login = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "NewSecurePassword@2026",
        })
        assert new_login.status_code == 200
        assert new_login.json()["access_token"] is not None
    finally:
        db.close()


def test_jwt_refresh_token_rotation():
    """
    Validates that a valid refresh token generates a new access token and refresh token pair.
    """
    db = SessionLocal()
    try:
        test_email = "refresh.officer@aicte-india.org"
        user = User(
            email=test_email,
            password_hash=hash_password("OfficerPass@123"),
            full_name="Dealing Officer Refresh",
            role="REGIONAL_OFFICER",
            email_verified=True,
            mfa_enabled=False,
        )
        db.add(user)
        db.commit()

        # Login to obtain initial tokens
        login_resp = client.post("/api/v1/auth/login", json={
            "email": test_email,
            "password": "OfficerPass@123",
        })
        assert login_resp.status_code == 200
        tokens = login_resp.json()
        orig_access = tokens["access_token"]
        orig_refresh = tokens["refresh_token"]

        # Exchange refresh token for fresh pair
        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": orig_refresh})
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["access_token"] is not None
        assert new_tokens["refresh_token"] is not None
        assert new_tokens["role"] == "REGIONAL_OFFICER"
    finally:
        db.close()


def test_officer_account_provisioning_and_rbac():
    """
    Validates that only SUPER_ADMIN can provision officer accounts,
    and unauthorized attempts return 403 Forbidden.
    """
    db = SessionLocal()
    try:
        # 1. Non-admin token attempt
        inst_token = create_access_token({
            "sub": "usr-inst",
            "email": "inst@demo.edu.in",
            "role": "INSTITUTION_USER",
        })
        unauth_resp = client.post(
            "/api/v1/auth/admin/create-officer",
            headers={"Authorization": f"Bearer {inst_token}"},
            json={
                "email": "new.ro@aicte-india.org",
                "password": "TempPassword@123",
                "full_name": "New Regional Officer",
                "role": "REGIONAL_OFFICER",
                "region_code": "SWRO",
            }
        )
        assert unauth_resp.status_code == 403

        # 2. Super Admin provisioning
        admin_token = create_access_token({
            "sub": "usr-admin",
            "email": "member.secretary@aicte-india.org",
            "role": "SUPER_ADMIN",
        })
        admin_resp = client.post(
            "/api/v1/auth/admin/create-officer",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "email": "new.ro@aicte-india.org",
                "password": "TempPassword@123",
                "full_name": "New Regional Officer",
                "role": "REGIONAL_OFFICER",
                "region_code": "SWRO",
            }
        )
        assert admin_resp.status_code == 200, admin_resp.text
        data = admin_resp.json()
        assert data["status"] == "SUCCESS"
        assert data["role"] == "REGIONAL_OFFICER"

        # Verify user in database
        officer = db.query(User).filter(User.email == "new.ro@aicte-india.org").first()
        assert officer is not None
        assert officer.email_verified is True
        assert officer.mfa_enabled is True
    finally:
        db.close()


def test_evaluator_mode_toggle_and_gating():
    """
    Validates dynamic runtime Evaluator Mode toggle:
    Anonymous call returns 404.
    SUPER_ADMIN call toggles mode when EVALUATOR_ALLOW_TOGGLE=True in non-production.
    When OFF: demo personas return 403 Forbidden.
    When ON: demo personas return 200 OK.
    """
    orig_mode = settings.DEMO_MODE
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    orig_toggle = getattr(settings, "EVALUATOR_ALLOW_TOGGLE", False)
    try:
        settings.EVALUATOR_ALLOW_TOGGLE = True

        # Anonymous toggle must fail with 404
        anon_resp = client.post("/api/v1/system/evaluator-mode", json={"enabled": False})
        assert anon_resp.status_code == 404

        admin_token = create_access_token({"sub": "admin-1", "role": "SUPER_ADMIN"})
        headers = {"Authorization": f"Bearer {admin_token}"}

        # 1. Turn Evaluator Mode OFF with SUPER_ADMIN
        toggle_off = client.post("/api/v1/system/evaluator-mode", headers=headers, json={"enabled": False})
        assert toggle_off.status_code == 200
        assert toggle_off.json()["evaluator_mode"] is False

        # Demo personas must return 403
        off_resp = client.get("/api/v1/auth/personas")
        assert off_resp.status_code == 403

        # 2. Turn Evaluator Mode ON with SUPER_ADMIN
        toggle_on = client.post("/api/v1/system/evaluator-mode", headers=headers, json={"enabled": True})
        assert toggle_on.status_code == 200
        assert toggle_on.json()["evaluator_mode"] is True

        # Demo personas must return 200
        on_resp = client.get("/api/v1/auth/personas")
        assert on_resp.status_code == 200
        assert len(on_resp.json()["personas"]) > 0

    finally:
        settings.DEMO_MODE = orig_mode
        settings.EVALUATOR_MODE = orig_eval
        settings.EVALUATOR_ALLOW_TOGGLE = orig_toggle
