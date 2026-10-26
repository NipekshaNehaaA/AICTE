"""
Security Regression Test Suite attacking Defects 1 through 6.
SIH26262 AICTE Prototype.
"""

import os
import pytest
import hashlib
from datetime import datetime, timedelta
from tests.http_client import AppTestClient
from app.main import app, on_startup
from app.config import settings
from app.database import SessionLocal
from app.models import User, Institution, Region, AuditTrail
from app.auth import (
    create_access_token,
    create_refresh_token,
    verify_mfa_code,
    hash_password,
    clear_rate_limits,
    decode_token,
)
from app.email_service import email_service


@pytest.fixture
def client():
    return AppTestClient(app)


def test_regression_defect_1_production_evaluator_mode_toggle_rejected(client):
    """
    REGRESSION ATTACK 1:
    With production env: POST /system/evaluator-mode (anonymous, and as an ordinary user)
    returns 404/401 and settings never change; /auth/demo-token/* stays 403 afterwards;
    MFA 123456 stays rejected afterwards.
    """
    orig_env = settings.ENV
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    orig_demo = settings.DEMO_MODE
    orig_toggle = getattr(settings, "EVALUATOR_ALLOW_TOGGLE", False)

    try:
        settings.ENV = "production"
        settings.EVALUATOR_MODE = False
        settings.DEMO_MODE = False
        settings.EVALUATOR_ALLOW_TOGGLE = False

        # 1. Anonymous attack on /api/v1/system/evaluator-mode
        resp_anon = client.post("/api/v1/system/evaluator-mode", json={"enabled": True})
        assert resp_anon.status_code == 404, f"Expected 404, got {resp_anon.status_code}: {resp_anon.text}"

        # Route alias /system/evaluator-mode
        resp_alias = client.post("/system/evaluator-mode", json={"enabled": True})
        assert resp_alias.status_code == 404

        # Verify settings NEVER changed
        assert settings.EVALUATOR_MODE is False
        assert settings.DEMO_MODE is False

        # 2. Attack as an ordinary user (e.g. INSTITUTION)
        institution_token = create_access_token({"sub": "user-inst-1", "role": "INSTITUTION"})
        resp_user = client.post(
            "/api/v1/system/evaluator-mode",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {institution_token}"},
        )
        assert resp_user.status_code == 404, f"Expected 404, got {resp_user.status_code}: {resp_user.text}"

        # Verify settings STILL never changed
        assert settings.EVALUATOR_MODE is False
        assert settings.DEMO_MODE is False

        # 3. GET /system/mode must return strictly {evaluator_mode: bool}. No version, no environment name.
        mode_resp = client.get("/api/v1/system/mode")
        assert mode_resp.status_code == 200
        mode_data = mode_resp.json()
        assert mode_data == {"evaluator_mode": False}
        assert "version" not in mode_data
        assert "environment" not in mode_data
        assert "demo_mode" not in mode_data

        # 4. /auth/demo-token/SUPER_ADMIN must remain 403 Forbidden
        demo_resp = client.post("/api/v1/auth/demo-token/SUPER_ADMIN")
        assert demo_resp.status_code == 403, f"Expected 403 Forbidden, got {demo_resp.status_code}"

        # 5. MFA 123456 bypass stays strictly rejected
        assert verify_mfa_code("JBSWY3DPEHPK3PXP", "123456") is False
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.mfa_enabled == True).first()
            if not user:
                user = db.query(User).first()
            if user:
                mfa_resp = client.post("/api/v1/auth/mfa-verify", json={"email": user.email, "mfa_code": "123456"})
                assert mfa_resp.status_code == 401
        finally:
            db.close()

    finally:
        settings.ENV = orig_env
        settings.EVALUATOR_MODE = orig_eval
        settings.DEMO_MODE = orig_demo
        settings.EVALUATOR_ALLOW_TOGGLE = orig_toggle


def test_regression_defect_6_boot_refusal_when_production_and_demo_flag():
    """
    REGRESSION ATTACK 6:
    Boot refuses when ENV=production and a demo flag is true.
    """
    orig_env = settings.ENV
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    orig_demo = settings.DEMO_MODE

    try:
        settings.ENV = "production"
        settings.DEMO_MODE = True
        settings.EVALUATOR_MODE = False

        with pytest.raises(RuntimeError) as exc_info:
            on_startup()
        assert "Startup refused" in str(exc_info.value) or "Boot refused" in str(exc_info.value)

        # Same if EVALUATOR_MODE is True
        settings.DEMO_MODE = False
        settings.EVALUATOR_MODE = True

        with pytest.raises(RuntimeError) as exc_info:
            on_startup()
        assert "Startup refused" in str(exc_info.value) or "Boot refused" in str(exc_info.value)

    finally:
        settings.ENV = orig_env
        settings.EVALUATOR_MODE = orig_eval
        settings.DEMO_MODE = orig_demo


def test_regression_defect_2_password_reset_security(client):
    """
    REGRESSION ATTACK 2:
    - forgot-password: response bodies for real and fake emails are identical.
    - No token field in any response in any mode.
    - Token delivered only via outbound email (in-memory test outbox).
    - Token works exactly once via reset-password.
    - Reused and expired tokens fail (400).
    - Existing sessions/refresh tokens die upon reset.
    - Audit entries written.
    """
    clear_rate_limits()
    email_service.clear_outbox()
    db = SessionLocal()
    try:
        real_email = "security.victim@aicte-india.org"
        fake_email = "nonexistent.attacker@aicte-india.org"

        # Ensure user exists with active credentials and known token_version
        user = db.query(User).filter(User.email == real_email).first()
        if not user:
            user = User(
                email=real_email,
                password_hash=hash_password("OriginalPassword@2026"),
                full_name="Security Test Victim",
                role="INSTITUTION_USER",
                email_verified=True,
                is_active=True,
                token_version=1,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # 1. Compare responses for real vs fake emails
        resp_real = client.post("/api/v1/auth/forgot-password", json={"email": real_email})
        resp_fake = client.post("/api/v1/auth/forgot-password", json={"email": fake_email})

        assert resp_real.status_code == 200
        assert resp_fake.status_code == 200
        assert resp_real.json() == resp_fake.json(), "Response leaked account existence!"
        assert "reset_token" not in resp_real.json()
        assert "token" not in resp_real.json()

        # 2. Token captured only from test outbox
        raw_token = email_service.get_latest_token(real_email)
        assert raw_token is not None
        assert len(raw_token) > 20

        # Check DB stores ONLY the SHA-256 hash
        db.refresh(user)
        expected_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        assert user.reset_password_token == expected_hash

        # 3. Simulate existing session with pre-reset refresh token
        old_refresh_token = create_refresh_token({
            "sub": user.id,
            "role": user.role,
            "token_version": user.token_version,
        })

        # 4. Reset password using valid token
        reset_resp = client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "NewSafePassword@2026!",
        })
        assert reset_resp.status_code == 200
        assert "reset_token" not in reset_resp.json()

        # 5. Token works exactly once: Replay attack fails
        replay_resp = client.post("/api/v1/auth/reset-password", json={
            "token": raw_token,
            "new_password": "AnotherPassword@2026!",
        })
        assert replay_resp.status_code == 400
        assert "invalid or expired" in replay_resp.json()["detail"].lower()

        # 6. Expired token fails
        expired_token = "expired_raw_token_xyz"
        user.reset_password_token = hashlib.sha256(expired_token.encode("utf-8")).hexdigest()
        user.reset_token_expires_at = datetime.utcnow() - timedelta(minutes=5)
        db.commit()

        exp_resp = client.post("/api/v1/auth/reset-password", json={
            "token": expired_token,
            "new_password": "YetAnotherPassword@2026!",
        })
        assert exp_resp.status_code == 400
        assert "invalid or expired" in exp_resp.json()["detail"].lower()

        # 7. Old sessions die: refresh token with old token_version is rejected
        refresh_resp = client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh_token})
        assert refresh_resp.status_code == 401, "Old session refresh token was not revoked!"

        # 8. Audit ledger entries
        audits = db.query(AuditTrail).filter(
            AuditTrail.entity_id == user.id,
            AuditTrail.action_type.in_(["PASSWORD_RESET_REQUESTED", "PASSWORD_RESET_USED"])
        ).all()
        assert len(audits) >= 2
    finally:
        db.close()


def test_regression_defect_3_signup_email_verification_security(client):
    """
    REGRESSION ATTACK 3:
    - POST /auth/signup never returns verification_token in response.
    - Duplicate email signup returns identical response without revealing account existence.
    - Cannot log in until emailed verification link is used.
    - Token stored hashed (SHA-256), single use, 24h expiry.
    - Link works once; reuse fails (400).
    """
    clear_rate_limits()
    email_service.clear_outbox()
    db = SessionLocal()
    try:
        signup_email = "new.institution@reg-aicte.edu.in"
        # Cleanup if previously exists
        old = db.query(User).filter(User.email == signup_email).first()
        if old:
            db.delete(old)
            db.commit()

        signup_payload = {
            "email": signup_email,
            "password": "InstitutionSecure@2026!",
            "full_name": "Dr. Principal New Institution",
            "institution_name": "New Institute of Science",
            "category": "Engineering & Tech",
            "region_code": "SWRO",
        }

        # 1. Sign up
        signup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
        assert signup_resp.status_code == 200
        resp_data = signup_resp.json()
        assert "verification_token" not in resp_data
        assert "token" not in resp_data

        # 2. Cannot log in until verified
        login_resp = client.post("/api/v1/auth/login", json={
            "email": signup_email,
            "password": "InstitutionSecure@2026!",
        })
        assert login_resp.status_code == 403
        assert "verification required" in login_resp.json()["detail"].lower()

        # 3. Duplicate signup attempt reveals nothing
        dup_resp = client.post("/api/v1/auth/signup", json=signup_payload)
        assert dup_resp.status_code == 200
        assert "verification_token" not in dup_resp.json()
        assert dup_resp.json()["status"] == "SUCCESS"

        # 4. Retrieve token from test outbox
        v_token = email_service.get_latest_token(signup_email)
        assert v_token is not None
        assert len(v_token) > 20

        # DB stores only SHA-256 hash
        user = db.query(User).filter(User.email == signup_email).first()
        assert user is not None
        assert user.email_verified is False
        assert user.verification_token == hashlib.sha256(v_token.encode("utf-8")).hexdigest()
        assert user.verification_token_expires_at > datetime.utcnow()

        # 5. Verify email with token
        verify_resp = client.post("/api/v1/auth/verify-email", json={"token": v_token})
        assert verify_resp.status_code == 200
        assert verify_resp.json()["status"] == "SUCCESS"

        # 6. Reusing verification token fails (single use)
        replay_verify = client.post("/api/v1/auth/verify-email", json={"token": v_token})
        assert replay_verify.status_code == 400
        assert "invalid or expired" in replay_verify.json()["detail"].lower()

        # 7. Login now succeeds
        success_login = client.post("/api/v1/auth/login", json={
            "email": signup_email,
            "password": "InstitutionSecure@2026!",
        })
        assert success_login.status_code == 200
        assert success_login.json()["access_token"] is not None
    finally:
        db.close()


def test_regression_defect_7_brute_force_rate_limiting(client):
    """
    REGRESSION ATTACK 7:
    Brute force: login, reset, verify, and signup endpoints rate limit (429)
    and audit the attempts.
    """
    clear_rate_limits()
    db = SessionLocal()
    try:
        # 1. Rate limit forgot-password
        target_email = "ratelimit.target@aicte-india.org"
        hit_429 = False
        for _ in range(7):
            r = client.post("/api/v1/auth/forgot-password", json={"email": target_email})
            if r.status_code == 429:
                hit_429 = True
                break
        assert hit_429, "forgot-password endpoint did not rate-limit brute force requests!"

        # 2. Rate limit reset-password token guessing
        hit_reset_429 = False
        for i in range(12):
            r = client.post("/api/v1/auth/reset-password", json={
                "token": f"bogus_guess_{i}",
                "new_password": "NewSafePassword@2026!",
            })
            if r.status_code == 429:
                hit_reset_429 = True
                break
        assert hit_reset_429, "reset-password endpoint did not rate-limit token guessing!"

        # 3. Check audit log for rate limit actions
        audits = db.query(AuditTrail).filter(
            AuditTrail.action_type.in_(["PASSWORD_RESET_RATE_LIMITED", "SIGNUP_RATE_LIMITED"])
        ).all()
        assert len(audits) >= 1
    finally:
        clear_rate_limits()
        db.close()


def test_regression_defect_4_production_demo_users_disabled_and_rejected(client):
    """
    REGRESSION ATTACK 4:
    - Production boot has no demo users.
    - A DB with demo users gets them disabled (is_active=False).
    - Logging in with DemoPassword@123 fails for every user.
    - Active user matching default password hash fails boot.
    """
    orig_env = settings.ENV
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    orig_demo = settings.DEMO_MODE

    db = SessionLocal()
    try:
        settings.ENV = "production"
        settings.EVALUATOR_MODE = False
        settings.DEMO_MODE = False

        # 1. Create a demo user with default password DemoPassword@123
        demo_email = "principal.19999999@fictional-aicte.edu.in"
        demo_user = db.query(User).filter(User.email == demo_email).first()
        if not demo_user:
            demo_user = User(
                email=demo_email,
                password_hash=hash_password("DemoPassword@123"),
                full_name="Dr. Principal Seeded Demo",
                role="INSTITUTION_USER",
                is_active=True,
                email_verified=True,
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        else:
            demo_user.password_hash = hash_password("DemoPassword@123")
            demo_user.is_active = True
            db.commit()

        # 2. Trigger production startup hygiene check
        on_startup()

        # 3. Demo user must now be disabled (is_active = False)
        db.refresh(demo_user)
        assert demo_user.is_active is False, "Seeded demo user was not disabled during production boot!"

        # 4. Logging in with DemoPassword@123 must fail with 403 Forbidden
        login_resp = client.post("/api/v1/auth/login", json={
            "email": demo_email,
            "password": "DemoPassword@123",
        })
        assert login_resp.status_code == 403, f"Expected 403, got {login_resp.status_code}: {login_resp.text}"
        assert "disabled" in login_resp.json()["detail"].lower()

        # 5. Boot self-check failure if an ACTIVE user still has default password hash
        active_demo = User(
            email="rogue.active@aicte-india.org",
            password_hash=hash_password("DemoPassword@123"),
            full_name="Rogue Active Account",
            role="REGIONAL_OFFICER",
            is_active=True,
            email_verified=True,
        )
        db.add(active_demo)
        db.commit()

        with pytest.raises(RuntimeError) as exc_info:
            on_startup()
        assert "Production Security Boot Refused" in str(exc_info.value)

        # Cleanup rogue user
        db.delete(active_demo)
        db.commit()

    finally:
        settings.ENV = orig_env
        settings.EVALUATOR_MODE = orig_eval
        settings.DEMO_MODE = orig_demo
        db.close()


def test_regression_defect_5_admin_first_login_password_change_enforced(client):
    """
    REGRESSION ATTACK 5:
    - Admin first login with ADMIN_INITIAL_PASSWORD returns restricted token.
    - Only permits POST /auth/change-password.
    - Calling any other API returns 403 Forbidden.
    - Weak passwords (< 12 chars), breach list, equal to email, unchanged password rejected.
    - Valid new password updates hash, clears must_change_password, and unlocks full access.
    """
    clear_rate_limits()
    db = SessionLocal()
    try:
        admin_email = "admin.firstlogin@aicte-india.org"
        initial_pw = "AdminInitialPass@2026"

        user = db.query(User).filter(User.email == admin_email).first()
        if not user:
            user = User(
                email=admin_email,
                password_hash=hash_password(initial_pw),
                full_name="First Login Admin",
                role="SUPER_ADMIN",
                must_change_password=True,
                is_active=True,
                email_verified=True,
                mfa_enabled=False,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            user.password_hash = hash_password(initial_pw)
            user.must_change_password = True
            user.mfa_enabled = False
            db.commit()

        # 1. Log in with initial password
        login_resp = client.post("/api/v1/auth/login", json={
            "email": admin_email,
            "password": initial_pw,
        })
        assert login_resp.status_code == 200
        login_data = login_resp.json()
        assert login_data["must_change_password"] is True
        restricted_token = login_data["access_token"]
        assert restricted_token is not None

        headers = {"Authorization": f"Bearer {restricted_token}"}

        # 2. Attacking other APIs with restricted token MUST return 403
        api_attempts = [
            client.get("/api/v1/compliance/documents", headers=headers),
            client.get("/api/v1/alerts/notifications", headers=headers),
            client.get("/api/v1/audit/trail", headers=headers),
        ]
        for resp in api_attempts:
            assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
            assert "password change required" in resp.json()["detail"].lower()

        # 3. Policy rejections on POST /auth/change-password
        # 3a. Weak (< 12 chars)
        r_weak = client.post("/api/v1/auth/change-password", json={"new_password": "Short1@"}, headers=headers)
        assert r_weak.status_code == 400
        assert "at least 12 characters" in r_weak.json()["detail"].lower()

        # 3b. Breached password
        r_breach = client.post("/api/v1/auth/change-password", json={"new_password": "Password@123456"}, headers=headers)
        assert r_breach.status_code == 400
        assert "breached" in r_breach.json()["detail"].lower() or "common" in r_breach.json()["detail"].lower()

        # 3c. Equal to email
        r_email = client.post("/api/v1/auth/change-password", json={"new_password": admin_email}, headers=headers)
        assert r_email.status_code == 400
        assert "email" in r_email.json()["detail"].lower()

        # 3d. Same as current password
        r_same = client.post("/api/v1/auth/change-password", json={"new_password": initial_pw}, headers=headers)
        assert r_same.status_code == 400
        assert "differ" in r_same.json()["detail"].lower()

        # 4. Valid strong password change succeeds
        new_strong_pw = "BrandNewSuperSecurePass@2026!"
        r_success = client.post("/api/v1/auth/change-password", json={"new_password": new_strong_pw}, headers=headers)
        assert r_success.status_code == 200
        new_token = r_success.json()["access_token"]
        assert new_token is not None

        # 5. DB state updated
        db.refresh(user)
        assert user.must_change_password is False

        # 6. New token can now access protected APIs
        new_headers = {"Authorization": f"Bearer {new_token}"}
        app_resp = client.get("/api/v1/compliance/documents", headers=new_headers)
        assert app_resp.status_code == 200

        # 7. Old restricted token remains blocked
        old_resp = client.get("/api/v1/compliance/documents", headers=headers)
        assert old_resp.status_code == 403

        # 8. Audit trail recorded
        audit = db.query(AuditTrail).filter(
            AuditTrail.entity_id == user.id,
            AuditTrail.action_type == "PASSWORD_CHANGED"
        ).first()
        assert audit is not None
    finally:
        db.close()


def test_regression_defect_8_e2e_json_response_leak_scan(client):
    """
    REGRESSION ATTACK 8:
    Scan every JSON response in the e2e smoke run for the strings:
    "reset_token", "verification_token", "123456", "DemoPassword"
    when running in production mode and fail on any hit.
    """
    clear_rate_limits()
    orig_env = settings.ENV
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    orig_demo = settings.DEMO_MODE

    forbidden_patterns = ["reset_token", "verification_token", "123456", "DemoPassword"]

    try:
        settings.ENV = "production"
        settings.EVALUATOR_MODE = False
        settings.DEMO_MODE = False

        endpoints_to_probe = [
            ("GET", "/api/v1/system/mode", None),
            ("GET", "/system/mode", None),
            ("POST", "/api/v1/system/evaluator-mode", {"enabled": True}),
            ("GET", "/api/v1/auth/personas", None),
            ("POST", "/api/v1/auth/demo-token/SUPER_ADMIN", None),
            ("POST", "/api/v1/auth/demo-token/REGIONAL_OFFICER", None),
            ("POST", "/api/v1/auth/login", {"email": "scan.test@aicte-india.org", "password": "WrongPassword@123"}),
            ("POST", "/api/v1/auth/forgot-password", {"email": "scan.user@aicte-india.org"}),
            ("POST", "/api/v1/auth/reset-password", {"token": "scan_token_1234", "new_password": "NewSafePassword@2026!"}),
            ("POST", "/api/v1/auth/signup", {
                "email": "scan.signup@reg-aicte.edu.in",
                "password": "SecurePassword@2026!",
                "full_name": "Dr. Scan Test",
                "institution_name": "Scanner Institute of Tech",
            }),
            ("POST", "/api/v1/auth/verify-email", {"token": "invalid_probe_token"}),
        ]

        for method, path, payload in endpoints_to_probe:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path, json=payload or {})

            raw_text = resp.text
            for pattern in forbidden_patterns:
                assert pattern not in raw_text, (
                    f"CRITICAL SECURITY LEAK: Forbidden pattern '{pattern}' found in response from {method} {path}!\n"
                    f"Response text: {raw_text}"
                )
    finally:
        settings.ENV = orig_env
        settings.EVALUATOR_MODE = orig_eval
        settings.DEMO_MODE = orig_demo
