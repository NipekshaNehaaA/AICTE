"""
Test Suite: SLA Calculator, Holiday Calendar, Multi-Tier Escalation Ladder, and Alert Timeliness
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime, timedelta, date
from app.database import SessionLocal
from app.models import Application, EscalationLog, Notification, AuditTrail
from app.sla_engine import SLAEngine
from app.scoped_dal import ScopedDAL, RequestContext

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_working_days_calculation():
    """Validates that Saturdays, Sundays, and statutory holidays are omitted from SLA clock."""
    # Monday 2026-10-19 to Friday 2026-10-23
    start = datetime(2026, 10, 19, 9, 0)
    # Add a holiday on Wednesday 2026-10-21
    holidays = [date(2026, 10, 21)]

    # Adding 3 working days from Monday:
    # Day 1: Tuesday Oct 20
    # Wednesday Oct 21 is holiday (skipped)
    # Day 2: Thursday Oct 22
    # Day 3: Friday Oct 23
    target = SLAEngine.add_working_days(start, 3, holidays)
    assert target.date() == date(2026, 10, 23)

    # Adding 5 working days crosses the weekend (Sat Oct 24, Sun Oct 25 skipped):
    # Day 4: Monday Oct 26
    # Day 5: Tuesday Oct 27
    target_weekend = SLAEngine.add_working_days(start, 5, holidays)
    assert target_weekend.date() == date(2026, 10, 27)

def test_sla_rag_classification():
    """Validates RAG status: ON_TRACK, AT_RISK (<= 2 days), OVERDUE."""
    app = Application()
    now = datetime(2026, 10, 22, 12, 0)
    holidays = []

    # 1. Due in 5 days -> ON_TRACK
    app.sla_deadline = now + timedelta(days=5)
    app.status = "IN_PROGRESS"
    status, days = SLAEngine.evaluate_case_sla(app, now, holidays)
    assert status == "ON_TRACK"
    assert days == 5.0

    # 2. Due in 1.5 days -> AT_RISK
    app.sla_deadline = now + timedelta(days=1.5)
    status, days = SLAEngine.evaluate_case_sla(app, now, holidays)
    assert status == "AT_RISK"

    # 3. Overdue by 2 days -> OVERDUE
    app.sla_deadline = now - timedelta(days=2.0)
    status, days = SLAEngine.evaluate_case_sla(app, now, holidays)
    assert status == "OVERDUE"
    assert days == -2.0

    # 4. Status == DEFICIENT -> PAUSED
    app.status = "DEFICIENT"
    status, days = SLAEngine.evaluate_case_sla(app, now, holidays)
    assert status == "PAUSED"

def test_hierarchical_escalation_ladder(db):
    """
    Validates hierarchical escalation:
    - Overdue by 4 days triggers Level 2 (Regional Head)
    - Overdue by 8 days triggers Level 3 (Bureau Head HQ)
    """
    # Create an isolated test application
    now = datetime.utcnow()
    app = Application(
        application_no=f"AICTE/TEST/{datetime.utcnow().timestamp()}",
        institution_id=db.query(Application).first().institution_id,
        region_id=db.query(Application).first().region_id,
        application_type="NEW_INSTITUTION",
        academic_year="2026-2027",
        pipeline_type="SCRUTINY_EVC",
        current_stage="SCRUTINY",
        status="IN_PROGRESS",
        submitter_id="usr-sub-test",
        sla_deadline=now,
        sla_status="ON_TRACK",
    )
    db.add(app)
    db.commit()

    dal = ScopedDAL(db, RequestContext(user_id="test-system", role="SUPER_ADMIN"))
    
    # Simulate overdue by 4 days (Level 2 threshold)
    virtual_now_l2 = app.sla_deadline + timedelta(days=4)
    esc_l2 = SLAEngine.process_escalations_for_application(db, app, virtual_now_l2, dal)
    assert len(esc_l2) > 0
    assert esc_l2[0]["tier"] == "L2_REGIONAL_HEAD"

    # Verify escalation log record
    log_l2 = db.query(EscalationLog).filter(
        EscalationLog.application_id == app.id,
        EscalationLog.escalation_level == "L2_REGIONAL_HEAD"
    ).first()
    assert log_l2 is not None
    assert log_l2.recipient_role == "REGIONAL_OFFICER"

    # Simulate overdue by 8 days (Level 3 threshold)
    virtual_now_l3 = app.sla_deadline + timedelta(days=8)
    esc_l3 = SLAEngine.process_escalations_for_application(db, app, virtual_now_l3, dal)
    assert len(esc_l3) > 0
    assert esc_l3[0]["tier"] == "L3_BUREAU_HEAD"

def test_time_travel_evaluation(db):
    """Validates that fast-forwarding virtual clock re-evaluates all applications live."""
    # Create an isolated test application due today
    now = datetime.utcnow()
    app = Application(
        application_no=f"AICTE/WARP/{datetime.utcnow().timestamp()}",
        institution_id=db.query(Application).first().institution_id,
        region_id=db.query(Application).first().region_id,
        application_type="EXTENSION_OF_APPROVAL",
        academic_year="2026-2027",
        pipeline_type="ONLY_SELF_DISCLOSURE",
        current_stage="SELF_DISCLOSURE",
        status="IN_PROGRESS",
        submitter_id="usr-sub-warp",
        sla_deadline=now,
        sla_status="ON_TRACK",
    )
    db.add(app)
    db.commit()

    dal = ScopedDAL(db, RequestContext(user_id="test-time-travel", role="SUPER_ADMIN"))
    # Advance time by 30 days
    warp_time = now + timedelta(days=30)
    stats = SLAEngine.run_time_travel_evaluation(db, warp_time, dal)
    
    assert stats["overdue"] > 0
    assert len(stats["escalations_fired"]) > 0
