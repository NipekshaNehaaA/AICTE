"""
=============================================================================
TEST SUITE: JWT SECURITY, ALGORITHM PINNING, EXPIRY, MFA & DEMO_MODE GATING
=============================================================================
Validates:
1. Secret key loaded from environment variable (JWT_SECRET_KEY / SECRET_KEY)
2. Algorithm strictly pinned to HS256; 'alg=none' and untrusted algorithms rejected
3. Token expiration enforced; expired tokens rejected with 401
4. Signature tampering detected and rejected
5. MFA verified server-side before any token is issued:
   - /login does NOT return access token for MFA-enabled accounts
   - Protected endpoints reject requests without token
   - /mfa-verify issues token ONLY upon valid TOTP verification
6. DEMO_MODE gating:
   - When DEMO_MODE=False: TOTP 123456 rejected, /personas 403, /demo-token 403
   - When DEMO_MODE=True: TOTP 123456 accepted, /personas 200, /demo-token 200
=============================================================================
"""

import os
import sys
from datetime import datetime, timedelta
import jwt
import pytest
from app.config import settings
from app.auth import (
    create_access_token,
    decode_token,
    verify_mfa_code,
)
from tests.http_client import AppTestClient

client = AppTestClient()

def test_jwt_secret_loaded_from_config():
    """Validates that JWT secret is loaded from environment variable or settings."""
    assert settings.SECRET_KEY is not None
    assert len(settings.SECRET_KEY) >= 32
    assert settings.ALGORITHM == "HS256"

def test_jwt_algorithm_pinned_rejects_none():
    """Negative Test: Rejects tokens with alg=none or untrusted algorithms."""
    import base64
    import json

    def b64url(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")

    header = {"alg": "none", "typ": "JWT"}
    payload = {
        "sub": "attacker",
        "role": "SUPER_ADMIN",
        "exp": int((datetime.utcnow() + timedelta(hours=1)).timestamp()),
    }
    raw_token = f"{b64url(json.dumps(header).encode())}.{b64url(json.dumps(payload).encode())}."

    with pytest.raises(ValueError) as exc:
        decode_token(raw_token)
    assert "not permitted" in str(exc.value) or "Invalid token" in str(exc.value)

    # HTTP endpoint test: Passing alg=none token must return 401
    resp = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {raw_token}"})
    assert resp.status_code == 401

def test_jwt_token_expiry_enforced():
    """Negative Test: Expired tokens are strictly rejected."""
    expired_time = datetime.utcnow() - timedelta(minutes=10)
    to_encode = {
        "sub": "usr-ro-01",
        "role": "REGIONAL_OFFICER",
        "exp": expired_time,
        "type": "access",
    }
    expired_token = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    with pytest.raises(ValueError) as exc:
        decode_token(expired_token)
    assert "expired" in str(exc.value).lower()

    # HTTP endpoint test: Passing expired token must return 401
    resp = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
    assert "expired" in resp.json().get("detail", "").lower()

def test_jwt_tampered_signature_rejected():
    """Negative Test: Tokens with modified signature or altered payload are rejected."""
    valid_token = create_access_token({"sub": "usr-ro-01", "role": "REGIONAL_OFFICER"})
    # Tamper with the last 4 characters of the signature
    tampered_token = valid_token[:-4] + "ABCD"

    with pytest.raises(ValueError) as exc:
        decode_token(tampered_token)
    assert "invalid" in str(exc.value).lower()

    resp = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401

def test_mfa_verified_server_side_before_token_issuance():
    """
    Validates that /login NEVER returns an access token if MFA is enabled.
    Token is issued ONLY after server-side MFA verification via /mfa-verify.
    """
    # 1. Step 1: Login with valid credentials for regional officer (MFA enabled)
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "ro.swro@aicte-india.org",
        "password": "DemoPassword@123",
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert login_data["mfa_required"] is True
    assert login_data.get("access_token") is None, "Security Breach: /login issued access token before MFA!"
    assert login_data.get("refresh_token") is None

    # 2. Attempt to access protected endpoint without token -> 401
    prot_resp = client.get("/api/v1/applications")
    assert prot_resp.status_code == 401

    # 3. Step 2: Attempt MFA verification with invalid code -> 401
    bad_mfa_resp = client.post("/api/v1/auth/mfa-verify", json={
        "email": "ro.swro@aicte-india.org",
        "mfa_code": "000000",
    })
    assert bad_mfa_resp.status_code == 401

    # 4. Step 2: Valid MFA code -> 200 with verified access_token
    good_mfa_resp = client.post("/api/v1/auth/mfa-verify", json={
        "email": "ro.swro@aicte-india.org",
        "mfa_code": "123456",
    })
    assert good_mfa_resp.status_code == 200
    mfa_data = good_mfa_resp.json()
    assert mfa_data["access_token"] is not None
    assert mfa_data["role"] == "REGIONAL_OFFICER"

    # 5. Access protected endpoint using newly issued token -> 200
    auth_resp = client.get("/api/v1/applications", headers={"Authorization": f"Bearer {mfa_data['access_token']}"})
    assert auth_resp.status_code == 200

def test_demo_mode_gating():
    """
    Validates that demo shortcuts (TOTP 123456, personas, demo token endpoint)
    are strictly gated behind the DEMO_MODE setting.
    """
    orig_demo_mode = settings.DEMO_MODE

    try:
        # TEST A: When DEMO_MODE is False (Production mode)
        settings.DEMO_MODE = False

        # 1. TOTP 123456 must be rejected
        assert verify_mfa_code("JBSWY3DPEHPK3PXP", "123456") is False

        # 2. /personas endpoint must return 403 Forbidden
        p_resp = client.get("/api/v1/auth/personas")
        assert p_resp.status_code == 403
        assert "disabled in production" in p_resp.json().get("detail", "")

        # 3. /demo-token endpoint must return 403 Forbidden
        dt_resp = client.post("/api/v1/auth/demo-token/SUPER_ADMIN")
        assert dt_resp.status_code == 403
        assert "disabled in production" in dt_resp.json().get("detail", "")

        # TEST B: When DEMO_MODE is True (Demo mode)
        settings.DEMO_MODE = True

        # 1. TOTP 123456 accepted
        assert verify_mfa_code("JBSWY3DPEHPK3PXP", "123456") is True

        # 2. /personas returns 200 with personas list
        p_resp = client.get("/api/v1/auth/personas")
        assert p_resp.status_code == 200
        assert "personas" in p_resp.json()

        # 3. /demo-token returns 200 with signed JWT
        dt_resp = client.post("/api/v1/auth/demo-token/SUPER_ADMIN")
        assert dt_resp.status_code == 200
        assert dt_resp.json()["role"] == "SUPER_ADMIN"
        assert "access_token" in dt_resp.json()

        # 4. /demo-switch-token alias returns 200 with signed JWT
        dst_resp = client.post("/api/v1/auth/demo-switch-token/SUPER_ADMIN")
        assert dst_resp.status_code == 200
        assert dst_resp.json()["role"] == "SUPER_ADMIN"
        assert "access_token" in dst_resp.json()

    finally:
        settings.DEMO_MODE = orig_demo_mode

def test_demo_mode_defaults_to_false(monkeypatch):
    """Validates that DEMO_MODE defaults to false when the environment variable is unset."""
    monkeypatch.delenv("DEMO_MODE", raising=False)
    from app.config import Settings
    fresh_settings = Settings()
    assert fresh_settings.DEMO_MODE is False

def test_startup_fails_without_jwt_secret_in_non_demo_mode(monkeypatch):
    """Validates that backend startup fails fast with RuntimeError if JWT_SECRET is missing in non-demo mode."""
    monkeypatch.delenv("JWT_SECRET", raising=False)
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    from app.main import on_startup
    orig_demo = settings.DEMO_MODE

    try:
        settings.DEMO_MODE = False
        with pytest.raises(RuntimeError) as exc:
            on_startup()
        assert "JWT_SECRET environment variable must be set" in str(exc.value)
    finally:
        settings.DEMO_MODE = orig_demo

def test_startup_fails_with_weak_jwt_secret_in_non_demo_mode(monkeypatch):
    """Validates that backend startup fails fast with RuntimeError if JWT_SECRET is weak (<32 chars or default placeholder)."""
    monkeypatch.setenv("JWT_SECRET", "short_secret")
    from app.main import on_startup
    orig_demo = settings.DEMO_MODE

    try:
        settings.DEMO_MODE = False
        with pytest.raises(RuntimeError) as exc:
            on_startup()
        assert "too weak" in str(exc.value)
    finally:
        settings.DEMO_MODE = orig_demo

def test_status_lookup_otp_gated_by_demo_mode():
    """
    Validates that the public status lookup endpoint gates OTP 123456 behind DEMO_MODE:
    - In non-demo mode (DEMO_MODE=False): returns 403 Forbidden
    - In demo mode (DEMO_MODE=True): accepts 123456
    """
    orig_demo = settings.DEMO_MODE

    try:
        # TEST A: When DEMO_MODE is False
        settings.DEMO_MODE = False
        resp_prod = client.post("/api/v1/workflow/status-lookup", json={
            "application_no": "APP-2026-SWRO-0001",
            "otp": "123456",
        })
        assert resp_prod.status_code == 403
        assert "disabled when DEMO_MODE=false" in resp_prod.json().get("detail", "")

        # TEST B: When DEMO_MODE is True
        settings.DEMO_MODE = True
        resp_demo = client.post("/api/v1/workflow/status-lookup", json={
            "application_no": "APP-2026-SWRO-0001",
            "otp": "123456",
        })
        # If application exists, returns 200; if not, returns 404 (not 403 / 401 OTP error)
        assert resp_demo.status_code in (200, 404)
        if resp_demo.status_code == 200:
            data = resp_demo.json()
            assert "application_no" in data
            assert "timeline" in data

    finally:
        settings.DEMO_MODE = orig_demo

if __name__ == "__main__":
    pytest.main(["-v", __file__])
