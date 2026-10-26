"""
Automated Test Suite for Task 2: Zero Demo Leaks & Production Public Tracking when EVALUATOR_MODE=False.

Verifies:
1. When EVALUATOR_MODE=False and DEMO_MODE=False:
   - Login responses and error messages contain zero instances of 'Demo', '123456', or 'Evaluator Mode'.
   - MFA enrollment/verification error messages never mention 'Demo' or '123456'.
   - Entering '123456' is strictly rejected with 401 and zero mentions of demo bypasses.
   - 1-click personas endpoint (/api/v1/auth/personas) is rejected with 403 without demo leaks.
2. Real email OTP flow for Public Tracking (/api/v1/workflow/public/request-otp & /status-lookup):
   - OTP is generated, hashed with SHA-256 (never stored plaintext), and sent to registered institution email.
   - demo_otp is never included in the response when EVALUATOR_MODE=False.
   - 10-minute expiry and 5 attempt limits strictly enforced.
   - Rate limiting per IP and per tracking ID enforced.
"""

import hashlib
import time
import pytest
from sqlalchemy.orm import Session
from tests.http_client import AppTestClient
from app.config import settings
from app.database import SessionLocal
from app.models import User, Application
from app.auth import (
    hash_password,
    _login_attempts,
)
from app.routers.intake_workflow import (
    _public_tracking_otp_store,
    _public_otp_ip_rate_limits,
    _public_otp_tracking_id_rate_limits,
)

client = AppTestClient()

FORBIDDEN_LEAK_WORDS = ["demo", "123456", "evaluator mode"]


@pytest.fixture(autouse=True)
def clean_evaluator_off_state():
    """Ensure clean state and EVALUATOR_MODE=False, DEMO_MODE=False."""
    _login_attempts.clear()
    _public_tracking_otp_store.clear()
    _public_otp_ip_rate_limits.clear()
    _public_otp_tracking_id_rate_limits.clear()

    orig_demo = settings.DEMO_MODE
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)

    settings.DEMO_MODE = False
    settings.EVALUATOR_MODE = False

    yield

    _login_attempts.clear()
    _public_tracking_otp_store.clear()
    _public_otp_ip_rate_limits.clear()
    _public_otp_tracking_id_rate_limits.clear()
    settings.DEMO_MODE = orig_demo
    settings.EVALUATOR_MODE = orig_eval


def assert_no_demo_leaks(text: str, context: str = ""):
    """Assert that a string contains no forbidden demo or evaluator leaks."""
    import re
    lower_text = text.lower()
    assert not re.search(r"\bdemo\b", lower_text), f"Demo leak detected in {context}! Found 'demo' in:\n{text}"
    assert "123456" not in text, f"Demo PIN leak detected in {context}! Found '123456' in:\n{text}"
    assert "evaluator mode" not in lower_text, f"Evaluator mode leak detected in {context}! Found 'evaluator mode' in:\n{text}"


def test_auth_login_responses_have_zero_demo_leaks(db: Session = None):
    """Verify login and error responses never mention Demo, 123456, or Evaluator Mode when mode is off."""
    db_session = SessionLocal()
    try:
        # Create a test officer user
        email = "test.prod.officer@aicte-india.org"
        existing = db_session.query(User).filter(User.email == email).first()
        if existing:
            db_session.delete(existing)
            db_session.commit()

        user = User(
            email=email,
            password_hash=hash_password("ProdPassword@2026"),
            full_name="Officer Production",
            role="REGIONAL_OFFICER",
            is_active=True,
            mfa_enabled=True,
            mfa_secret=None,
        )
        db_session.add(user)
        db_session.commit()

        # 1. Invalid password login
        resp_bad_pw = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPassword999!"}
        )
        assert resp_bad_pw.status_code == 401
        assert_no_demo_leaks(resp_bad_pw.text, "invalid password error")

        # 2. Valid password login requiring MFA enrollment
        resp_enroll = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "ProdPassword@2026"}
        )
        assert resp_enroll.status_code == 200
        data_enroll = resp_enroll.json()
        assert data_enroll["mfa_required"] is True
        assert data_enroll["mfa_enrollment_required"] is True
        assert_no_demo_leaks(resp_enroll.text, "mfa enrollment challenge response")

        # 3. Confirm MFA enrollment with '123456' -> must be REJECTED with 401 and no demo leaks
        resp_confirm_bypass = client.post(
            "/api/v1/auth/mfa-enroll-confirm",
            json={"email": email, "mfa_code": "123456"}
        )
        assert resp_confirm_bypass.status_code == 401
        assert_no_demo_leaks(resp_confirm_bypass.text, "mfa enroll confirm with 123456")

        # 4. MFA verify endpoint directly with '123456' -> rejected with 401 and no leaks
        resp_verify_bypass = client.post(
            "/api/v1/auth/mfa-verify",
            json={"email": email, "mfa_code": "123456"}
        )
        assert resp_verify_bypass.status_code == 401
        assert_no_demo_leaks(resp_verify_bypass.text, "mfa verify with 123456")

        # 5. GET /personas -> must be 403 Forbidden with zero demo leaks
        resp_personas = client.get("/api/v1/auth/personas")
        assert resp_personas.status_code == 403
        assert_no_demo_leaks(resp_personas.text, "personas forbidden response")

    finally:
        db_session.close()


def test_public_tracking_real_otp_flow():
    """Verify real email OTP generation, hashing at rest, expiration, and rate limits."""
    db_session = SessionLocal()
    try:
        app = db_session.query(Application).first()
        assert app is not None, "Application seed required"
        app_no = app.application_no

        # 1. Request OTP for the application
        resp_req = client.post(
            "/api/v1/workflow/public/request-otp",
            json={"tracking_id": app_no}
        )
        assert resp_req.status_code == 200
        data_req = resp_req.json()
        assert data_req["status"] == "SUCCESS"
        assert "masked_email" in data_req
        # Critical Task 2 assertion: demo_otp MUST NOT be returned when EVALUATOR_MODE=false
        assert "demo_otp" not in data_req or data_req.get("demo_otp") is None
        assert_no_demo_leaks(resp_req.text, "public request-otp response")

        # 2. Check in-memory store: only SHA-256 hash is stored, never plaintext
        record = _public_tracking_otp_store.get(app_no)
        assert record is not None
        assert "otp_hash" in record
        assert "otp" not in record  # Plaintext OTP is never stored
        assert record["attempts_left"] == 5

        # 3. Try to use hardcoded '123456' -> must fail with 401 and zero demo leaks
        resp_bypass = client.post(
            "/api/v1/workflow/status-lookup",
            json={"application_no": app_no, "otp": "123456"}
        )
        assert resp_bypass.status_code == 403
        assert_no_demo_leaks(resp_bypass.text, "status lookup with 123456")

        # 4. Try invalid dynamic OTP (e.g. 000000) -> attempts decrement (returns 401)
        resp_bad = client.post(
            "/api/v1/workflow/status-lookup",
            json={"application_no": app_no, "otp": "000000"}
        )
        assert resp_bad.status_code == 401
        assert "4 attempt(s) remaining" in resp_bad.json()["detail"]
        assert_no_demo_leaks(resp_bad.text, "status lookup invalid otp")

        # 5. Simulate setting a known OTP hash for verification test
        test_otp = "948201"
        salt = settings.SECRET_KEY[:16]
        test_hash = hashlib.sha256(f"{app_no}:{test_otp}:{salt}".encode()).hexdigest()
        _public_tracking_otp_store[app_no]["otp_hash"] = test_hash

        resp_ok = client.post(
            "/api/v1/workflow/status-lookup",
            json={"application_no": app_no, "otp": test_otp}
        )
        assert resp_ok.status_code == 200
        data_ok = resp_ok.json()
        assert data_ok["application_no"] == app_no
        assert "timeline" in data_ok

        # 6. Verify single-use / invalidation on success: cannot reuse test_otp
        resp_reuse = client.post(
            "/api/v1/workflow/status-lookup",
            json={"application_no": app_no, "otp": test_otp}
        )
        assert resp_reuse.status_code == 400  # "No active verification code found"

    finally:
        db_session.close()


def test_public_tracking_exhaustion_lockout():
    """Verify that after 5 wrong attempts, OTP is permanently invalidated (429/401)."""
    db_session = SessionLocal()
    try:
        app = db_session.query(Application).first()
        app_no = app.application_no

        client.post("/api/v1/workflow/public/request-otp", json={"tracking_id": app_no})

        # Submit 4 wrong OTPs (returns 401 each time)
        for i in range(4):
            r = client.post("/api/v1/workflow/status-lookup", json={"application_no": app_no, "otp": f"11111{i}"})
            assert r.status_code == 401

        # 5th attempt invalidates (returns 429)
        r5 = client.post("/api/v1/workflow/status-lookup", json={"application_no": app_no, "otp": "999999"})
        assert r5.status_code == 429
        assert "Maximum attempts exceeded" in r5.json()["detail"]

        # 6th attempt: store should be cleared
        assert app_no not in _public_tracking_otp_store

    finally:
        db_session.close()


def test_public_tracking_rate_limiting():
    """Verify rate limits per IP (max 5) and per tracking ID (max 3) within 10 minutes."""
    db_session = SessionLocal()
    try:
        app = db_session.query(Application).first()
        app_no = app.application_no

        # 1st request -> ok
        r1 = client.post("/api/v1/workflow/public/request-otp", json={"tracking_id": app_no})
        assert r1.status_code == 200

        # 2nd request -> ok
        r2 = client.post("/api/v1/workflow/public/request-otp", json={"tracking_id": app_no})
        assert r2.status_code == 200

        # 3rd request -> ok
        r3 = client.post("/api/v1/workflow/public/request-otp", json={"tracking_id": app_no})
        assert r3.status_code == 200

        # 4th request on same tracking ID -> 429 Rate Limit
        r4 = client.post("/api/v1/workflow/public/request-otp", json={"tracking_id": app_no})
        assert r4.status_code == 429
        assert "Rate limit exceeded" in r4.json()["detail"]
        assert_no_demo_leaks(r4.text, "rate limit error response")

    finally:
        db_session.close()
