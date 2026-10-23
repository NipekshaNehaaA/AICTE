"""
Test Suite: Intake, Table 2.3 Routing, Revert Loop, Paused SLA Clock, and AI Draft Approval
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from datetime import datetime, timedelta
from app.database import SessionLocal
from app.models import Institution, Application, StageRevert, LLMDraft, AuditTrail
from app.rules_engine import APHRulesEngine

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_aph_table_2_3_pipeline_determination():
    """Validates deterministic pipeline selection based on APH Table 2.3."""
    # 1. Extension of Approval on Self-Disclosure -> ONLY_SELF_DISCLOSURE
    eoa_pipe = APHRulesEngine.determine_pipeline("EXTENSION_OF_APPROVAL")
    assert eoa_pipe["pipeline_name"] == "ONLY_SELF_DISCLOSURE"
    assert eoa_pipe["requires_scrutiny"] is False
    assert eoa_pipe["requires_evc"] is False

    # 2. New Institution -> SCRUTINY_EVC
    new_inst_pipe = APHRulesEngine.determine_pipeline("NEW_INSTITUTION")
    assert new_inst_pipe["pipeline_name"] == "SCRUTINY_EVC"
    assert new_inst_pipe["requires_scrutiny"] is True
    assert new_inst_pipe["requires_evc"] is True

    # 3. Increase in Intake -> SCRUTINY_EVC_SAC
    intake_pipe = APHRulesEngine.determine_pipeline("INCREASE_INTAKE")
    assert intake_pipe["pipeline_name"] == "SCRUTINY_EVC_SAC"
    assert intake_pipe["requires_sac"] is True

    # 4. Closure of Institution -> ONLY_SCRUTINY
    closure_pipe = APHRulesEngine.determine_pipeline("CLOSURE")
    assert closure_pipe["pipeline_name"] == "ONLY_SCRUTINY"
    assert closure_pipe["requires_evc"] is False

def test_workflow_revert_and_paused_sla_clock(db):
    """
    Validates that returning an application for deficiency pauses the SLA clock
    and resubmission resumes it.
    """
    from app.routers.intake_workflow import revert_for_deficiency, submit_deficiency_cure, StageRevertRequest, CureSubmitRequest
    from app.scoped_dal import RequestContext

    inst = db.query(Institution).first()
    now = datetime.utcnow()
    app = Application(
        application_no=f"AICTE/REV-TEST/{now.timestamp()}",
        institution_id=inst.id,
        region_id=inst.region_id,
        application_type="NEW_INSTITUTION",
        academic_year="2026-2027",
        pipeline_type="SCRUTINY_EVC",
        current_stage="SCRUTINY",
        status="IN_PROGRESS",
        submitter_id="usr-sub-rev",
        sla_deadline=now + timedelta(days=7),
        sla_status="ON_TRACK",
    )
    db.add(app)
    db.commit()

    ro_ctx = RequestContext(user_id="officer-swro-01", role="REGIONAL_OFFICER", region_id=app.region_id)
    initial_deadline = app.sla_deadline

    # 1. Official reverts application for deficiency
    revert_req = StageRevertRequest(
        reason_category="Land Lease Near Expiration",
        deficiency_remarks="Live lease period is less than course duration as per Clause 2.1(e). Submit 30-year extension.",
        aph_clause_ref="Chapter II, Clause 2.1(e) (Page 12)",
        cure_days=15,
    )
    res = revert_for_deficiency(app.id, revert_req, ro_ctx, db)
    assert res["status"] == "REVERTED_FOR_DEFICIENCY"
    assert res["sla_clock_paused"] is True

    db.refresh(app)
    assert app.status == "DEFICIENT"
    assert app.current_stage == "DEFICIENCY_REVERTED"
    assert app.last_paused_at is not None

    # Simulate 2 days passing while paused
    app.last_paused_at = datetime.utcnow() - timedelta(days=2)
    db.commit()

    # 2. Institution submits cure response
    inst_ctx = RequestContext(user_id=app.submitter_id, role="INSTITUTION_USER", institution_id=app.institution_id)
    cure_req = CureSubmitRequest(
        institution_response="Uploaded registered 30-year land lease extension deed with Sub-Registrar seal.",
    )
    res_cure = submit_deficiency_cure(app.id, cure_req, inst_ctx, db)
    assert res_cure["status"] == "RESUBMITTED"
    assert res_cure["sla_clock_resumed"] is True

    db.refresh(app)
    assert app.status == "IN_PROGRESS"
    assert app.current_stage == "RE_SCRUTINY"
    assert app.last_paused_at is None
    assert app.paused_accumulated_hours >= 47.0 # ~48 hours
    assert app.sla_deadline > initial_deadline # Deadline was pushed forward by paused duration!

def test_isolated_ai_draft_and_human_approval_gate(db):
    """
    Validates that:
    1. AI generates draft into `llm_drafts` table without modifying case state (SUGGEST-ONLY).
    2. Approver must differ from requester (Pairwise SoD).
    3. Named human officer approves draft to promote to official record.
    """
    from app.routers.intake_workflow import generate_draft_case_summary, approve_ai_draft_docket
    from app.scoped_dal import RequestContext

    app = db.query(Application).first()
    assert app

    # Step 1: Officer A requests AI case summary
    officer_a_ctx = RequestContext(user_id="officer-requester-a", role="REGIONAL_OFFICER", region_id=app.region_id)
    draft_res = generate_draft_case_summary(app.id, officer_a_ctx, db)
    assert draft_res["classification"] == "SUGGEST_ONLY"
    assert "Decision reserved for the competent authority" in draft_res["notice"]
    draft_id = draft_res["draft_id"]

    draft_record = db.query(LLMDraft).filter(LLMDraft.id == draft_id).first()
    assert draft_record.status == "PENDING_HUMAN_REVIEW"
    assert draft_record.confidence_score >= 0.90

    # Step 2: Officer A attempts to approve own requested draft -> BLOCKED by SoD
    with pytest.raises(Exception):
        approve_ai_draft_docket(draft_id, None, officer_a_ctx, db)

    # Step 3: Officer B (Approving Official) approves the draft -> SUCCESS
    officer_b_ctx = RequestContext(user_id="director-approver-b", role="SUPER_ADMIN")
    appr_res = approve_ai_draft_docket(draft_id, "Approved with minor note on laboratory space.", officer_b_ctx, db)
    assert appr_res["status"] == "OFFICIALLY_APPROVED"
    assert appr_res["approved_by"] == "director-approver-b"

    db.refresh(draft_record)
    assert draft_record.status == "ACCEPTED_OFFICIAL"
    assert draft_record.approver_id == "director-approver-b"
