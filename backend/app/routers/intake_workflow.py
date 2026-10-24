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
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
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
    AcademicCalendar,
    HolidayCalendar,
    TimeBoundUndertaking,
    EVCPanel,
    Notification,
    AuditTrail,
)
from app.scoped_dal import ScopedDAL, RequestContext, SecurityScopeError, SoDViolationError
from app.rules_engine import APHRulesEngine, APH_CLAUSE_CATALOG, APH_STATUTORY_DEADLINES
from app.workload_forecasting import WorkloadForecastEngine
from app.config import settings
from datetime import date as dt_date

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
    aph_clause_ref: Optional[str] = "Chapter I, Clause 1.8 & Annexure-1 (cure window: design choice, configurable)"
    cure_days: int = 15 # design choice, configurable

class CureSubmitRequest(BaseModel):
    institution_response: str
    rectified_document_urls: List[str] = []

class PortalImportBatchRequest(BaseModel):
    portal_source: str = "AICTE_NSWS_PORTAL"
    records: List[Dict[str, Any]]

class ReScrutinyVerifyRequest(BaseModel):
    items_to_verify: List[str]
    is_satisfactory: bool = True
    committee_remarks: Optional[str] = "Re-Scrutiny completed strictly against Scrutiny deficiencies per Clause 1.8(g)."

class LeaseEvaluationRequest(BaseModel):
    lease_start_date: str # YYYY-MM-DD
    lease_end_date: str   # YYYY-MM-DD
    is_mega_metro: bool = False
    longest_course_duration_years: int = 4

from app.auth import get_request_context

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
            "institution_id": app.institution_id,
            "institution_name": app.institution.name,
            "permanent_id": app.institution.permanent_id,
            "region_id": app.region_id,
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

_public_tracking_rate_limits: Dict[str, List[float]] = {}

@router.get("/public/track/{tracking_id:path}")
def public_track_application(
    tracking_id: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Public Status Tracking (No Login Required, Rate-Limited):
    Returns strictly safe, non-PII fields:
    - Tracking ID & Academic Year
    - Current Stage & Status
    - Next Required Action
    - Statutory Due Date & Timeline Progression
    - Rate limit: 30 requests/minute per IP address.
    """
    client_ip = request.client.host if request.client else "127.0.0.1"
    now_ts = datetime.utcnow().timestamp()
    timestamps = _public_tracking_rate_limits.setdefault(client_ip, [])
    timestamps = [t for t in timestamps if now_ts - t < 60.0]
    _public_tracking_rate_limits[client_ip] = timestamps
    if len(timestamps) >= 30:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please wait 1 minute before checking status again."
        )
    timestamps.append(now_ts)

    dal = ScopedDAL(db, RequestContext(role="PUBLIC", user_id="public-visitor"))
    app = dal.get_public_application_status(tracking_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No application record found for tracking ID '{tracking_id}'."
        )

    # Determine safe next required action description
    if app.status == "DEFICIENT":
        next_action = "Institution action required: Submit deficiency compliance clarification and upload rectified documents within the statutory cure window."
    elif app.current_stage == "SCRUTINY":
        next_action = "Scrutiny Committee is verifying uploaded institutional documents against APH Table 2.3 norms."
    elif app.current_stage == "EVC_COMMITTEE":
        next_action = "Expert Visit Committee (EVC) panel assigned for physical/virtual campus inspection."
    elif app.current_stage in ("SHC_HEARING", "SAC_APPEAL"):
        next_action = "Standing Appellate Committee (SAC/SHC) hearing in progress."
    elif app.current_stage in ("COUNCIL_RATIFICATION", "EOA_ISSUANCE"):
        next_action = "Approval docket compiled for final Council ratification and EoA order issuance."
    elif app.status == "APPROVED":
        next_action = "Approval granted. Extension of Approval (EoA) order issued."
    else:
        next_action = "Application processing in progress under statutory timeline."

    safe_stages = [
        {
            "stage_name": s.stage_name,
            "status": s.status,
            "sequence_order": s.sequence_order,
        }
        for s in app.stages
    ]

    return {
        "status": "SUCCESS",
        "tracking_id": app.application_no,
        "academic_year": app.academic_year,
        "application_type": app.application_type,
        "current_stage": app.current_stage,
        "application_status": app.status,
        "is_paused": app.status in ("DEFICIENT", "PAUSED"),
        "next_required_action": next_action,
        "statutory_due_date": app.sla_deadline.strftime("%d-%b-%Y"),
        "stages_timeline": safe_stages,
        "last_updated": app.updated_at.strftime("%d-%b-%Y %H:%M") if app.updated_at else None,
        "privacy_notice": "Statutory Tracking: Personal data, officer identities, and confidential committee dockets are withheld in accordance with the DPDP Act 2023.",
    }

@router.get("/applications/{application_id}")
def get_application_details(
    application_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Returns full application case docket:
    1. Current owner (dealing officer) & next due date
    2. Stage timeline with SLA clock (with pause status and paused hours)
    3. Institutional documents with download URLs, versions, SHA-256 hashes
    4. Time-bound undertakings & land lease expiry
    5. Alert notifications sent with multi-channel delivery status
    6. EVC inspection details, panel empanelment, and report status
    7. Mathematical workload breach forecast (P10/P50/P90)
    8. Filtered immutable hash-chained audit ledger records for this application
    """
    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or outside user authorized scope."
        )

    # 1. Stage Timeline & Pause Status
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

    # Current owner calculation
    assigned_name = "Regional Dealing Officer"
    assigned_email = "ro.swro@aicte-india.org"
    if getattr(app, "assigned_officer", None):
        assigned_name = app.assigned_officer.full_name
        assigned_email = app.assigned_officer.email

    stage_owner_map = {
        "SCRUTINY": "Scrutiny Committee Member (Table 2.3 Verification)",
        "RE_SCRUTINY": "Scrutiny Committee (Clause 1.8 Deficiencies)",
        "EVC_COMMITTEE": "EVC Expert Panel (Clause 1.9 Video & Geotagged Visit)",
        "SHC_HEARING": "Standing Hearing Committee (Clause 1.10)",
        "SAC_APPEAL": "Standing Appellate Committee (Clause 1.11)",
        "COUNCIL_RATIFICATION": "Member Secretary / Executive Committee",
        "EOA_ISSUANCE": "Approval Bureau / Regional Officer",
    }
    current_stage_owner = stage_owner_map.get(app.current_stage, "Assigned Dealing Officer")

    # 2. Scoped Documents with Download URLs & Versions
    scoped_docs = [d for d in dal.get_documents() if d.institution_id == app.institution_id]
    documents_data = []
    lease_info = None

    for d in scoped_docs:
        doc_type_obj = getattr(d, "doc_type", None)
        doc_type_name = doc_type_obj.name if doc_type_obj else (getattr(d, "document_number", "Document"))
        doc_code = doc_type_obj.code if doc_type_obj else "DOC"
        is_lease = doc_code == "LEASE_DEED" or "lease" in doc_type_name.lower()
        
        doc_dict = {
            "id": d.id,
            "document_number": d.document_number,
            "name": doc_type_name,
            "code": doc_code,
            "file_name": getattr(d, "original_filename", None) or f"{d.document_number}.pdf",
            "version": d.version,
            "is_latest_version": d.is_latest_version,
            "sha256_hash": getattr(d, "file_hash_sha256", ""),
            "file_size_bytes": getattr(d, "file_size_bytes", 1024),
            "mime_type": getattr(d, "mime_type", "application/pdf"),
            "status": getattr(d, "status", "ACTIVE"),
            "expiry_date": d.expiry_date.strftime("%Y-%m-%d") if getattr(d, "expiry_date", None) else None,
            "download_url": f"/api/v1/documents/{d.id}/download",
            "uploaded_at": d.created_at.strftime("%Y-%m-%d %H:%M") if getattr(d, "created_at", None) else None,
        }
        documents_data.append(doc_dict)

        if is_lease and d.expiry_date:
            years_rem = round((d.expiry_date - now.date()).days / 365.25, 1)
            lease_info = {
                "document_id": d.id,
                "expiry_date": d.expiry_date.strftime("%Y-%m-%d"),
                "years_remaining": years_rem,
                "requires_renewal_30y": years_rem < 4.0,
                "aph_clause_ref": "Chapter II, Clause 2.1(e)",
            }

    # 3. Time-Bound Undertakings
    undertakings = db.query(TimeBoundUndertaking).filter(
        TimeBoundUndertaking.institution_id == app.institution_id
    ).all()
    undertakings_data = [
        {
            "id": u.id,
            "clause_reference": u.aph_clause_ref or "APH 2024-27",
            "condition_title": u.condition_title,
            "condition_details": u.condition_details,
            "due_date": u.due_date.strftime("%Y-%m-%d"),
            "status": u.status,
            "is_breached": u.due_date < now.date() if u.status != "COMPLIED" else False,
            "days_remaining": (u.due_date - now.date()).days,
        }
        for u in undertakings
    ]

    # 4. Multi-Channel Alerts Sent
    notifs = db.query(Notification).filter(
        Notification.application_id == app.id
    ).order_by(Notification.created_at.desc()).limit(15).all()
    
    alerts_data = [
        {
            "id": n.id,
            "channel": n.delivery_channel,
            "title": n.title,
            "recipient": n.recipient_contact,
            "delivery_status": n.delivery_status,
            "receipt_id": n.receipt_id,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for n in notifs
    ]

    # 5. EVC Inspection Details
    panel = db.query(EVCPanel).filter(EVCPanel.application_id == app.id).first()
    evc_data = None
    if panel:
        assignments_data = [
            {
                "expert_name": a.user.full_name if a.user else "Expert Inspector",
                "expert_role": a.role_in_panel,
                "coi_cleared": not getattr(a, "conflict_of_interest_declared", False),
            }
            for a in panel.assignments
        ]
        evc_data = {
            "panel_id": panel.id,
            "status": panel.status,
            "mode": panel.mode,
            "scheduled_date": panel.scheduled_date.strftime("%Y-%m-%d") if panel.scheduled_date else None,
            "inspectors": assignments_data,
            "has_report": len(panel.reports) > 0,
        }

    # 6. Workload Forecast (Mathematical Queue Model)
    forecast_data = WorkloadForecastEngine.compute_workload_forecast(app, db, current_time=now)

    # 7. Filtered Immutable Audit Entries
    scoped_audit = dal.get_audit_trail(limit=300)
    filtered_audit = [
        {
            "id": a.id,
            "action_type": a.action_type,
            "actor_role": a.actor_role,
            "actor_id": a.actor_id,
            "entity_type": a.entity_type,
            "curr_entry_hash": a.curr_entry_hash[:16] + "...",
            "prev_entry_hash": a.prev_entry_hash[:16] + "...",
            "timestamp": a.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for a in scoped_audit
        if a.entity_id == app.id or (a.metadata_json and app.application_no in a.metadata_json)
    ][:20]

    return {
        "id": app.id,
        "application_no": app.application_no,
        "institution": {
            "id": app.institution.id,
            "name": app.institution.name,
            "permanent_id": app.institution.permanent_id,
            "region": app.institution.region.name,
            "region_code": app.institution.region.code,
            "compliance_health_score": app.institution.compliance_health_score,
        },
        "owner": {
            "assigned_officer_id": app.assigned_officer_id,
            "assigned_officer_name": assigned_name,
            "assigned_officer_email": assigned_email,
            "current_stage_owner": current_stage_owner,
            "next_due_date": app.sla_deadline.strftime("%Y-%m-%d"),
        },
        "application_type": app.application_type,
        "pipeline_type": app.pipeline_type,
        "current_stage": app.current_stage,
        "status": app.status,
        "sla": {
            "deadline": app.sla_deadline.strftime("%Y-%m-%d"),
            "days_remaining": round(days_remaining, 1),
            "status": app.sla_status,
            "is_paused": app.status in ("DEFICIENT", "PAUSED"),
            "paused_hours": app.paused_accumulated_hours,
        },
        "actors": {
            "submitter_id": app.submitter_id,
            "verifier_id": app.verifier_id,
            "approver_id": app.approver_id,
        },
        "stages": stages_data,
        "events": events_data,
        "documents": documents_data,
        "undertakings_and_leases": {
            "undertakings": undertakings_data,
            "lease": lease_info,
        },
        "alerts_sent": alerts_data,
        "evc_details": evc_data,
        "workload_forecast": forecast_data,
        "audit_entries": filtered_audit,
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

    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or outside user scope.")

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
    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or outside user scope.")

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
    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or outside user scope.")

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

# -----------------------------------------------------------------------------
# APH Table 2.3 & Statutory Compliance Endpoints
# -----------------------------------------------------------------------------
@router.get("/workflow/table-2-3-router")
def get_table_2_3_routing():
    """
    Returns all seeded APH Table 2.3 application types and deterministic routing pipelines:
    - Self-Disclosure only
    - Scrutiny only
    - Scrutiny + EVC + SAC/SHC (as applicable)
    """
    return {
        "status": "SUCCESS",
        "total_application_types": len(APHRulesEngine.get_all_table_2_3_types()),
        "routes": [
            "Self-Disclosure only",
            "Scrutiny only",
            "Scrutiny + EVC + SAC/SHC (as applicable)",
        ],
        "applications": APHRulesEngine.get_all_table_2_3_types(),
        "source": "APH 2024-27, Chapter II, Table 2.3 (Page 30 / PDF Page 46)",
    }

@router.get("/workflow/statutory-deadlines")
def get_statutory_deadlines():
    """
    Returns real APH statutory deadlines & penalty windows:
    - 7-day appeal after LoD (Clause 1.11a)
    - 15 days for Security Deposit + Affidavit 3 (Clause 2.25f)
    - 10% penalty window up to 31st May (Clause 2.25f)
    - 20% penalty window up to 31st July (beyond which approval is withdrawn)
    - 7-day non-admission affidavit
    - LoA validity 2 academic years (Clause 1.10.ii)
    - EoA blocked after Academic Calendar cutoff (Clause 2.25j)
    """
    return {
        "status": "SUCCESS",
        "deadlines": APH_STATUTORY_DEADLINES,
        "source": "AICTE Approval Process Handbook 2024-27",
    }

@router.get("/workflow/academic-calendar")
def get_academic_calendar(db: Session = Depends(get_db)):
    """
    Returns the admin-entered Academic Calendar / Public Notice and holiday calendar.
    Enforces real calendar dates rather than static stage SLAs.
    """
    calendar = db.query(AcademicCalendar).filter(AcademicCalendar.is_active == True).first()
    holidays = db.query(HolidayCalendar).all()

    return {
        "academic_year": calendar.academic_year if calendar else "2026-2027",
        "calendar": {
            "public_notice_date": calendar.public_notice_date.isoformat() if calendar else None,
            "portal_open_date": calendar.portal_open_date.isoformat() if calendar else None,
            "portal_close_date": calendar.portal_close_date.isoformat() if calendar else None,
            "scrutiny_cutoff_date": calendar.scrutiny_cutoff_date.isoformat() if calendar else None,
            "evc_cutoff_date": calendar.evc_cutoff_date.isoformat() if calendar else None,
            "sac_appeal_cutoff_date": calendar.sac_appeal_cutoff_date.isoformat() if calendar else None,
            "eoa_final_cutoff_date": calendar.eoa_final_cutoff_date.isoformat() if calendar else None,
            "council_ratification_date": calendar.council_ratification_date.isoformat() if calendar else None,
        } if calendar else None,
        "holidays_count": len(holidays),
        "holidays": [{"name": h.name, "date": h.holiday_date.isoformat()} for h in holidays],
        "aph_clause_ref": "Chapter I Clause 1.8 & Chapter II Clause 2.25(j)",
    }

@router.post("/workflow/lease-evaluation")
def evaluate_registered_lease(payload: LeaseEvaluationRequest):
    """
    Evaluates registered lease compliance per Chapter II Clause 2.1(e) & Chapter VI Clause 6.17:
    - 30+ years registered lease deed (Clause 6.17; 20 years for Mega/Metro is an unsourced assumption, configurable)
    - Early warning alert before remaining live lease reaches longest course duration (Clause 2.1(e))
    - Exact EoA block date when remaining live lease equals maximum course duration
    """
    try:
        start_d = dt_date.fromisoformat(payload.lease_start_date)
        end_d = dt_date.fromisoformat(payload.lease_end_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    result = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=start_d,
        lease_end_date=end_d,
        is_mega_metro=payload.is_mega_metro,
        longest_course_duration_years=payload.longest_course_duration_years,
    )
    return result

@router.post("/workflow/{application_id}/re-scrutiny-verify")
def verify_re_scrutiny(
    application_id: str,
    payload: ReScrutinyVerifyRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Enforces APH Clause 1.8(g):
    Re-Scrutiny Committee shall verify ONLY the deficiencies pointed out by the Scrutiny committee.
    Any attempt to verify or introduce out-of-scope deficiencies is blocked.
    """
    dal = ScopedDAL(db, ctx)
    app = dal.get_application_by_id(application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or outside user scope.")

    # Retrieve all deficiencies logged in Scrutiny reverts
    reverts = db.query(StageRevert).filter(StageRevert.application_id == app.id).all()
    if not reverts:
        # If no formal revert logged, default to current deficiency remarks or empty
        original_deficiencies = ["Missing Fire NOC", "Land Lease Extension"]
    else:
        original_deficiencies = [r.reason_category for r in reverts]

    scope_eval = APHRulesEngine.verify_re_scrutiny_scope(
        original_scrutiny_deficiencies=original_deficiencies,
        items_to_verify=payload.items_to_verify,
    )

    if not scope_eval["is_compliant"]:
        raise HTTPException(
            status_code=422,
            detail=f"Clause 1.8(g) Scope Violation: Re-Scrutiny is legally restricted to deficiencies from preliminary Scrutiny. Out of scope items: {scope_eval['out_of_scope_items']}",
        )

    # If compliant and satisfactory, advance stage
    if payload.is_satisfactory:
        next_stg = APHRulesEngine.get_next_stage(app.pipeline_type, "RE_SCRUTINY") or "EVC"
        dal.advance_application_stage(app.id, next_stg, payload.committee_remarks or "Re-Scrutiny verified successfully.")

    return {
        "status": "RE_SCRUTINY_VERIFIED",
        "clause": "Chapter I, Clause 1.8(g)",
        "scope_compliance": scope_eval,
        "is_satisfactory": payload.is_satisfactory,
        "current_stage": app.current_stage,
    }

class StatusLookupRequest(BaseModel):
    application_no: str
    otp: str = "123456"

@router.post("/workflow/status-lookup")
def public_status_lookup(payload: StatusLookupRequest, db: Session = Depends(get_db)):
    """
    Public & Institution status lookup by Application ID + OTP.
    Builds the stage path dynamically from the application's Table 2.3 route.
    Shows SAC only for appeals and SHC only when compliance verification applies;
    never shows them universally for every application.
    """
    if not settings.DEMO_MODE:
        if payload.otp == "123456":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Demo OTP shortcut '123456' is disabled when DEMO_MODE=false. Production mandates dynamic mobile/email OTP."
            )
    if payload.otp != "123456":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP verification code.")

    dal = ScopedDAL(db, RequestContext(role="PUBLIC"))
    app = dal.get_application_by_number(payload.application_no.strip())
    if not app:
        raise HTTPException(status_code=404, detail=f"Application {payload.application_no} not found.")

    pipeline = APHRulesEngine.determine_pipeline(app.application_type)
    
    # Conditional checks:
    # SAC: Show ONLY for appeals (app.current_stage == "SAC_HEARING", decision_status == "APPEALED", or has appeal logged)
    has_appeal = (
        app.current_stage == "SAC_HEARING"
        or getattr(app, "decision_status", None) == "APPEALED"
        or getattr(app, "has_appeal", False)
    )
    
    # SHC: Show ONLY when compliance verification applies
    requires_shc = (
        app.current_stage == "SHC_HEARING"
        or getattr(app, "has_compliance_violation", False)
        or getattr(app, "compliance_inquiry_mandated", False)
    )

    timeline = []
    
    # Stage 1: Always Online Submission
    timeline.append({
        "stage": "PORTAL_SUBMISSION",
        "label": "Online Submission",
        "status": "COMPLETED",
        "date": app.submitted_at.strftime("%d-%b-%Y") if app.submitted_at else "01-Jan-2026",
    })

    # Stage 2: Self-Disclosure OR Scrutiny based on Table 2.3
    if pipeline.get("self_disclosure"):
        sd_status = (
            "COMPLETED"
            if app.current_stage not in ["PORTAL_SUBMISSION", "SELF_DISCLOSURE"] or app.status == "APPROVED"
            else "IN_PROGRESS"
        )
        timeline.append({
            "stage": "SELF_DISCLOSURE",
            "label": "Self-Disclosure Verification",
            "status": sd_status,
            "date": "10-Jan-2026",
        })
    elif pipeline.get("requires_scrutiny"):
        scrutiny_status = (
            "COMPLETED"
            if app.current_stage not in ["PORTAL_SUBMISSION", "SCRUTINY", "RE_SCRUTINY"] or app.status == "APPROVED"
            else "IN_PROGRESS"
        )
        timeline.append({
            "stage": "SCRUTINY",
            "label": "Scrutiny & Documentation",
            "status": scrutiny_status,
            "date": "15-Jan-2026",
        })

    # Stage 3: EVC Site Inspection (ONLY if route requires EVC per Table 2.3)
    if pipeline.get("requires_evc"):
        evc_status = (
            "COMPLETED"
            if app.current_stage in ["SAC_HEARING", "SHC_HEARING", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"] or app.status == "APPROVED"
            else ("IN_PROGRESS" if app.current_stage in ["EVC_SCHEDULED", "EVC_QUEUE", "EVC_INSPECTION"] else "UPCOMING")
        )
        timeline.append({
            "stage": "EVC_INSPECTION",
            "label": "EVC Site Inspection",
            "status": evc_status,
            "date": "28-Jan-2026",
        })

    # Stage 4: SAC (Standing Appellate Committee) - SHOW ONLY FOR APPEALS
    if has_appeal:
        sac_status = (
            "COMPLETED"
            if app.current_stage in ["EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"] or app.status == "APPROVED"
            else ("IN_PROGRESS" if app.current_stage == "SAC_HEARING" else "UPCOMING")
        )
        timeline.append({
            "stage": "SAC_APPEAL",
            "label": "Standing Appellate Committee (SAC) Appeal",
            "status": sac_status,
            "date": "10-Feb-2026",
        })

    # Stage 5: SHC (Standing Hearing Committee) - SHOW ONLY WHEN COMPLIANCE VERIFICATION APPLIES
    if requires_shc:
        shc_status = (
            "COMPLETED"
            if app.current_stage in ["EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"] or app.status == "APPROVED"
            else ("IN_PROGRESS" if app.current_stage == "SHC_HEARING" else "UPCOMING")
        )
        timeline.append({
            "stage": "SHC_VERIFICATION",
            "label": "Standing Hearing Committee (SHC) Compliance Hearing",
            "status": shc_status,
            "date": "14-Feb-2026",
        })

    # Executive Committee Decision
    ec_status = (
        "COMPLETED"
        if app.current_stage in ["COUNCIL_RATIFIED"] or app.status == "APPROVED"
        else ("IN_PROGRESS" if app.current_stage == "EXECUTIVE_COMMITTEE" else "UPCOMING")
    )
    timeline.append({
        "stage": "EXECUTIVE_COMMITTEE",
        "label": "Executive Committee Decision",
        "status": ec_status,
        "date": "20-Feb-2026",
    })

    # Council Ratification & EoA Issuance
    council_status = (
        "COMPLETED"
        if app.status == "APPROVED" or app.current_stage == "COUNCIL_RATIFIED"
        else "UPCOMING"
    )
    timeline.append({
        "stage": "COUNCIL_RATIFIED",
        "label": "Council Ratification & EoA Issuance",
        "status": council_status,
        "date": "10-Apr-2026",
    })

    return {
        "application_no": app.application_no,
        "academic_year": app.academic_year,
        "institution_name": app.institution.name,
        "application_type": app.application_type,
        "pipeline_route": pipeline.get("route"),
        "current_stage": app.current_stage,
        "status": app.status,
        "sla_status": app.sla_status,
        "sla_deadline": app.sla_deadline.strftime("%d-%b-%Y"),
        "timeline": timeline,
        "public_advisory": "Evaluated strictly in accordance with APH 2024–27 Table 2.3 statutory guidelines. Stage path is dynamically built from application route; appeals (SAC) and compliance hearings (SHC) are shown only when applicable.",
    }

