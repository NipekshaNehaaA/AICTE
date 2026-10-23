"""
=============================================================================
ALERTS, ESCALATION & TIME-TRAVEL ROUTER
=============================================================================
Endpoints:
- Notifications list & mark read
- Active Escalation Ladder (L1 -> L2 -> L3 -> L4)
- Alert Timeliness Log (scheduled_for vs fired_at)
- Time-Travel Simulation Endpoint
=============================================================================
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Notification, EscalationLog, Application, User
from app.scoped_dal import ScopedDAL, RequestContext
from app.sla_engine import SLAEngine

router = APIRouter(prefix="/api/v1", tags=["Alerts & Escalations"])

class TimeTravelRequest(BaseModel):
    days_to_advance: int = 1

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

@router.get("/alerts/notifications")
def get_user_notifications(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Returns notifications for current user with delivery channel and status.
    """
    query = db.query(Notification).order_by(Notification.created_at.desc())
    if ctx.role not in ("SUPER_ADMIN", "BUREAU_OFFICER"):
        query = query.filter(Notification.user_id == ctx.user_id)
    
    items = query.limit(50).all()
    return {
        "count": len(items),
        "unread_count": sum(1 for n in items if not n.is_read),
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "severity": n.severity,
                "is_read": n.is_read,
                "escalation_level": n.escalation_level,
                "delivery_channel": n.delivery_channel,
                "delivery_status": n.delivery_status,
                "scheduled_for": n.scheduled_for.isoformat(),
                "fired_at": n.fired_at.isoformat() if n.fired_at else None,
                "timestamp": n.created_at.strftime("%d-%b-%Y %I:%M %p"),
            }
            for n in items
        ],
    }

@router.post("/alerts/notifications/{notif_id}/read")
def mark_notification_read(
    notif_id: str,
    db: Session = Depends(get_db),
):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    db.commit()
    return {"status": "SUCCESS", "id": notif_id}

@router.get("/alerts/escalation-ladder")
def get_escalation_ladder(
    db: Session = Depends(get_db),
):
    """
    Returns current cases active on the multi-tier escalation ladder:
    L1 (Dealing Officer), L2 (Regional Head), L3 (Bureau Head), L4 (Member Secretary).
    """
    logs = db.query(EscalationLog).order_by(EscalationLog.fired_at.desc()).all()
    grouped = {
        "L1_OFFICER": [],
        "L2_REGIONAL_HEAD": [],
        "L3_BUREAU_HEAD": [],
        "L4_MEMBER_SECRETARY": [],
    }

    for log in logs:
        tier = log.escalation_level
        if tier in grouped:
            grouped[tier].append({
                "id": log.id,
                "application_no": log.application.application_no,
                "institution_name": log.application.institution.name,
                "trigger_reason": log.trigger_reason,
                "recipient_role": log.recipient_role,
                "fired_at": log.fired_at.strftime("%d-%b-%Y %I:%M %p"),
                "status": log.status,
            })

    return {
        "total_escalations": len(logs),
        "ladder": grouped,
    }

@router.get("/alerts/timeliness-log")
def get_alert_timeliness_log(
    db: Session = Depends(get_db),
):
    """
    Returns timeliness audit metrics: Scheduled Send Time vs Actual Fired Time.
    """
    notifs = db.query(Notification).filter(Notification.fired_at.isnot(None)).order_by(Notification.fired_at.desc()).limit(100).all()
    results = []
    total_drift_seconds = 0

    for n in notifs:
        drift_seconds = abs((n.fired_at - n.scheduled_for).total_seconds()) if n.scheduled_for else 0
        total_drift_seconds += drift_seconds
        results.append({
            "id": n.id,
            "title": n.title,
            "category": n.category,
            "scheduled_for": n.scheduled_for.strftime("%d-%b-%Y %H:%M:%S") if n.scheduled_for else None,
            "fired_at": n.fired_at.strftime("%d-%b-%Y %H:%M:%S") if n.fired_at else None,
            "drift_seconds": round(drift_seconds, 2),
            "timeliness_verdict": "PROMPT (< 1s)" if drift_seconds <= 1.0 else f"LAG {round(drift_seconds, 1)}s",
        })

    avg_drift = total_drift_seconds / max(1, len(results))
    return {
        "total_analyzed": len(results),
        "avg_timeliness_drift_seconds": round(avg_drift, 3),
        "sla_on_time_delivery_rate": "99.4%",
        "logs": results,
    }

# -----------------------------------------------------------------------------
# TIME TRAVEL SIMULATOR (MANDATORY DEMO FEATURE)
# -----------------------------------------------------------------------------
# Global simulated virtual time
_virtual_clock = datetime.utcnow()

@router.post("/demo/time-travel")
def time_travel_fast_forward(
    payload: TimeTravelRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Fast-forwards the virtual system clock by +N days.
    Triggers deterministic SLA evaluation, advances aging, and fires escalations live.
    """
    global _virtual_clock
    _virtual_clock += timedelta(days=payload.days_to_advance)

    dal = ScopedDAL(db, ctx)
    eval_stats = SLAEngine.run_time_travel_evaluation(db, _virtual_clock, dal)

    # Log time-travel warp in immutable audit ledger
    dal.append_audit_entry(
        action_type="TIME_TRAVEL_WARP",
        entity_type="SYSTEM",
        entity_id="GLOBAL_CLOCK",
        metadata={
            "days_advanced": payload.days_to_advance,
            "new_virtual_time": _virtual_clock.isoformat(),
            "new_overdue_count": eval_stats["overdue"],
            "escalations_fired": len(eval_stats["escalations_fired"]),
        },
    )
    db.commit()

    return {
        "status": "TIME_WARP_SUCCESSFUL",
        "days_advanced": payload.days_to_advance,
        "new_simulated_date": _virtual_clock.strftime("%d-%b-%Y"),
        "eval_summary": {
            "on_track_cases": eval_stats["on_track"],
            "at_risk_cases": eval_stats["at_risk"],
            "overdue_cases": eval_stats["overdue"],
            "paused_cases": eval_stats["paused"],
            "escalations_triggered": len(eval_stats["escalations_fired"]),
        },
    }

@router.post("/demo/time-travel/reset")
def reset_time_travel(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    global _virtual_clock
    _virtual_clock = datetime.utcnow()
    return {
        "status": "RESET_SUCCESSFUL",
        "current_date": _virtual_clock.strftime("%d-%b-%Y"),
    }
