"""
Unit tests for Time Travel and Scripted Scenario Demo Engine.
Validates:
1. Time travel status, advance (+N days), and clock reset.
2. Individual execution of all 8 steps in the evaluator scenario:
   - Step 1: APH Upload & Ingestion
   - Step 2: Rules Update & Compilation
   - Step 3: Application Ingestion & Table 2.3 Auto-Routing
   - Step 4: Conflict-Free EVC Panel Dispatch
   - Step 5: Time-Travel Fast-Forward (+15 Days)
   - Step 6: Multi-Tier SLA Breach Alert & Escalation Cascade
   - Step 7: Anti-Fraud Document Anomaly Detection
   - Step 8: Cryptographic SHA-256 Audit Chain Verification Proof
3. Full scripted scenario one-click execution end-to-end.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from tests.http_client import AppTestClient
from app.auth import create_access_token

client = AppTestClient()

@pytest.fixture
def super_admin_token():
    return create_access_token({"sub": "usr-member-sec", "role": "SUPER_ADMIN"})

def test_time_travel_status_and_control(super_admin_token):
    """Verify time-travel status endpoint reports virtual date and drift."""
    resp = client.get("/api/v1/demo/time-travel/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "virtual_date" in data
    assert "drift_days" in data

    # Advance clock by 10 days
    adv_resp = client.post("/api/v1/demo/time-travel/advance", json={"days": 10})
    assert adv_resp.status_code == 200
    adv_data = adv_resp.json()
    assert adv_data["status"] == "ADVANCED"
    assert adv_data["days_advanced"] == 10

    # Reset clock (accepts token)
    reset_resp = client.post("/api/v1/demo/time-travel/reset", headers={"Authorization": f"Bearer {super_admin_token}"})
    assert reset_resp.status_code == 200

def test_scripted_scenario_individual_steps():
    """Verify each of the 8 scripted scenario steps can execute individually."""
    # Step 1: APH Upload
    r1 = client.post("/api/v1/demo/scenario/step/1-aph-upload")
    assert r1.status_code == 200
    d1 = r1.json()
    assert d1["step_id"] == 1
    assert d1["step_key"] == "aph_upload"
    assert d1["status"] == "COMPLETED"

    # Step 2: Rules Update
    r2 = client.post("/api/v1/demo/scenario/step/2-rules-update")
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["step_id"] == 2
    assert d2["step_key"] == "rules_update"
    assert "v2026." in d2["details"]["active_ruleset_version"]

    # Step 3: Auto-Route
    r3 = client.post("/api/v1/demo/scenario/step/3-auto-route")
    assert r3.status_code == 200
    d3 = r3.json()
    assert d3["step_id"] == 3
    assert d3["step_key"] == "auto_route"
    assert "APP-DEMO-" in d3["details"]["application_no"]

    # Step 4: EVC Scheduled
    r4 = client.post("/api/v1/demo/scenario/step/4-evc-scheduled")
    assert r4.status_code == 200
    d4 = r4.json()
    assert d4["step_id"] == 4
    assert d4["step_key"] == "evc_scheduled"

    # Step 5: Time Jump
    r5 = client.post("/api/v1/demo/scenario/step/5-time-jump")
    assert r5.status_code == 200
    d5 = r5.json()
    assert d5["step_id"] == 5
    assert d5["step_key"] == "time_jump"
    assert d5["details"]["days_fast_forwarded"] == 15

    # Step 6: Alert Escalates
    r6 = client.post("/api/v1/demo/scenario/step/6-alert-escalates")
    assert r6.status_code == 200
    d6 = r6.json()
    assert d6["step_id"] == 6
    assert d6["step_key"] == "alert_escalates"
    assert len(d6["details"]["escalation_levels_fired"]) >= 3

    # Step 7: Anomaly Flag
    r7 = client.post("/api/v1/demo/scenario/step/7-anomaly-flag")
    assert r7.status_code == 200
    d7 = r7.json()
    assert d7["step_id"] == 7
    assert d7["step_key"] == "anomaly_flag"

    # Step 8: Audit Chain Verifies
    r8 = client.post("/api/v1/demo/scenario/step/8-audit-chain-verifies")
    assert r8.status_code == 200
    d8 = r8.json()
    assert d8["step_id"] == 8
    assert d8["step_key"] == "audit_chain_verifies"
    assert d8["details"]["chain_valid"] is True

def test_full_scripted_scenario_run():
    """Verify that the one-click full scripted scenario completes all 8 steps."""
    resp = client.post("/api/v1/demo/scenario/run")
    assert resp.status_code == 200
    data = resp.json()
    assert data["execution_status"] == "SUCCESS"
    assert data["total_steps"] == 8
    assert data["steps_completed"] == 8
    assert len(data["steps"]) == 8
    for idx, s in enumerate(data["steps"]):
        assert s["step_id"] == idx + 1
        assert s["status"] == "COMPLETED"
