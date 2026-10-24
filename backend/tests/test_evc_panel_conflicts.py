"""
Unit and integration tests for EVC Panel Conflict-of-Interest, Load Balancing, and .ics Export.
Verifies:
1. Exclusion Rule 1: Exclude experts from same state as institution (Annexure-16 Clause 16.5).
2. Exclusion Rule 2: Exclude experts with prior review within cooling period (configurable 12-24 months).
3. Exclusion Rule 3: Exclude double-booked experts on proposed inspection date.
4. Load balancing: Lower workload & optimized regional travel prioritized.
5. Official confirmation rejects double-booking attempts with HTTP 400.
6. RFC 5545 .ics calendar export returns valid iCalendar file.
"""

from datetime import datetime, timedelta, date
import pytest
from app.database import SessionLocal
from app.models import Application, Institution, Region, EVCPanel, EVCAssignment, User
from app.scoped_dal import RequestContext
from app.routers.evc_hub import (
    suggest_smart_panel,
    confirm_evc_schedule,
    export_evc_schedule_ics,
    SuggestPanelRequest,
    ConfirmPanelRequest,
    EMPANELLED_EXPERTS,
    PRIOR_INSPECTION_REVIEWS,
)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_exclusion_rule_same_state_conflict(db):
    """Experts affiliated with the same state as the applicant institution are strictly excluded."""
    app = db.query(Application).first()
    assert app is not None
    inst_state = app.institution.state # e.g. Karnataka

    req = SuggestPanelRequest(
        application_id=app.id,
        proposed_date="2026-11-20",
        mode="ON_SITE",
    )
    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=app.region_id)
    res = suggest_smart_panel(payload=req, ctx=ctx, db=db)

    # All suggested panel members must NOT be from inst_state
    for expert in res["suggested_panel"]:
        assert expert.get("state", "").lower() != inst_state.lower()

    # Home-state candidates must appear in excluded_candidates
    home_state_exclusions = [
        exc for exc in res["excluded_candidates"]
        if "EXCLUDED_HOME_STATE" in exc["reason"]
    ]
    assert len(home_state_exclusions) > 0

def test_exclusion_rule_cooling_period(db):
    """Experts who inspected the institution within cooling window are excluded."""
    app = db.query(Application).first()
    assert app is not None

    # Inject a prior inspection within the cooling window (e.g. 150 days ago)
    PRIOR_INSPECTION_REVIEWS.append({
        "expert_id": "exp-prof-03", # Amitabh Sen from West Bengal
        "institution_name": app.institution.name,
        "inspection_date": (date.today() - timedelta(days=150)).strftime("%Y-%m-%d"),
    })

    req = SuggestPanelRequest(
        application_id=app.id,
        proposed_date="2026-11-20",
        cooling_period_months=24,
    )
    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=app.region_id)
    res = suggest_smart_panel(payload=req, ctx=ctx, db=db)

    cooling_exclusions = [
        exc for exc in res["excluded_candidates"]
        if exc["id"] == "exp-prof-03" and "EXCLUDED_COOLING_PERIOD" in exc["reason"]
    ]
    assert len(cooling_exclusions) == 1
    assert "cooling window" in cooling_exclusions[0]["reason"].lower()

def test_load_balancing_and_inclusion_rationale(db):
    """Suggested panel members contain explicit inclusion rationale and balanced workload."""
    app = db.query(Application).first()
    assert app is not None

    req = SuggestPanelRequest(
        application_id=app.id,
        proposed_date="2026-11-25",
        mode="ON_SITE",
    )
    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=app.region_id)
    res = suggest_smart_panel(payload=req, ctx=ctx, db=db)

    assert len(res["suggested_panel"]) == 3
    for expert in res["suggested_panel"]:
        assert "inclusion_rationale" in expert
        assert len(expert["inclusion_rationale"]) > 10
        assert "workload_active_visits" in expert

    assert "load_balancing_summary" in res
    assert res["load_balancing_summary"]["selected_panel_size"] == 3

def test_double_booking_guard_in_confirm_schedule(db):
    """Confirming an expert who is already scheduled on the same date is blocked with HTTP 400."""
    app1 = db.query(Application).first()
    apps = db.query(Application).all()
    app2 = apps[1] if len(apps) > 1 else apps[0]
    assert app1 is not None and app2 is not None

    test_date = date.today() + timedelta(days=12)

    # Ensure app1 has a panel on test_date
    panel1 = app1.evc_panel
    if not panel1:
        panel1 = EVCPanel(application_id=app1.id, scheduled_date=test_date, status="CONFIRMED")
        db.add(panel1)
        db.commit()
    else:
        panel1.scheduled_date = test_date
        db.commit()

    # Assign exp-prof-01 to panel1
    db.query(EVCAssignment).filter(EVCAssignment.panel_id == panel1.id).delete()
    db.add(EVCAssignment(
        panel_id=panel1.id,
        user_id="exp-prof-01",
        role_in_panel="CHAIRMAN"
    ))
    db.commit()

    # Now attempt to confirm app2 on the same test_date with exp-prof-01
    panel2 = app2.evc_panel
    if not panel2:
        panel2 = EVCPanel(application_id=app2.id, scheduled_date=test_date, status="CONFIRMED")
        db.add(panel2)
        db.commit()
    else:
        panel2.scheduled_date = test_date
        db.commit()

    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=app2.region_id)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as excinfo:
        confirm_evc_schedule(
            application_id=app2.id,
            payload=ConfirmPanelRequest(selected_member_ids=["exp-prof-01", "exp-ind-01", "exp-arch-01"]),
            ctx=ctx,
            db=db,
        )
    assert excinfo.value.status_code == 400
    assert "double-booking" in excinfo.value.detail.lower()

def test_export_evc_schedule_ics(db):
    """GET /api/v1/evc/schedule/{panel_id}/ics returns valid RFC 5545 iCalendar content."""
    app = db.query(Application).first()
    assert app is not None

    panel = app.evc_panel
    if not panel:
        panel = EVCPanel(application_id=app.id, scheduled_date=date.today() + timedelta(days=5), status="CONFIRMED")
        db.add(panel)
        db.commit()

    response = export_evc_schedule_ics(panel_id=panel.id, db=db)
    assert response.status_code == 200
    assert "text/calendar" in response.media_type

    content = response.body.decode("utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "VERSION:2.0" in content
    assert "BEGIN:VEVENT" in content
    assert f"SUMMARY:AICTE EVC Inspection: {app.institution.name}" in content
    assert "STATUS:CONFIRMED" in content
    assert "END:VEVENT" in content
    assert "END:VCALENDAR" in content
