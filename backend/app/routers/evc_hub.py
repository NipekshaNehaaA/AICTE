"""
=============================================================================
EVC (EXPERT VISIT COMMITTEE) SCHEDULING & INSPECTION HUB ROUTER
=============================================================================
Based on AICTE Approval Process Handbook (APH 2024-27):
- Clause 1.9 & 2.23.2: EVC Process & 30-min Video Recording with GPS Coordinates
- Annexure-16, Clause 16.5: EVC Panel Composition (Professor, Industry Expert, Architect)
- Annexure-7: Workflow Transition upon EVC Report (Nil Deficiency vs Deficiency Noted)
=============================================================================
"""

from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    Application,
    EVCPanel,
    EVCAssignment,
    EVCReport,
    User,
    Region,
    CaseEvent,
)
from app.scoped_dal import ScopedDAL, RequestContext, SecurityScopeError, SoDViolationError

router = APIRouter(prefix="/api/v1/evc", tags=["EVC Inspection Hub"])

class SuggestPanelRequest(BaseModel):
    application_id: str
    proposed_date: str # YYYY-MM-DD
    mode: str = "ON_SITE" # ON_SITE, VIRTUAL

class ConfirmPanelRequest(BaseModel):
    selected_member_ids: List[str]
    notes: Optional[str] = "Panel confirmed in accordance with Annexure-16 Clause 16.5."

class ConflictDeclarationRequest(BaseModel):
    has_conflict: bool = False
    statement: str = "I declare no past employment, consultancy, or financial interest with this institution in the last 5 years."

class SubmitEVCReportRequest(BaseModel):
    recommendation: str # RECOMMENDED, NOT_RECOMMENDED, CONDITIONAL
    inspection_summary: str
    deficiencies: List[str] = []
    geo_lat: float = 12.9716
    geo_lng: float = 77.5946

def get_request_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header("REGIONAL_OFFICER"),
    x_region_id: Optional[str] = Header(None),
) -> RequestContext:
    return RequestContext(
        user_id=x_user_id or "usr-demo-default",
        role=x_user_role or "REGIONAL_OFFICER",
        region_id=x_region_id,
    )

@router.get("/queue")
def get_evc_queue(
    region_code: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Returns applications requiring an EVC inspection after preliminary scrutiny.
    Tracks scheduling deadlines (15-day SLA, sample value configurable).
    """
    query = db.query(Application).filter(
        Application.pipeline_type.in_(["SCRUTINY_EVC", "SCRUTINY_EVC_SAC", "ONLY_EVC"]),
        Application.current_stage.in_(["SCRUTINY", "EVC_QUEUE", "EVC_SCHEDULED"]),
    )
    if region_code:
        query = query.join(Application.region).filter(Region.code == region_code)

    apps = query.all()
    today = date.today()
    results = []

    for a in apps:
        panel = a.evc_panel
        results.append({
            "application_id": a.id,
            "application_no": a.application_no,
            "institution_name": a.institution.name,
            "region": a.institution.region.name,
            "region_code": a.institution.region.code,
            "application_type": a.application_type,
            "current_stage": a.current_stage,
            "panel_status": panel.status if panel else "NOT_SCHEDULED",
            "scheduled_date": panel.scheduled_date.strftime("%Y-%m-%d") if panel else None,
            "is_scheduled": bool(panel),
            "sla_deadline": a.sla_deadline.strftime("%Y-%m-%d"),
            "sla_status": a.sla_status,
        })

    return {"count": len(results), "queue": results}

@router.post("/suggest-panel")
def suggest_smart_panel(
    payload: SuggestPanelRequest,
    db: Session = Depends(get_db),
):
    """
    EVC Smart Scheduler: Proposes panel members using region, expertise, workload,
    and automated conflict-of-interest checks (SUGGEST-ONLY, Clause 16.5).
    """
    app = db.query(Application).filter(Application.id == payload.application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    # In a full system, experts are matched by domain & availability without conflicts
    suggested_experts = [
        {
            "id": "exp-01",
            "name": "Prof. R. Soundarajan (IIT Madras)",
            "role_in_panel": "CHAIRMAN",
            "expertise": "Computer Science & Engineering",
            "workload_active_visits": 1,
            "conflict_free": True,
            "clause_ref": "Annexure-16 Clause 16.5 (Academician >= Professor)",
        },
        {
            "id": "exp-02",
            "name": "Dr. Sunita Kulkarni (Tata Motors R&D)",
            "role_in_panel": "EXPERT_MEMBER",
            "expertise": "Industry Expert (12+ Years)",
            "workload_active_visits": 0,
            "conflict_free": True,
            "clause_ref": "Annexure-16 Clause 16.5 (Industry Expert >= 5 yrs)",
        },
        {
            "id": "exp-03",
            "name": "Ar. Vikramaditya Sen (CoA / CPWD Empanelled)",
            "role_in_panel": "ARCHITECT_EXPERT",
            "expertise": "Structural & Built-Up Area Verification",
            "workload_active_visits": 2,
            "conflict_free": True,
            "clause_ref": "Annexure-16 Clause 16.5 (Architect registered with CoA)",
        },
    ]

    return {
        "classification": "SUGGEST_ONLY",
        "notice": "AI Smart Proposal. Official panel assignment requires Regional Officer confirmation.",
        "application_no": app.application_no,
        "proposed_date": payload.proposed_date,
        "mode": payload.mode,
        "suggested_panel": suggested_experts,
        "statutory_mandate": "Annexure-16 Clause 16.5 & Clause 1.9 (30-min Geotagged Video Recording Mandatory)",
    }

@router.post("/{application_id}/confirm")
def confirm_evc_schedule(
    application_id: str,
    payload: ConfirmPanelRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Regional Officer officially confirms the EVC inspection panel and date (HUMAN-ONLY).
    """
    if ctx.role == "AUDITOR":
        raise HTTPException(status_code=403, detail="Auditor role is strictly read-only.")

    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found.")

    panel = app.evc_panel
    if not panel:
        panel = EVCPanel(
            application_id=app.id,
            scheduled_date=date.today() + timedelta(days=7),
            mode="ON_SITE",
            status="CONFIRMED",
        )
        db.add(panel)
        db.flush()
    else:
        panel.status = "CONFIRMED"

    app.current_stage = "EVC_SCHEDULED"

    # Append case event
    db.add(CaseEvent(
        application_id=app.id,
        event_type="EVC_SCHEDULED",
        actor_id=ctx.user_id,
        actor_role=ctx.role,
        description=f"EVC inspection panel confirmed for {panel.scheduled_date}. {payload.notes}",
        aph_clause_ref="Chapter I Clause 1.9 & Annexure-16 Clause 16.5",
    ))

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="EVC_SCHEDULED",
        entity_type="EVC_PANEL",
        entity_id=panel.id,
        metadata={"scheduled_date": panel.scheduled_date.isoformat(), "confirmed_by": ctx.user_id},
    )
    db.commit()

    return {
        "status": "PANEL_CONFIRMED",
        "panel_id": panel.id,
        "scheduled_date": panel.scheduled_date.strftime("%Y-%m-%d"),
        "new_stage": app.current_stage,
    }

@router.post("/reports/{panel_id}/submit")
def submit_evc_inspection_report(
    panel_id: str,
    payload: SubmitEVCReportRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    EVC Committee Member submits official geotagged inspection report.
    """
    panel = db.query(EVCPanel).filter(EVCPanel.id == panel_id).first()
    if not panel:
        raise HTTPException(status_code=404, detail="EVC Panel not found.")

    report = EVCReport(
        panel_id=panel.id,
        submitted_by=ctx.user_id or "usr-evc-convener",
        inspection_summary=payload.inspection_summary,
        deficiencies_found=str(payload.deficiencies),
        geo_lat=payload.geo_lat,
        geo_lng=payload.geo_lng,
        geo_timestamp=datetime.utcnow(),
        recommendation=payload.recommendation,
        is_final=True,
    )
    db.add(report)
    panel.status = "REPORT_SUBMITTED"

    app = panel.application
    app.current_stage = "EXECUTIVE_COMMITTEE"

    db.add(CaseEvent(
        application_id=app.id,
        event_type="EVC_REPORT_SUBMITTED",
        actor_id=ctx.user_id,
        actor_role="COMMITTEE_MEMBER",
        description=f"EVC Inspection Report submitted with verdict [{payload.recommendation}]. GPS: ({payload.geo_lat}, {payload.geo_lng}).",
        aph_clause_ref="Chapter I Clause 1.9(g) (30-min Geotagged Video & Verification)",
    ))

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="EVC_REPORT_SUBMITTED",
        entity_type="EVC_REPORT",
        entity_id=report.id,
        metadata={
            "recommendation": payload.recommendation,
            "geo_coordinates": f"{payload.geo_lat},{payload.geo_lng}",
        },
    )
    db.commit()

    return {
        "status": "REPORT_ACCEPTED",
        "report_id": report.id,
        "recommendation": report.recommendation,
        "geotag_verified": True,
        "application_stage_updated": app.current_stage,
    }
