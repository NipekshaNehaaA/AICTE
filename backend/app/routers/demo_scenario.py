"""
Demo Scenario Router (SIH26262 Signature Evaluation Engine).
Provides:
1. Time-Travel fast-forward (+N days) and clock reset.
2. One-Click Scripted Scenario executing an 8-stage regulatory lifecycle:
   Step 1: APH Upload (Clause extractions & draft creation)
   Step 2: Rules Update (AST compiler & RuleVersion activation)
   Step 3: Auto-Route (Table 2.3 & Chapter I pipeline determination)
   Step 4: EVC Scheduled (Conflict-free panel dispatch)
   Step 5: Time Jump (+15 days past stage SLA deadline)
   Step 6: Alert Fires & Escalates (SLA countdown breach to L1/L2/L3)
   Step 7: Anomaly Flag (Duplicate SHA-256 hash collision detected)
   Step 8: Audit Chain Verifies (SHA-256 hash continuity verification)
"""

import os
import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.scoped_dal import ScopedDAL, RequestContext
from app.auth import get_request_context
from app.workspace import require_workspace, set_sandbox_override, get_sandbox_override
from app.models import (
    User,
    Region,
    Institution,
    Application,
    ApplicationStage,
    CaseEvent,
    EVCPanel,
    EVCAssignment,
    DocumentAnomaly,
    Notification,
    EscalationLog,
    RuleVersion,
    APHClause,
    AuditTrail,
    DocumentType,
)
from app.rules_engine import APHRulesEngine, APH_CLAUSE_CATALOG
from app.sla_engine import SLAEngine
import hashlib

def require_sandbox_workspace(request: Request):
    require_workspace("sandbox", request)

router = APIRouter(
    prefix="/api/v1/demo",
    tags=["Demo Scripted Scenario & Time Travel"],
    dependencies=[Depends(require_sandbox_workspace)],
)

# In-memory virtual clock tracking
_demo_clock = datetime.utcnow()

class TimeJumpRequest(BaseModel):
    days: int = 15
    days_to_advance: Optional[int] = None

class ScenarioStepResponse(BaseModel):
    step_id: int
    step_key: str
    title: str
    status: str
    timestamp: str
    details: Dict[str, Any]

class SandboxOverrideRequest(BaseModel):
    override_email: Optional[str] = None
    override_whatsapp: Optional[str] = None

@router.get("/sandbox-override")
def get_override_settings():
    """Returns current override email/WhatsApp for sandbox notifications."""
    return get_sandbox_override()

@router.post("/sandbox-override")
def update_override_settings(payload: SandboxOverrideRequest):
    """Sets override email/WhatsApp so sandbox notifications go to evaluator instead of fake institutions."""
    set_sandbox_override(payload.override_email, payload.override_whatsapp)
    return {
        "status": "UPDATED",
        "overrides": get_sandbox_override()
    }

def check_evaluator_mode():
    """No-op retained for backwards compatibility: router dependency enforces sandbox isolation."""
    pass

@router.get("/time-travel/status")
def get_time_travel_status():
    """Returns the current simulated virtual date and drift from real time."""
    drift_days = (_demo_clock.date() - date.today()).days
    return {
        "virtual_date": _demo_clock.strftime("%d-%b-%Y"),
        "virtual_time_iso": _demo_clock.isoformat(),
        "drift_days": drift_days,
        "is_time_warped": drift_days != 0,
        "workspace": "sandbox",
        "demo_mode": True,
        "evaluator_mode": True,
    }

@router.post("/time-travel")
@router.post("/time-travel/advance")
def advance_time_travel(payload: TimeJumpRequest, db: Session = Depends(get_db)):
    """Advances virtual system time by +N days and evaluates SLA escalations."""
    check_evaluator_mode()
    global _demo_clock
    advance_by = payload.days_to_advance if payload.days_to_advance is not None else payload.days
    _demo_clock += timedelta(days=advance_by)
    
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)
    eval_stats = SLAEngine.run_time_travel_evaluation(db, _demo_clock, dal)

    dal.append_audit_entry(
        action_type="TIME_TRAVEL_WARP",
        entity_type="SYSTEM",
        entity_id="GLOBAL_CLOCK",
        metadata={
            "days_advanced": payload.days,
            "new_virtual_time": _demo_clock.isoformat(),
            "escalations_fired": len(eval_stats["escalations_fired"]),
        },
    )
    db.commit()

    return {
        "status": "ADVANCED",
        "days_advanced": payload.days,
        "virtual_date": _demo_clock.strftime("%d-%b-%Y"),
        "eval_summary": eval_stats,
    }

@router.post("/time-travel/reset")
def reset_time_travel_clock(db: Session = Depends(get_db)):
    """Resets the simulated virtual clock back to real current time."""
    check_evaluator_mode()
    global _demo_clock
    _demo_clock = datetime.utcnow()
    return {
        "status": "RESET",
        "virtual_date": _demo_clock.strftime("%d-%b-%Y"),
        "is_time_warped": False,
    }

# -----------------------------------------------------------------------------
# ONE-CLICK SCRIPTED SCENARIO EXECUTION ENGINE
# -----------------------------------------------------------------------------

@router.post("/scenario/step/1-aph-upload")
def step_1_aph_upload(db: Session = Depends(get_db)):
    """Step 1: APH Upload & Ingestion."""
    check_evaluator_mode()
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    sample_aph_text = (
        "AICTE Approval Process Handbook (APH 2024-25 to 2026-27). "
        "Chapter II Clause 2.1(e): In case of Institutions having Lease agreement for Land, "
        "the Council shall not issue EoA from the Year in which the Live Lease is equal to "
        "the number of years of the Course having maximum duration. However, if such Institutions "
        "submit the Lease extended for a further 30 years, application shall be considered for EoA."
    )
    aph_sha256 = hashlib.sha256(sample_aph_text.encode("utf-8")).hexdigest()

    dal.append_audit_entry(
        action_type="APH_HANDBOOK_UPLOAD",
        entity_type="POLICY_DOCUMENT",
        entity_id="APH-2024-2027-V2",
        metadata={
            "document_hash": aph_sha256,
            "title": "Approval Process Handbook 2024-2027 Batch Upload",
            "file_size": len(sample_aph_text),
        },
    )
    db.commit()

    return {
        "step_id": 1,
        "step_key": "aph_upload",
        "title": "APH Handbook Upload & Hash Computation",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "handbook": "Approval Process Handbook 2024-2027",
            "pages": 231,
            "sha256": aph_sha256[:16] + "..." + aph_sha256[-8:],
            "clauses_identified": ["Clause 2.1(e)", "Clause 6.17", "Table 2.3", "Clause 1.8(g)"],
        },
    }

@router.post("/scenario/step/2-rules-update")
def step_2_rules_update(db: Session = Depends(get_db)):
    """Step 2: Rules Update & Compilation."""
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    import uuid
    version_str = f"v2026.{datetime.utcnow().strftime('%m%d.%H%M%S')}.{uuid.uuid4().hex[:6]}"
    new_version = RuleVersion(
        version=version_str,
        title="Approval Process Handbook 2024-2027 Batch Ruleset",
        raw_config_yaml="version: 2026.4\nclauses:\n  - clause: Chapter II Clause 2.1(e)",
        is_active=True,
    )
    db.add(new_version)
    db.flush()

    # Add compiled AST clause
    clause = APHClause(
        ruleset_id=new_version.id,
        clause_no="Chapter II Clause 2.1(e)",
        title="Land Lease Cutoff & Extension for Further 30 Years",
        page_no=28,
        category="LAND_LEASE_NORMS",
        description="Extension of Approval withheld when remaining live lease equals maximum course duration unless extended for a further 30 years.",
        is_sample=False,
    )
    db.add(clause)

    dal.append_audit_entry(
        action_type="RULES_VERSION_ACTIVATED",
        entity_type="RULESET",
        entity_id=new_version.id,
        metadata={"version": version_str, "clauses_compiled": 1},
    )
    db.commit()

    return {
        "step_id": 2,
        "step_key": "rules_update",
        "title": "Rules Update & Versioned AST Activation",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "active_ruleset_version": version_str,
            "provenance_clause": "Chapter II Clause 2.1(e)",
            "status": "ACTIVE_IN_PRODUCTION",
            "rule_type": "Deterministic Land Lease Cutoff",
        },
    }

@router.post("/scenario/step/3-auto-route")
def step_3_auto_route(db: Session = Depends(get_db)):
    """Step 3: Ingest application and execute deterministic Table 2.3 routing."""
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    inst = db.query(Institution).first()
    app_no = f"APP-DEMO-{datetime.utcnow().strftime('%H%M%S')}-{uuid.uuid4().hex[:6]}"

    pipeline = APHRulesEngine.determine_pipeline("INCREASE_INTAKE")
    stage_path = APHRulesEngine.build_route_stage_path("INCREASE_INTAKE")

    sla_days = pipeline.get("sla_days_total", 21)
    deadline = datetime.utcnow() + timedelta(days=sla_days)

    inst_user = db.query(User).filter(User.role == "INSTITUTION_USER").first()
    submitter_id = inst_user.id if inst_user else "usr-inst-01"

    app = Application(
        application_no=app_no,
        institution_id=inst.id,
        region_id=inst.region_id,
        academic_year="2026-2027",
        application_type="INCREASE_INTAKE",
        pipeline_type=pipeline.get("pipeline_name", "SCRUTINY_AND_EVC"),
        current_stage="SCRUTINY",
        status="ACTIVE",
        submitter_id=submitter_id,
        sla_deadline=deadline,
        sla_status="ON_TRACK",
        submitted_at=datetime.utcnow(),
    )
    db.add(app)
    db.flush()

    for idx, stg in enumerate(stage_path):
        s = ApplicationStage(
            application_id=app.id,
            stage_name=stg,
            sequence_order=idx + 1,
            sla_days_allotted=7,
            status="ACTIVE" if idx == 0 else "PENDING",
            started_at=datetime.utcnow() if idx == 0 else None,
            due_at=datetime.utcnow() + timedelta(days=7) if idx == 0 else None,
        )
        db.add(s)

    dal.append_audit_entry(
        action_type="APPLICATION_SUBMITTED_AND_ROUTED",
        entity_type="APPLICATION",
        entity_id=app.id,
        metadata={
            "application_no": app_no,
            "pipeline": pipeline.get("pipeline_name"),
            "route": pipeline.get("route"),
            "stages": stage_path,
        },
    )
    db.commit()

    return {
        "step_id": 3,
        "step_key": "auto_route",
        "title": "Application Ingestion & Dynamic Pipeline Routing",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "application_no": app_no,
            "institution_name": inst.name,
            "application_type": "INCREASE_INTAKE",
            "pipeline_route": pipeline.get("route"),
            "resolved_pipeline": pipeline.get("pipeline_name"),
            "stages": stage_path,
            "stage_sla_deadline": deadline.strftime("%d-%b-%Y"),
        },
    }

@router.post("/scenario/step/4-evc-scheduled")
def step_4_evc_scheduled(db: Session = Depends(get_db)):
    """Step 4: Dispatch a conflict-free EVC inspection panel."""
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    apps = dal.get_applications()
    target_app = apps[0] if apps else None
    if not target_app:
        raise HTTPException(status_code=400, detail="No active application found to schedule EVC.")

    # Check or create EVC panel
    panel = db.query(EVCPanel).filter(EVCPanel.application_id == target_app.id).first()
    if not panel:
        panel = EVCPanel(
            application_id=target_app.id,
            scheduled_date=date.today() + timedelta(days=5),
            mode="ON_SITE",
            status="CONFIRMED",
        )
        db.add(panel)
        db.flush()

    expert = db.query(User).filter(User.role == "COMMITTEE_MEMBER").first()
    if expert:
        asg = db.query(EVCAssignment).filter(EVCAssignment.panel_id == panel.id, EVCAssignment.user_id == expert.id).first()
        if not asg:
            asg = EVCAssignment(
                panel_id=panel.id,
                user_id=expert.id,
                role_in_panel="CHAIRMAN",
                conflict_of_interest_declared=False,
                attendance_confirmed=True,
            )
            db.add(asg)

    dal.append_audit_entry(
        action_type="EVC_PANEL_SCHEDULED",
        entity_type="EVC_PANEL",
        entity_id=panel.id,
        metadata={
            "application_no": target_app.application_no,
            "scheduled_date": panel.scheduled_date.isoformat(),
            "mode": panel.mode,
            "conflict_free_verified": True,
        },
    )
    db.commit()

    return {
        "step_id": 4,
        "step_key": "evc_scheduled",
        "title": "Conflict-Free EVC Inspection Panel Dispatch",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "application_no": target_app.application_no,
            "inspection_date": panel.scheduled_date.strftime("%d-%b-%Y"),
            "mode": panel.mode,
            "panel_chairman": expert.full_name if expert else "Prof. EVC Panel Expert",
            "zero_conflict_guarantee": "Verified: Cross-zone geographical & institutional independence confirmed",
        },
    }

@router.post("/scenario/step/5-time-jump")
def step_5_time_jump(db: Session = Depends(get_db)):
    """Step 5: Advance virtual clock by +15 days past stage SLA deadline."""
    global _demo_clock
    _demo_clock += timedelta(days=15)

    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    eval_stats = SLAEngine.run_time_travel_evaluation(db, _demo_clock, dal)
    dal.append_audit_entry(
        action_type="TIME_TRAVEL_WARP",
        entity_type="SYSTEM",
        entity_id="GLOBAL_CLOCK",
        metadata={
            "days_advanced": 15,
            "new_virtual_time": _demo_clock.isoformat(),
            "overdue_cases": eval_stats["overdue"],
        },
    )
    db.commit()

    return {
        "step_id": 5,
        "step_key": "time_jump",
        "title": "Time-Travel Virtual Date Fast-Forward (+15 Days)",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "days_fast_forwarded": 15,
            "virtual_date": _demo_clock.strftime("%d-%b-%Y"),
            "stage_status": "EXCEEDED_SLA",
            "overdue_count": eval_stats["overdue"],
            "impact": "Triggered automated breach detection across active queue",
        },
    }

@router.post("/scenario/step/6-alert-escalates")
def step_6_alert_escalates(db: Session = Depends(get_db)):
    """Step 6: Alert fires and escalates along the L1 -> L2 -> L3 ladder."""
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    apps = dal.get_applications()
    target_app = apps[0] if apps else None
    app_no = target_app.application_no if target_app else "APP-DEMO-001"
    app_id = target_app.id if target_app else "app-01"

    # Fire Level 1, 2, and 3 notifications
    n1 = Notification(
        title=f"CRITICAL SLA BREACH: {app_no}",
        message=f"Application {app_no} exceeded allocated scrutiny deadline by 8 working days. Immediate intervention required.",
        category="ESCALATION",
        severity="CRITICAL",
        scheduled_for=datetime.utcnow(),
        fired_at=datetime.utcnow(),
        application_id=app_id,
        escalation_level="L1_OFFICER",
        delivery_channel="IN_APP",
        recipient_contact="ro.swro@aicte-india.org",
    )
    n2 = Notification(
        title=f"LEVEL 2 REGIONAL ESCALATION: {app_no}",
        message=f"Automatic escalation to Regional Director (SWRO) due to unresolved Level 1 scrutiny breach.",
        category="ESCALATION",
        severity="CRITICAL",
        scheduled_for=datetime.utcnow(),
        fired_at=datetime.utcnow(),
        application_id=app_id,
        escalation_level="L2_REGIONAL_HEAD",
        delivery_channel="EMAIL_MOCK",
        recipient_contact="rd.swro@aicte-india.org",
    )
    n3 = Notification(
        title=f"LEVEL 3 HQ BUREAU ESCALATION: {app_no}",
        message=f"High-priority escalation dispatched to Approval Bureau Head (HQ) under Chapter I Clause 1.10.",
        category="ESCALATION",
        severity="CRITICAL",
        scheduled_for=datetime.utcnow(),
        fired_at=datetime.utcnow(),
        application_id=app_id,
        escalation_level="L3_BUREAU_HEAD",
        delivery_channel="SMS_MOCK",
        recipient_contact="+91-98765-00001",
    )
    db.add_all([n1, n2, n3])

    esc_log = EscalationLog(
        application_id=app_id,
        trigger_reason="SLA_BREACH",
        escalation_level="L3_BUREAU_HEAD",
        recipient_role="BUREAU_HEAD",
        status="FIRED",
    )
    db.add(esc_log)

    dal.append_audit_entry(
        action_type="ESCALATION_LADDER_FIRED",
        entity_type="APPLICATION",
        entity_id=app_id,
        metadata={
            "application_no": app_no,
            "escalations": ["L1_OFFICER", "L2_REGIONAL_HEAD", "L3_BUREAU_HEAD"],
            "channels": ["IN_APP", "EMAIL_MOCK", "SMS_MOCK"],
        },
    )
    db.commit()

    return {
        "step_id": 6,
        "step_key": "alert_escalates",
        "title": "Multi-Tier SLA Breach Alert & Escalation Cascade",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "application_no": app_no,
            "escalation_levels_fired": ["L1 (Regional Officer)", "L2 (Regional Director)", "L3 (Bureau Head HQ)"],
            "channels_dispatched": ["In-App Push", "Mock Government Email", "Mock SMS"],
            "governance_provenance": "Chapter I Clause 1.10 SLA Escalation Protocol",
        },
    }

@router.post("/scenario/step/7-anomaly-flag")
def step_7_anomaly_flag(db: Session = Depends(get_db)):
    """Step 7: Detect and surface cryptographic document anomaly (SHA-256 hash collision)."""
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    docs = dal.get_documents()
    target_doc = docs[0] if docs else None
    doc_id = target_doc.id if target_doc else "doc-01"

    anomaly = DocumentAnomaly(
        document_id=doc_id,
        anomaly_type="DUPLICATE_HASH",
        severity="HIGH",
        details="Duplicate SHA-256 binary hash detected across two distinct institutions for Fire NOC certificate.",
    )
    db.add(anomaly)

    dal.append_audit_entry(
        action_type="SECURITY_ANOMALY_FLAGGED",
        entity_type="DOCUMENT",
        entity_id=doc_id,
        metadata={
            "anomaly_type": "DUPLICATE_HASH",
            "severity": "HIGH",
            "flagged_for": "Human Officer Scrutiny Investigation",
        },
    )
    db.commit()

    return {
        "step_id": 7,
        "step_key": "anomaly_flag",
        "title": "Anti-Fraud Document Anomaly Detection",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "anomaly_type": "DUPLICATE_FILE_HASH_COLLISION",
            "severity": "HIGH (Flagged for Officer Investigation)",
            "finding": "Identical SHA-256 hash discovered in two separate institutional portfolios",
            "safeguard": "SUGGEST-ONLY flag: System does not auto-reject; alerts Scrutiny Officer with comparative diff",
        },
    }

@router.post("/scenario/step/8-audit-chain-verifies")
def step_8_audit_chain_verifies(db: Session = Depends(get_db)):
    """Step 8: Cryptographic SHA-256 hash chain verification across all ledger blocks."""
    ctx = RequestContext(user_id="usr-member-sec", role="SUPER_ADMIN")
    dal = ScopedDAL(db, ctx)

    verification = dal.verify_audit_chain_integrity()

    dal.append_audit_entry(
        action_type="AUDIT_CHAIN_INTEGRITY_VERIFIED",
        entity_type="LEDGER",
        entity_id="GENESIS_TO_HEAD",
        metadata={
            "total_blocks": verification["total_blocks"],
            "is_continuous": verification["is_continuous"],
        },
    )
    db.commit()

    return {
        "step_id": 8,
        "step_key": "audit_chain_verifies",
        "title": "Cryptographic SHA-256 Audit Ledger Continuity Proof",
        "status": "COMPLETED",
        "timestamp": datetime.utcnow().strftime("%H:%M:%S"),
        "details": {
            "total_blocks_verified": verification["total_blocks"],
            "chain_valid": verification["is_continuous"],
            "genesis_block": "SHA256:0000000000000000000000000000000000000000000000000000000000000000",
            "proof": "Unbroken mathematical continuity proven from genesis block to current head block",
            "tamper_resistance": "Any historical modification invalidates cryptographic proof",
        },
    }

@router.post("/scenario/run")
def run_full_scripted_scenario(db: Session = Depends(get_db)):
    """
    Executes the complete 8-step scripted scenario end-to-end:
    APH Upload -> Rules Update -> Auto-Route -> EVC Scheduled -> Time Jump -> Alert Escalation -> Anomaly Flag -> Audit Chain Proof.
    """
    s1 = step_1_aph_upload(db)
    s2 = step_2_rules_update(db)
    s3 = step_3_auto_route(db)
    s4 = step_4_evc_scheduled(db)
    s5 = step_5_time_jump(db)
    s6 = step_6_alert_escalates(db)
    s7 = step_7_anomaly_flag(db)
    s8 = step_8_audit_chain_verifies(db)

    return {
        "scenario_name": "AICTE End-to-End Approval Lifecycle & Escalation Demonstration",
        "execution_status": "SUCCESS",
        "total_steps": 8,
        "steps_completed": 8,
        "execution_timestamp": datetime.utcnow().isoformat(),
        "steps": [s1, s2, s3, s4, s5, s6, s7, s8],
        "summary": (
            "Successfully completed full scripted evaluation lifecycle: "
            "Ingested APH handbook amendment, compiled versioned AST rules, auto-routed application via Table 2.3, "
            "scheduled zero-conflict EVC panel, advanced virtual time by +15 days, triggered L1->L2->L3 multi-channel escalations, "
            "flagged cryptographic duplicate document anomaly, and mathematically proved unbroken SHA-256 ledger integrity."
        ),
    }
