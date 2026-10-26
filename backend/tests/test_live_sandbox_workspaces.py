"""
Automated Test Suite for TASK 1: Live / Sandbox Workspaces & Cross-Workspace Security Attacks.
Verifies:
1. Strict workspace isolation between 'live' (aicte_live.db) and 'sandbox' (aicte_sandbox.db).
2. Cross-workspace token attacks:
   - Sandbox tokens rejected by Live endpoints with 403.
   - Live tokens rejected by Sandbox-only endpoints with 404.
3. Sandbox-only endpoints return 404 for Live tokens or X-Workspace: live:
   - /api/v1/auth/demo-personas
   - /api/v1/auth/demo-token/{role}
   - /api/v1/demo/time-travel/*
   - /api/v1/demo/scenario/*
   - /api/v1/demo/sandbox-override
4. Bypass PIN 123456 strictly rejected in Live workspace.
5. Real messages override:
   - In sandbox with override: sends to evaluator override recipient with 'Sandbox: sent to <override>'.
   - In sandbox without override: synthetic addresses skipped.
   - In live: sends to real recipient directly.
6. Zero runtime mutation: /api/v1/system/evaluator-mode returns 404.
"""

import os
import pytest
from tests.http_client import AppTestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config import settings
from app.auth import create_access_token, hash_password
from app.models import Base, User, Institution, Region
from app.workspace import set_sandbox_override, get_sandbox_override, current_workspace_var
from app.email_service import email_service
from app.database import get_engine, get_session_maker, init_db

client = AppTestClient()

@pytest.fixture(autouse=True)
def setup_workspaces():
    """Ensure both live and sandbox databases are initialized and seeded."""
    init_db("live")
    init_db("sandbox")
    from app.seed import seed_database
    seed_database("live")
    seed_database("sandbox")
    yield

def test_system_mode_and_no_runtime_mutation():
    """Verify runtime mutation of settings.EVALUATOR_MODE is disabled and returns 404."""
    res_get = client.get("/api/v1/system/mode", headers={"X-Workspace": "sandbox"})
    assert res_get.status_code == 200
    assert res_get.json()["evaluator_mode"] is True

    res_live = client.get("/api/v1/system/mode", headers={"X-Workspace": "live"})
    assert res_live.status_code == 200
    assert res_live.json()["evaluator_mode"] is False

    # Attempt runtime mutation
    res_post = client.post("/api/v1/system/evaluator-mode", json={"enabled": True})
    assert res_post.status_code == 404

def test_sandbox_token_rejected_by_live_endpoints_with_403():
    """A token issued for sandbox workspace MUST be rejected when presenting to Live."""
    sandbox_token = create_access_token(
        data={"sub": "usr-ro-01", "role": "REGIONAL_OFFICER", "email": "ro.swro@aicte-india.org"},
        workspace="sandbox"
    )

    # Calling an endpoint with X-Workspace: live while presenting a sandbox token
    headers = {
        "Authorization": f"Bearer {sandbox_token}",
        "X-Workspace": "live",
    }
    response = client.get("/api/v1/applications", headers=headers)
    assert response.status_code == 403
    assert "Workspace Violation" in response.json()["detail"]

def test_live_token_rejected_by_sandbox_endpoints_with_403():
    """A token issued for live workspace MUST be rejected when presenting to Sandbox."""
    live_token = create_access_token(
        data={"sub": "usr-admin-01", "role": "SUPER_ADMIN", "email": "admin@aicte-india.org"},
        workspace="live"
    )

    headers = {
        "Authorization": f"Bearer {live_token}",
        "X-Workspace": "sandbox",
    }
    response = client.get("/api/v1/applications", headers=headers)
    assert response.status_code == 403
    assert "Workspace Violation" in response.json()["detail"]

def test_sandbox_only_endpoints_return_404_in_live():
    """Verify all demo/persona/time-travel endpoints return 404 for Live callers."""
    live_token = create_access_token(
        data={"sub": "usr-admin-01", "role": "SUPER_ADMIN", "email": "admin@aicte-india.org"},
        workspace="live"
    )
    live_headers = {"Authorization": f"Bearer {live_token}", "X-Workspace": "live"}

    # 1. Personas endpoint
    res_personas = client.get("/api/v1/auth/demo-personas", headers={"X-Workspace": "live"})
    assert res_personas.status_code == 404

    # 2. Demo token endpoint
    res_token = client.post("/api/v1/auth/demo-token/REGIONAL_OFFICER", headers={"X-Workspace": "live"})
    assert res_token.status_code == 404

    # 3. Time travel status
    res_tt_status = client.get("/api/v1/demo/time-travel/status", headers=live_headers)
    assert res_tt_status.status_code == 404

    # 4. Time travel advance
    res_tt_adv = client.post("/api/v1/demo/time-travel/advance", json={"days": 7}, headers=live_headers)
    assert res_tt_adv.status_code == 404

    # 5. Demo scenario run
    res_scenario = client.post("/api/v1/demo/scenario/run", headers=live_headers)
    assert res_scenario.status_code == 404

    # 6. Sandbox override settings
    res_override = client.get("/api/v1/demo/sandbox-override", headers=live_headers)
    assert res_override.status_code == 404

def test_sandbox_endpoints_accessible_in_sandbox():
    """Verify demo endpoints succeed when called in Sandbox workspace."""
    sb_token = create_access_token(
        data={"sub": "usr-ro-01", "role": "REGIONAL_OFFICER", "email": "ro.swro@aicte-india.org"},
        workspace="sandbox"
    )
    sb_headers = {"Authorization": f"Bearer {sb_token}", "X-Workspace": "sandbox"}

    # Personas accessible
    res_personas = client.get("/api/v1/auth/demo-personas", headers={"X-Workspace": "sandbox"})
    assert res_personas.status_code == 200
    assert len(res_personas.json()["personas"]) > 0

    # Demo token generation accessible
    res_token = client.post("/api/v1/auth/demo-token/REGIONAL_OFFICER", headers={"X-Workspace": "sandbox"})
    assert res_token.status_code == 200
    assert "access_token" in res_token.json()
    assert res_token.json()["workspace"] == "sandbox"

    # Time travel status accessible
    res_tt = client.get("/api/v1/demo/time-travel/status", headers=sb_headers)
    assert res_tt.status_code == 200
    assert res_tt.json()["workspace"] == "sandbox"

def test_pin_123456_bypass_rejected_in_live():
    """Bypass PIN 123456 is strictly rejected in Live workspace for public tracking & MFA."""
    # 1. Public status lookup
    res_public_live = client.post(
        "/api/v1/workflow/status-lookup",
        json={"application_no": "APP-2026-TEST", "otp": "123456"},
        headers={"X-Workspace": "live"}
    )
    assert res_public_live.status_code == 403
    assert "strictly disabled in Live" in res_public_live.json()["detail"]

    # 2. MFA verification in Live
    res_mfa_live = client.post(
        "/api/v1/auth/mfa-verify",
        json={"email": "officer@aicte-india.org", "mfa_code": "123456"},
        headers={"X-Workspace": "live"}
    )
    assert res_mfa_live.status_code in (400, 403, 404)
    if res_mfa_live.status_code == 403:
        assert "Sandbox test PIN '123456' is strictly rejected" in res_mfa_live.json()["detail"]

def test_evaluator_sandbox_override_routing():
    """Real messages in sandbox go ONLY to evaluator override, never to fake institutions."""
    from app.email_service import get_test_outbox, clear_test_outbox
    clear_test_outbox()

    # 1. Set override
    set_sandbox_override("evaluator.proof@gmail.com", "+919876543210")
    overrides = get_sandbox_override()
    assert overrides["override_email"] == "evaluator.proof@gmail.com"

    # 2. In sandbox context with override
    token_var = current_workspace_var.set("sandbox")
    try:
        dispatch = email_service.send_email(
            to_email="fake.principal.101@fictional-aicte.edu.in",
            subject="Test Application Notice",
            text_content="Your compliance notice is attached.",
        )
        assert dispatch["recipient"] == "evaluator.proof@gmail.com"
        assert dispatch["original_recipient"] == "fake.principal.101@fictional-aicte.edu.in"
        assert dispatch["sandbox_note"] == "Sandbox: sent to evaluator.proof@gmail.com"

        outbox = get_test_outbox()
        assert len(outbox) > 0
        assert outbox[-1]["to"] == "evaluator.proof@gmail.com"
        assert outbox[-1]["sandbox_note"] == "Sandbox: sent to evaluator.proof@gmail.com"
    finally:
        current_workspace_var.reset(token_var)

    # 3. Reset override to None
    set_sandbox_override(None, None)
    token_var = current_workspace_var.set("sandbox")
    try:
        dispatch_skipped = email_service.send_email(
            to_email="fake.principal.102@fictional-aicte.edu.in",
            subject="Test Skipped Notice",
            text_content="Notice content",
        )
        assert dispatch_skipped["status"] == "SANDBOX_SKIPPED_NO_OVERRIDE"
        assert "skipped synthetic recipient" in dispatch_skipped["sandbox_note"]
    finally:
        current_workspace_var.reset(token_var)

def test_clean_live_database_has_no_demo_data():
    """Verify aicte_live.db contains zero synthetic institutions."""
    live_sm = get_session_maker("live")
    db_live = live_sm()
    try:
        institutions = db_live.query(Institution).all()
        # In live workspace, no synthetic colleges from DEMO catalog are seeded
        assert len(institutions) == 0
    finally:
        db_live.close()

    # And sandbox database has synthetic institutions
    sb_sm = get_session_maker("sandbox")
    db_sb = sb_sm()
    try:
        sb_institutions = db_sb.query(Institution).all()
        assert len(sb_institutions) > 0
    finally:
        db_sb.close()
