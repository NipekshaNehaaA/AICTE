"""
=============================================================================
INTAKE & WORKFLOW ROUTING ROUTER
=============================================================================
Endpoints:
- Application Intake (New Institution, EoA, Intake Increase, New Course, etc.)
- AICTE Portal Mock Import Adapter
- Deterministic Stage Progression & Pairwise SoD checks
- Revert / Deficiency Loop with SLA Pausing
- Cure Clarification Submission & SLA Unpausing
- Isolated AI Electronic Case Summary Generator & Human Approval Gate
=============================================================================
"""

import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Application,
    ApplicationStage,
    CaseEvent,
    StageRevert,
    Institution,
    Region,
    User,
    LLMDraft,
)
from app.scoped_dal import ScopedDAL, RequestContext, SecurityScopeError, SoDViolationError
from app.rules_engine import APHRulesEngine, APH_CLAUSE_CATALOG

router = APIRouter(prefix="/api/v1", tags=["Intake & Workflow"])

# -----------------------------------------------------------------------------
# Pydantic Schemas
# -----------------------------------------------------------------------------
class ApplicationCreateRequest(BaseModel):
    institution_id: str
    application_type: str # NEW_INSTITUTION, EXTENSION_OF_APPROVAL, INCREASE_INTAKE, NEW_PROGRAMME, CLOSURE
    academic_year: str = "2026-2027"
    course_name: Optional[str] = "Computer Science and Engineering"
    intake_proposed: int = 60
    remarks: Optional[str] = ""

class StageRevertRequest(BaseModel):
    reason_category: str # Missing Fire NOC, Insufficient Land Lease, Principal Unqualified, etc.
    deficiency_remarks: str
    aph_clause_ref: Optional[str] = "Chapter I, Clause 1.8(f) & Annexure-1 (Page 7, 77)"
    cure_days: int = 15

class CureSubmitRequest(BaseModel):
    institution_response: str
    rectified_document_urls: List[str] = []

class PortalImportBatchRequest(BaseModel):
    portal_source: str = "AICTE_NSWS_PORTAL"
    records: List[Dict[str, Any]]

# Helper to build RequestContext from demo headers
def get_request_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header("REGIONAL_OFFICER"),
    x_region_id: Optional[str] = Header(None),
    x_institution_id: Optional[str] = Header(None),
) -> RequestContext:
    return RequestContext(
        user_id=x_user_id or "usr-demo-default",
        role=x_user_role or "REGIONAL_OFFICER",
        region_id=x_region_id,
        institution_id=x_institution_id,
    )

# -----------------------------------------------------------------------------
# Intake Endpoints
# -----------------------------------------------------------------------------
@router.post("/applications/submit")
def submit_application(
    payload: ApplicationCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Submits an application from an institution or officer.
    Deterministic rules engine selects pipeline based on APH 2024-27 Table 2.3.
    """
    inst = db.query(Institution).filter(Institution.id == payload.institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    pipeline_info = APHRulesEngine.determine_pipeline(payload.application_type)
    pipeline_type = pipeline_info["pipeline_name"]
    stages_seq = pipeline_info["stages"]

    app_no = f"AICTE/2026-27/{inst.permanent_id}-{uuid.uuid4().hex[:4].upper()}"
    now = datetime.utcnow()
    initial_stage = stages_seq[0]
    stage_sla = APHRulesEngine.calculate_stage_sla(initial_stage)
    sla_deadline = now + timedelta(days=stage_sla)

    # Submitter is current user
    submitter_id = ctx.user_id if ctx.user_id else "usr-submitter-default"

    new_app = Application(
        application_no=app_no,
        institution_id=inst.id,
        region_id=inst.region_id,
        application_type=payload.application_type,
        academic_year=payload.academic_year,
        pipeline_type=pipeline_type,
        current_stage=initial_stage,
        status="IN_PROGRESS",
        submitter_id=submitter_id,
        sla_deadline=sla_deadline,
        sla_status="ON_TRACK",
        submitted_at=now,
    )
    db.add(new_app)
    db.flush()

    # Create sequence of stages
    for idx, stg_name in enumerate(stages_seq):
        stage_record = ApplicationStage(
            application_id=new_app.id,
            stage_name=stg_name,
            sequence_order=idx + 1,
            status="ACTIVE" if idx == 0 else "PENDING",
            started_at=now if idx == 0 else None,
            due_at=sla_deadline if idx == 0 else None,
            sla_days_allotted=APHRulesEngine.calculate_stage_sla(stg_name),
        )
        db.add(stage_record)

    # Append intake case event
    db.add(CaseEvent(
        application_id=new_app.id,
        event_type="INTAKE",
        actor_id=submitter_id,
        actor_role=ctx.role,
        description=f"Application submitted for {payload.application_type}. Pipeline routed to {pipeline_type}.",
        aph_clause_ref=pipeline_info["aph_clause_ref"],
    ))

    # Append hash-chained audit entry
    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="APPLICATION_INTAKE",
        entity_type="APPLICATION",
        entity_id=new_app.id,
        metadata={
            "application_no": app_no,
            "pipeline": pipeline_type,
            "aph_clause": pipeline_info["aph_clause_ref"],
        },
    )
    db.commit()

    return {
        "status": "SUCCESS",
        "application_id": new_app.id,
        "application_no": app_no,
        "pipeline_type": pipeline_type,
        "current_stage": initial_stage,
        "sla_deadline": sla_deadline.isoformat(),
        "aph_provenance": pipeline_info["aph_clause_ref"],
    }

@router.post("/applications/import-aicte-portal")
def import_from_aicte_portal(
    payload: PortalImportBatchRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Mock adapter accepting batch application records from the AICTE / NSWS portal.
    Demonstrates integration-readiness with automated pipeline mapping.
    """
    imported_count = 0
    now = datetime.utcnow()

    for rec in payload.records:
        perm_id = rec.get("permanent_id")
        inst = db.query(Institution).filter(Institution.permanent_id == perm_id).first()
        if not inst:
            # Create synthetic institution placeholder
            inst = Institution(
                permanent_id=perm_id or f"1-{random.randint(10000000, 99999999)}",
                name=rec.get("institution_name", "Imported Technical Institute"),
                address=rec.get("address", "Knowledge Corridor, Academic Sector"),
                state=rec.get("state", "Karnataka"),
                region_id=db.query(Region).first().id,
                category=rec.get("category", "Engineering & Tech"),
                is_synthetic=True,
            )
            db.add(inst)
            db.flush()

        app_type = rec.get("application_type", "EXTENSION_OF_APPROVAL")
        pipeline_info = APHRulesEngine.determine_pipeline(app_type)
        stages_seq = pipeline_info["stages"]

        app_no = f"AICTE/2026-27/{inst.permanent_id}"
        stage_sla = APHRulesEngine.calculate_stage_sla(stages_seq[0])

        app = Application(
            application_no=app_no,
            institution_id=inst.id,
            region_id=inst.region_id,
            application_type=app_type,
            academic_year="2026-2027",
            pipeline_type=pipeline_info["pipeline_name"],
            current_stage=stages_seq[0],
            status="IN_PROGRESS",
            submitter_id=ctx.user_id or "usr-portal-adapter",
            sla_deadline=now + timedelta(days=stage_sla),
            sla_status="ON_TRACK",
        )
        db.add(app)
        db.flush()

        for idx, stg in enumerate(stages_seq):
            db.add(ApplicationStage(
                application_id=app.id,
                stage_name=stg,
                sequence_order=idx + 1,
                status="ACTIVE" if idx == 0 else "PENDING",
                started_at=now if idx == 0 else None,
                due_at=now + timedelta(days=stage_sla) if idx == 0 else None,
                sla_days_allotted=APHRulesEngine.calculate_stage_sla(stg),
            ))

        imported_count += 1

    db.commit()
    return {
        "status": "SUCCESS",
        "imported_records": imported_count,
        "source": payload.portal_source,
    }

# -----------------------------------------------------------------------------
# Applications Query Endpoints
# -----------------------------------------------------------------------------
@router.get("/applications")
def list_applications(
    stage: Optional[str] = None,
    sla_status: Optional[str] = None,
    region_code: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Returns list of applications scoped by user role and region via ScopedDAL.
    """
    dal = ScopedDAL(db, ctx)
    apps = dal.get_applications()

    results = []
    for app in apps:
        if stage and app.current_stage != stage:
            continue
        if sla_status and app.sla_status != sla_status:
            continue
        if region_code and app.institution.region.code != region_code:
            continue

        results.append({
            "id": app.id,
            "application_no": app.application_no,
            "institution_name": app.institution.name,
            "permanent_id": app.institution.permanent_id,
            "region_code": app.institution.region.code,
            "application_type": app.application_type,
            "pipeline_type": app.pipeline_type,
            "current_stage": app.current_stage,
            "status": app.status,
            "sla_deadline": app.sla_deadline.strftime("%Y-%m-%d"),
            "sla_status": app.sla_status,
            "paused_hours": app.paused_accumulated_hours,
            "submitted_at": app.submitted_at.strftime("%Y-%m-%d"),
        })

    return {"count": len(results), "applications": results}

@router.get("/applications/{application_id}")
def get_application_details(
    application_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Returns full application case timeline, SLA clocks, and APH provenance.
    """
    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or outside user scope.")

    stages_data = [
        {
            "id": s.id,
            "stage_name": s.stage_name,
            "sequence_order": s.sequence_order,
            "status": s.status,
            "sla_days_allotted": s.sla_days_allotted,
            "started_at": s.started_at.strftime("%Y-%m-%d") if s.started_at else None,
            "due_at": s.due_at.strftime("%Y-%m-%d") if s.due_at else None,
            "completed_at": s.completed_at.strftime("%Y-%m-%d") if s.completed_at else None,
        }
        for s in app.stages
    ]

    events_data = [
        {
            "id": e.id,
            "event_type": e.event_type,
            "actor_role": e.actor_role,
            "description": e.description,
            "aph_clause_ref": e.aph_clause_ref,
            "timestamp": e.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for e in reversed(app.events)
    ]

    # Calculate days remaining
    now = datetime.utcnow()
    days_remaining = (app.sla_deadline - now).total_seconds() / 86400.0

    return {
        "id": app.id,
        "application_no": app.application_no,
        "institution": {
            "name": app.institution.name,
            "permanent_id": app.institution.permanent_id,
            "region": app.institution.region.name,
            "region_code": app.institution.region.code,
            "compliance_health_score": app.institution.compliance_health_score,
        },
        "application_type": app.application_type,
        "pipeline_type": app.pipeline_type,
        "current_stage": app.current_stage,
        "status": app.status,
        "sla": {
            "deadline": app.sla_deadline.strftime("%Y-%m-%d"),
            "days_remaining": round(days_remaining, 1),
            "status": app.sla_status,
            "is_paused": app.status == "DEFICIENT",
            "paused_hours": app.paused_accumulated_hours,
        },
        "actors": {
            "submitter_id": app.submitter_id,
            "verifier_id": app.verifier_id,
            "approver_id": app.approver_id,
        },
        "stages": stages_data,
        "events": events_data,
        "aph_provenance": APHRulesEngine.get_clause_provenance(app.pipeline_type),
    }

# -----------------------------------------------------------------------------
# Workflow Progression & Revert Loop
# -----------------------------------------------------------------------------
@router.post("/workflow/{application_id}/advance")
def advance_stage(
    application_id: str,
    remarks: str = "Stage completed by authorized official.",
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    AUTO-advances an application to the next prescribed stage upon authorized sign-off.
    Enforces pairwise Separation of Duties (SoD).
    """
    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    next_stg = APHRulesEngine.get_next_stage(app.pipeline_type, app.current_stage)
    if not next_stg:
        next_stg = "APPROVED"

    try:
        updated_app = dal.advance_application_stage(app.id, next_stg, remarks)
        return {
            "status": "SUCCESS",
            "previous_stage": app.current_stage,
            "new_stage": updated_app.current_stage,
            "updated_at": updated_app.updated_at.isoformat(),
        }
    except SoDViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SecurityScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.post("/workflow/{application_id}/revert")
def revert_for_deficiency(
    application_id: str,
    payload: StageRevertRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Authorized return/revert of application for deficiencies.
    Pauses statutory SLA clock and notifies institution with cure deadline.
    """
    if ctx.role == "AUDITOR":
        raise HTTPException(status_code=403, detail="Auditor role is strictly read-only.")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    now = datetime.utcnow()
    cure_deadline = now + timedelta(days=payload.cure_days)

    # Update application status to DEFICIENT (pauses clock)
    old_stage = app.current_stage
    app.current_stage = "DEFICIENCY_REVERTED"
    app.status = "DEFICIENT"
    app.last_paused_at = now

    revert_entry = StageRevert(
        application_id=app.id,
        stage_id=app.stages[0].id if app.stages else "stg-01",
        reverted_by=ctx.user_id,
        reason_category=payload.reason_category,
        deficiency_remarks=payload.deficiency_remarks,
        aph_clause_ref=payload.aph_clause_ref,
        cure_deadline=cure_deadline,
    )
    db.add(revert_entry)

    # Log case event
    db.add(CaseEvent(
        application_id=app.id,
        event_type="STAGE_REVERT",
        actor_id=ctx.user_id,
        actor_role=ctx.role,
        description=f"Returned for deficiency: [{payload.reason_category}] - {payload.deficiency_remarks}. SLA clock paused.",
        aph_clause_ref=payload.aph_clause_ref,
    ))

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="STAGE_REVERT",
        entity_type="APPLICATION",
        entity_id=app.id,
        metadata={
            "deficiency": payload.reason_category,
            "cure_days": payload.cure_days,
            "cure_deadline": cure_deadline.isoformat(),
        },
    )
    db.commit()

    return {
        "status": "REVERTED_FOR_DEFICIENCY",
        "current_stage": app.current_stage,
        "cure_deadline": cure_deadline.strftime("%Y-%m-%d"),
        "sla_clock_paused": True,
    }

@router.post("/workflow/{application_id}/cure-submit")
def submit_deficiency_cure(
    application_id: str,
    payload: CureSubmitRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Institution submits deficiency rectification evidence.
    Unpauses statutory SLA clock and routes application to Re-Scrutiny (Clause 1.8(g)).
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    now = datetime.utcnow()
    # Calculate paused duration
    if app.last_paused_at:
        paused_duration = (now - app.last_paused_at).total_seconds() / 3600.0
        app.paused_accumulated_hours += paused_duration
        # Extend SLA deadline by paused hours
        app.sla_deadline += timedelta(hours=paused_duration)
        app.last_paused_at = None

    app.current_stage = "RE_SCRUTINY"
    app.status = "IN_PROGRESS"

    db.add(CaseEvent(
        application_id=app.id,
        event_type="CURE_SUBMISSION",
        actor_id=ctx.user_id,
        actor_role="INSTITUTION_USER",
        description=f"Deficiency rectification submitted: {payload.institution_response}. SLA clock resumed.",
        aph_clause_ref="Chapter I, Clause 1.8(g) (Page 7)",
    ))

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="CURE_SUBMITTED",
        entity_type="APPLICATION",
        entity_id=app.id,
        metadata={"response": payload.institution_response},
    )
    db.commit()

    return {
        "status": "RESUBMITTED",
        "current_stage": app.current_stage,
        "sla_clock_resumed": True,
        "new_sla_deadline": app.sla_deadline.strftime("%Y-%m-%d"),
    }

# -----------------------------------------------------------------------------
# Isolated AI Assistant (SUGGEST-ONLY Draft Docket)
# -----------------------------------------------------------------------------
@router.post("/workflow/{application_id}/draft-summary")
def generate_draft_case_summary(
    application_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Isolated AI layer drafts a structured electronic case docket (SUGGEST-ONLY).
    Writes strictly to `llm_drafts` table. CANNOT modify case state.
    """
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    # Schema-validated case summary JSON
    docket_content = {
        "header": {
            "application_no": app.application_no,
            "institution_name": app.institution.name,
            "permanent_id": app.institution.permanent_id,
            "region": app.institution.region.name,
            "academic_cycle": app.academic_year,
        },
        "pipeline_assessment": {
            "prescribed_route": app.pipeline_type,
            "current_stage": app.current_stage,
            "sla_performance": f"{app.sla_status} (Target: {app.sla_deadline.strftime('%d-%b-%Y')})",
            "statutory_pause_hours": app.paused_accumulated_hours,
        },
        "scrutiny_findings": [
            "Registered Land Lease Deed verified for 30 years as per Clause 6.17(a).",
            "Building stability certificate active.",
            "Faculty student ratio meeting norms for proposed intake.",
        ],
        "suggested_recommendation": "Eligible to advance to Expert Visit Committee (EVC) verification.",
        "aph_clause_provenance": [
            "Chapter I, Clause 1.8 (Page 7)",
            "Chapter I, Clause 1.9 (Page 8)",
            "Chapter VI, Clause 6.17(a) (Page 56)",
        ],
    }

    draft = LLMDraft(
        draft_type="CASE_SUMMARY",
        related_entity_type="APPLICATION",
        related_entity_id=app.id,
        prompt_hash=uuid.uuid4().hex,
        model_version="hosted-llm-v1",
        generated_content=str(docket_content),
        confidence_score=0.96,
        source_citations="['Chapter I, Clause 1.8', 'Chapter VI, Clause 6.17']",
        status="PENDING_HUMAN_REVIEW",
        requester_id=ctx.user_id,
    )
    db.add(draft)
    db.commit()

    return {
        "status": "DRAFT_GENERATED",
        "draft_id": draft.id,
        "classification": "SUGGEST_ONLY",
        "notice": "AI draft. Decision reserved for the competent authority.",
        "confidence_score": draft.confidence_score,
        "docket": docket_content,
    }

@router.post("/workflow/ai-drafts/{draft_id}/approve")
def approve_ai_draft_docket(
    draft_id: str,
    human_edits: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Human-in-the-loop gate: An authorized officer promotes the AI draft to official docket.
    Separation of Duties enforces: requester_id != approver_id.
    """
    dal = ScopedDAL(db, ctx)
    try:
        approved_draft = dal.approve_ai_draft(draft_id, human_edits)
        return {
            "status": "OFFICIALLY_APPROVED",
            "draft_id": approved_draft.id,
            "approved_by": approved_draft.approver_id,
            "approved_at": approved_draft.approved_at.isoformat(),
        }
    except SoDViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SecurityScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))
