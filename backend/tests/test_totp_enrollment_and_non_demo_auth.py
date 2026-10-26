"""
Automated Test Suite for Task 1: Officer TOTP Enrollment & Production Auth (DEMO_MODE=False).

Verifies:
1. TOTP enrollment happy path: initial login returns mfa_enrollment_required + QR + URI,
   confirmation validates code, encrypts secret at rest, generates 8 recovery codes, issues JWT tokens.
2. Wrong TOTP code during enrollment is rejected (401).
3. Replay protection: reusing the same 6-digit TOTP code within the 30-second window is rejected (401).
4. Recovery code single-use: emergency recovery code works once, second attempt with same code fails.
5. Sandbox bypass PIN '123456' strictly rejected when DEMO_MODE/EVALUATOR_MODE is OFF.
6. Admin MFA reset: SUPER_ADMIN resets officer MFA, logged in hash-chained audit ledger,
   officer is required to re-enroll on next login.
7. Brute-force lockout: MFA verification failures lock out the user after 5 attempts.
"""

import json
import time
import pyotp
import pytest
from sqlalchemy.orm import Session
from tests.http_client import AppTestClient
from app.config import settings
from app.database import SessionLocal
from app.models import User, AuditTrail
from app.auth import (
    hash_password,
    create_access_token,
    decrypt_mfa_secret,
    encrypt_mfa_secret,
    _login_attempts,
)

client = AppTestClient()


@pytest.fixture(autouse=True)
def clean_state():
    """Ensure clean failure tracker and restored settings around each test."""
    _login_attempts.clear()
    orig_demo = settings.DEMO_MODE
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    yield
    _login_attempts.clear()
    settings.DEMO_MODE = orig_demo
    settings.EVALUATOR_MODE = orig_eval


def create_test_officer(db: Session, email: str, enrolled: bool = False, secret_plain: str = None) -> tuple[User, str]:
    """Helper to provision a fresh officer account for testing."""
    password = "OfficerSecretPass@2026"
    pw_hash = hash_password(password)

    # Delete existing user if any
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        db.delete(existing)
        db.commit()

    officer = User(
        email=email,
        password_hash=pw_hash,
        full_name="Dealing Officer Test",
        role="REGIONAL_OFFICER",
        email_verified=True,
        mfa_enabled=True,
    )
    if enrolled and secret_plain:
        officer.mfa_secret = encrypt_mfa_secret(secret_plain)
    db.add(officer)
    db.commit()
    db.refresh(officer)
    return officer, password


def test_totp_enrollment_happy_path():
    """
    1. First successful password login for an officer with no secret returns
       mfa_enrollment_required, provisioning_uri, and QR code data URI.
    2. Confirmation endpoint validates TOTP code, encrypts secret at rest,
       and returns 8 recovery codes.
    """
    db = SessionLocal()
    try:
        email = "totp.enroll.happy@aicte-india.org"
        officer, password = create_test_officer(db, email, enrolled=False)

        # Step 1: Login with password -> triggers enrollment requirement
        login_res = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        assert login_res.status_code == 200
        body = login_res.json()
        assert body["mfa_required"] is True
        assert body["mfa_enrollment_required"] is True
        assert "qr_code_base64" in body
        assert body["qr_code_base64"].startswith("data:image/png;base64,")
        assert "provisioning_uri" in body
        assert "otpauth://totp/" in body["provisioning_uri"]
        assert "manual_entry_key" in body
        manual_key = body["manual_entry_key"]
        assert len(manual_key) >= 16

        # Step 2: Confirm enrollment with valid TOTP code generated from manual_key
        totp = pyotp.TOTP(manual_key)
        valid_code = totp.now()

        confirm_res = client.post("/api/v1/auth/mfa-enroll-confirm", json={
            "email": email,
            "mfa_code": valid_code
        })
        assert confirm_res.status_code == 200
        confirm_body = confirm_res.json()
        assert confirm_body["access_token"] is not None
        assert confirm_body["refresh_token"] is not None
        assert "recovery_codes" in confirm_body
        recovery_codes = confirm_body["recovery_codes"]
        assert len(recovery_codes) == 8
        for rc in recovery_codes:
            assert "-" in rc  # Formatted like XXXX-XXXX

        # Step 3: Verify DB state - secret is encrypted at rest, not plain text
        db.refresh(officer)
        assert officer.mfa_secret is not None
        assert officer.mfa_secret != manual_key
        assert decrypt_mfa_secret(officer.mfa_secret) == manual_key
        assert officer.mfa_pending_secret is None
        assert officer.last_mfa_timestep is not None
        assert officer.mfa_recovery_codes is not None
        stored_hashes = json.loads(officer.mfa_recovery_codes)
        assert len(stored_hashes) == 8
    finally:
        db.close()


def test_totp_enrollment_wrong_code_rejected():
    """
    Submitting an incorrect 6-digit TOTP code during enrollment confirmation
    must be rejected with 401 Unauthorized.
    """
    db = SessionLocal()
    try:
        email = "totp.enroll.wrong@aicte-india.org"
        officer, password = create_test_officer(db, email, enrolled=False)

        # Step 1: Initiate enrollment
        login_res = client.post("/api/v1/auth/login", json={
            "email": email,
            "password": password
        })
        assert login_res.status_code == 200

        # Step 2: Send invalid TOTP code
        confirm_res = client.post("/api/v1/auth/mfa-enroll-confirm", json={
            "email": email,
            "mfa_code": "000999"
        })
        assert confirm_res.status_code == 401
        assert "Invalid verification code" in confirm_res.json()["detail"]

        # User remains unenrolled
        db.refresh(officer)
        assert officer.mfa_secret is None
    finally:
        db.close()


def test_totp_replay_of_same_code_rejected():
    """
    Submitting the exact same 6-digit TOTP code twice within the same
    30-second window must be rejected (replay attack prevention).
    """
    db = SessionLocal()
    try:
        email = "totp.replay.test@aicte-india.org"
        plain_secret = pyotp.random_base32()
        officer, password = create_test_officer(db, email, enrolled=True, secret_plain=plain_secret)

        totp = pyotp.TOTP(plain_secret)
        code = totp.now()

        # First verification succeeds
        res1 = client.post("/api/v1/auth/mfa-verify", json={
            "email": email,
            "mfa_code": code
        })
        assert res1.status_code == 200
        assert res1.json()["access_token"] is not None

        # Immediate second verification with SAME code must fail (replay protection)
        res2 = client.post("/api/v1/auth/mfa-verify", json={
            "email": email,
            "mfa_code": code
        })
        assert res2.status_code == 401
        assert "already been used" in res2.json()["detail"]
    finally:
        db.close()


def test_recovery_code_single_use():
    """
    An emergency recovery code must successfully authenticate the user once,
    and be permanently consumed so a second attempt with the same code fails.
    """
    db = SessionLocal()
    try:
        email = "totp.recovery.test@aicte-india.org"
        officer, password = create_test_officer(db, email, enrolled=False)

        # Enroll and obtain recovery codes
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
        manual_key = login_res.json()["manual_entry_key"]
        code = pyotp.TOTP(manual_key).now()
        confirm_res = client.post("/api/v1/auth/mfa-enroll-confirm", json={"email": email, "mfa_code": code})
        assert confirm_res.status_code == 200
        recovery_codes = confirm_res.json()["recovery_codes"]
        first_code = recovery_codes[0]

        # Use recovery code to authenticate
        verify_res1 = client.post("/api/v1/auth/mfa-verify", json={
            "email": email,
            "mfa_code": first_code
        })
        assert verify_res1.status_code == 200
        assert verify_res1.json()["access_token"] is not None

        # Re-use the exact same recovery code -> must fail
        verify_res2 = client.post("/api/v1/auth/mfa-verify", json={
            "email": email,
            "mfa_code": first_code
        })
        assert verify_res2.status_code == 401

        # Check DB: remaining recovery codes reduced from 8 to 7
        db.refresh(officer)
        remaining_hashes = json.loads(officer.mfa_recovery_codes)
        assert len(remaining_hashes) == 7
    finally:
        db.close()


def test_demo_code_123456_rejected_when_evaluator_mode_off():
    """
    When DEMO_MODE=False and EVALUATOR_MODE=False:
    Entering '123456' must be rejected with 401 Unauthorized,
    and error detail must NOT mention '123456' or 'Demo'.
    """
    settings.DEMO_MODE = False
    settings.EVALUATOR_MODE = False

    db = SessionLocal()
    try:
        email = "totp.nodemo.test@aicte-india.org"
        plain_secret = pyotp.random_base32()
        officer, password = create_test_officer(db, email, enrolled=True, secret_plain=plain_secret)

        res = client.post("/api/v1/auth/mfa-verify", json={
            "email": email,
            "mfa_code": "123456"
        })
        assert res.status_code == 401
        err_msg = res.json()["detail"]
        assert "123456" not in err_msg
        assert "Demo" not in err_msg
        assert "Evaluator Mode" not in err_msg
    finally:
        db.close()


def test_admin_reset_mfa_audited():
    """
    Super Admin can reset an officer's MFA settings.
    - Action is recorded in SHA-256 hash-chained audit ledger.
    - Officer's stored secret and recovery codes are wiped.
    - Officer is required to re-enroll on next login.
    - Non-admin callers receive 403 Forbidden.
    """
    db = SessionLocal()
    try:
        # Create Super Admin
        admin_email = "superadmin.mfa.test@aicte-india.org"
        admin_user = db.query(User).filter(User.email == admin_email).first()
        if not admin_user:
            admin_user = User(
                email=admin_email,
                password_hash=hash_password("SuperAdminPass@2026"),
                full_name="Super Admin MFA Auditor",
                role="SUPER_ADMIN",
                email_verified=True,
                mfa_enabled=False,
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)

        admin_token = create_access_token({
            "sub": admin_user.id,
            "email": admin_user.email,
            "role": admin_user.role,
        })

        # Create enrolled officer
        officer_email = "officer.to.reset@aicte-india.org"
        plain_secret = pyotp.random_base32()
        officer, officer_pw = create_test_officer(db, officer_email, enrolled=True, secret_plain=plain_secret)

        # 1. Non-admin attempt should be 403 Forbidden
        officer_token = create_access_token({
            "sub": officer.id,
            "email": officer.email,
            "role": officer.role,
        })
        non_admin_res = client.post(
            f"/api/v1/auth/admin/reset-mfa/{officer.id}",
            headers={"Authorization": f"Bearer {officer_token}"}
        )
        assert non_admin_res.status_code == 403

        # 2. Super Admin executes reset
        reset_res = client.post(
            f"/api/v1/auth/admin/reset-mfa/{officer.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert reset_res.status_code == 200
        assert reset_res.json()["status"] == "SUCCESS"

        # 3. Check officer DB state
        db.refresh(officer)
        assert officer.mfa_secret is None
        assert officer.mfa_pending_secret is None
        assert officer.mfa_recovery_codes is None
        assert officer.last_mfa_timestep is None
        assert officer.mfa_enabled is True

        # 4. Verify audit ledger entry
        audit_entry = db.query(AuditTrail).filter(
            AuditTrail.action_type == "MFA_RESET_BY_ADMIN",
            AuditTrail.entity_id == officer.id
        ).first()
        assert audit_entry is not None
        assert audit_entry.actor_id == admin_user.id
        assert audit_entry.actor_role == "SUPER_ADMIN"
        meta = json.loads(audit_entry.metadata_json)
        assert meta["target_email"] == officer_email

        # 5. On next password login, officer is prompted for enrollment
        next_login_res = client.post("/api/v1/auth/login", json={
            "email": officer_email,
            "password": officer_pw
        })
        assert next_login_res.status_code == 200
        assert next_login_res.json()["mfa_enrollment_required"] is True
    finally:
        db.close()


def test_mfa_lockout_after_consecutive_failures():
    """
    5 consecutive failed MFA attempts triggers account lockout (429 Too Many Requests).
    """
    settings.DEMO_MODE = False
    settings.EVALUATOR_MODE = False

    db = SessionLocal()
    try:
        email = "totp.lockout.test@aicte-india.org"
        plain_secret = pyotp.random_base32()
        officer, password = create_test_officer(db, email, enrolled=True, secret_plain=plain_secret)

        # 5 failed attempts
        for i in range(5):
            res = client.post("/api/v1/auth/mfa-verify", json={
                "email": email,
                "mfa_code": f"00000{i}"
            })
            assert res.status_code == 401

        # 6th attempt should be locked out (429)
        locked_res = client.post("/api/v1/auth/mfa-verify", json={
            "email": email,
            "mfa_code": "000006"
        })
        assert locked_res.status_code == 429
        assert "locked" in locked_res.json()["detail"].lower()
    finally:
        db.close()
