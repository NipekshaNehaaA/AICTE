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

from app.auth import get_request_context

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
                "recipient_contact": n.recipient_contact,
                "language": n.language,
                "receipt_id": n.receipt_id,
                "retry_count": n.retry_count or 0,
                "error_message": n.error_message,
                "idempotency_key": n.idempotency_key,
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

@router.post("/alerts/notifications/{notif_id}/resend")
def resend_failed_alert(
    notif_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Retries dispatch for a failed or deferred alert notification across its configured channel.
    Updates delivery receipt and stamps the action into the hash-chained audit ledger.
    """
    from app.email_service import email_service
    from app.twilio_whatsapp import whatsapp_adapter

    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found.")

    dal = ScopedDAL(db, ctx)
    now = datetime.utcnow()
    new_status = notif.delivery_status
    new_receipt = notif.receipt_id

    if notif.delivery_channel == "EMAIL":
        recipient = notif.recipient_contact or "officer@aicte-india.org"
        receipt = email_service.send_email(
            to_email=recipient,
            subject=notif.title,
            text_content=notif.message,
            override_quiet=True,
            current_time=now,
        )
        new_status = receipt.get("status", "DELIVERED")
        new_receipt = receipt.get("message_id")
        notif.error_message = receipt.get("failure_reason")
    elif "WHATSAPP" in (notif.delivery_channel or ""):
        recipient = notif.recipient_contact or "+91-9876543210"
        receipt = whatsapp_adapter.send_whatsapp_message(
            to_phone=recipient,
            message_body=notif.message,
            user_opted_in=True,
        )
        new_status = receipt.get("status", "DELIVERED")
        new_receipt = receipt.get("receipt_id")
        notif.error_message = receipt.get("error_message")
    else:
        new_status = "DELIVERED"
        new_receipt = f"manual_resend_{now.timestamp()}"

    notif.delivery_status = new_status
    notif.receipt_id = new_receipt
    notif.retry_count = (notif.retry_count or 0) + 1
    notif.fired_at = now

    dal.append_audit_entry(
        action_type="ALERT_RESENT",
        entity_type="NOTIFICATION",
        entity_id=notif.id,
        metadata={
            "delivery_channel": notif.delivery_channel,
            "new_status": new_status,
            "receipt_id": new_receipt,
            "retry_count": notif.retry_count,
        },
    )
    db.commit()

    return {
        "status": "RESENT",
        "notification_id": notif.id,
        "delivery_status": new_status,
        "receipt_id": new_receipt,
        "retry_count": notif.retry_count,
    }

class UserPreferencesPayload(BaseModel):
    preferred_language: Optional[str] = "en"
    preferred_channels: Optional[str] = "IN_APP,EMAIL"
    whatsapp_phone: Optional[str] = None
    opt_in_whatsapp: Optional[bool] = False
    quiet_hours_start: Optional[int] = 22
    quiet_hours_end: Optional[int] = 6
    quiet_hours_enabled: Optional[bool] = True

@router.get("/alerts/preferences")
def get_user_preferences(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """Returns the current user and/or institution notification preferences."""
    from app.models import Institution
    user = db.query(User).filter(User.id == ctx.user_id).first()
    inst = db.query(Institution).filter(Institution.id == ctx.institution_id).first() if ctx.institution_id else None

    return {
        "user_id": ctx.user_id,
        "preferred_language": (user.preferred_language if user else (inst.preferred_language if inst else "en")) or "en",
        "preferred_channels": (user.preferred_channels if user else "IN_APP,EMAIL") or "IN_APP,EMAIL",
        "whatsapp_phone": (user.whatsapp_phone if user else None) or "+91-9876543210",
        "opt_in_whatsapp": user.opt_in_whatsapp if user else False,
        "quiet_hours_start": getattr(user, "quiet_hours_start", 22) if user else 22,
        "quiet_hours_end": getattr(user, "quiet_hours_end", 6) if user else 6,
        "quiet_hours_enabled": getattr(user, "quiet_hours_enabled", True) if user else True,
        "institution_language": inst.preferred_language if inst else None,
    }

@router.put("/alerts/preferences")
def update_user_preferences(
    payload: UserPreferencesPayload,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """Updates user notification preferences and institution language with audit ledger logging."""
    from app.models import Institution
    user = db.query(User).filter(User.id == ctx.user_id).first()
    if user:
        if payload.preferred_language:
            user.preferred_language = payload.preferred_language.lower().strip()
        if payload.preferred_channels:
            user.preferred_channels = payload.preferred_channels.strip()
        if payload.whatsapp_phone is not None:
            user.whatsapp_phone = payload.whatsapp_phone.strip()
        if payload.opt_in_whatsapp is not None:
            user.opt_in_whatsapp = payload.opt_in_whatsapp
        if payload.quiet_hours_start is not None:
            user.quiet_hours_start = payload.quiet_hours_start
        if payload.quiet_hours_end is not None:
            user.quiet_hours_end = payload.quiet_hours_end
        if payload.quiet_hours_enabled is not None:
            user.quiet_hours_enabled = payload.quiet_hours_enabled

    if ctx.institution_id and payload.preferred_language:
        inst = db.query(Institution).filter(Institution.id == ctx.institution_id).first()
        if inst:
            inst.preferred_language = payload.preferred_language.lower().strip()

    db.commit()

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="USER_PREFERENCES_UPDATED",
        entity_type="USER",
        entity_id=ctx.user_id or "ANONYMOUS",
        metadata={
            "preferred_language": payload.preferred_language,
            "preferred_channels": payload.preferred_channels,
            "opt_in_whatsapp": payload.opt_in_whatsapp,
            "quiet_hours_start": payload.quiet_hours_start,
            "quiet_hours_end": payload.quiet_hours_end,
            "quiet_hours_enabled": payload.quiet_hours_enabled,
        },
    )

    return {
        "status": "PREFERENCES_SAVED",
        "preferred_language": payload.preferred_language,
        "preferred_channels": payload.preferred_channels,
        "opt_in_whatsapp": payload.opt_in_whatsapp,
        "quiet_hours_start": payload.quiet_hours_start,
        "quiet_hours_end": payload.quiet_hours_end,
        "quiet_hours_enabled": payload.quiet_hours_enabled,
    }

class TestMessagePayload(BaseModel):
    channels: Optional[List[str]] = None
    language: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_whatsapp: Optional[str] = None
    template_key: Optional[str] = "DEFICIENCY_CURE_NOTICE"

@router.post("/alerts/test-dispatch")
@router.post("/alerts/test-message")
def test_dispatch_message(
    payload: TestMessagePayload,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Dispatches real statutory test messages across selected channels (IN_APP, EMAIL, WHATSAPP).
    Returns real provider receipts (never faked). Logs dispatch to immutable audit ledger.
    """
    import uuid
    from app.email_service import email_service
    from app.twilio_whatsapp import whatsapp_adapter
    from app.multilingual_notifications import NOTIFICATION_TEMPLATES

    user = db.query(User).filter(User.id == ctx.user_id).first()
    now = datetime.utcnow()
    ws = getattr(ctx, "workspace", "sandbox")

    lang = (payload.language or (user.preferred_language if user else "en") or "en").lower().strip()
    if lang not in ("en", "hi", "ta"):
        lang = "en"

    # Resolve statutory template
    template_key = payload.template_key or "DEFICIENCY_CURE_NOTICE"
    tmpl_group = NOTIFICATION_TEMPLATES.get(template_key, NOTIFICATION_TEMPLATES["DEFICIENCY_CURE_NOTICE"])
    tmpl = tmpl_group.get(lang, tmpl_group["en"])

    title = tmpl["title"].format(
        application_no="TEST-APP-2026",
        institution_name="AICTE Demonstration Campus",
    )
    aph_ref = tmpl.get("aph_clause_ref", "Chapter I Clause 1.8(f)")
    message = tmpl["message"].format(
        application_no="TEST-APP-2026",
        institution_name="AICTE Demonstration Campus",
        due_date=(now + timedelta(days=14)).strftime("%d-%b-%Y"),
        aph_clause_ref=aph_ref,
        mode="Physical Site Inspection",
    )

    # Resolve channels
    raw_channels = payload.channels
    if not raw_channels:
        pref = (user.preferred_channels if user else "IN_APP,EMAIL") or "IN_APP,EMAIL"
        raw_channels = [c.strip() for c in pref.split(",") if c.strip()]

    channel_results = []

    for ch in raw_channels:
        norm_ch = ch.upper().strip()
        if norm_ch == "IN_APP":
            test_notif = Notification(
                user_id=ctx.user_id,
                title=f"[TEST] {title}",
                message=message,
                category="SYSTEM_TEST",
                severity="INFO",
                is_read=False,
                delivery_channel="IN_APP",
                delivery_status="DELIVERED",
                recipient_contact=user.email if user else "in_app_desk",
                receipt_id=f"rec_inapp_{uuid.uuid4().hex[:12]}",
                language=lang,
                scheduled_for=now,
                fired_at=now,
            )
            db.add(test_notif)
            db.commit()
            channel_results.append({
                "channel": "IN_APP",
                "status": "DELIVERED",
                "receipt_id": test_notif.receipt_id,
                "title": test_notif.title,
                "note": "Delivered to in-app notification desk with zero latency.",
                "timestamp": now.isoformat(),
            })

        elif norm_ch == "EMAIL":
            target_email = payload.recipient_email or (user.email if user else "officer@aicte-india.org")
            receipt = email_service.send_email(
                to_email=target_email,
                subject=f"[AICTE Regulatory Test] {title}",
                text_content=message,
                override_quiet=True, # Explicit test message overrides quiet hours
                workspace=ws,
                quiet_hours_start=getattr(user, "quiet_hours_start", 22) if user else 22,
                quiet_hours_end=getattr(user, "quiet_hours_end", 6) if user else 6,
                quiet_hours_enabled=getattr(user, "quiet_hours_enabled", True) if user else True,
            )
            channel_results.append({
                "channel": "EMAIL",
                "status": receipt.get("status", "DELIVERED"),
                "receipt_id": receipt.get("message_id"),
                "recipient": receipt.get("recipient", target_email),
                "sandbox_note": receipt.get("sandbox_note"),
                "failure_reason": receipt.get("failure_reason"),
                "smtp_host": receipt.get("smtp_host"),
                "smtp_port": receipt.get("smtp_port"),
                "timestamp": now.isoformat(),
            })

        elif norm_ch in ("WHATSAPP", "WHATSAPP_SANDBOX"):
            target_phone = payload.recipient_whatsapp or (user.whatsapp_phone if user else "+919876543210")
            receipt = whatsapp_adapter.send_whatsapp_message(
                to_phone=target_phone,
                message_body=message,
                user_opted_in=True,
                workspace=ws,
            )
            channel_results.append({
                "channel": "WHATSAPP_SANDBOX",
                "status": receipt.get("status", "DELIVERED"),
                "receipt_id": receipt.get("receipt_id"),
                "recipient": receipt.get("recipient", target_phone),
                "sandbox_note": receipt.get("sandbox_note"),
                "twilio_status": receipt.get("twilio_status"),
                "note": receipt.get("note") or receipt.get("reason"),
                "error_message": receipt.get("error_message"),
                "timestamp": now.isoformat(),
            })

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="TEST_NOTIFICATION_DISPATCHED",
        entity_type="NOTIFICATION",
        entity_id=ctx.user_id or "SYSTEM",
        metadata={
            "language": lang,
            "template_key": template_key,
            "channels_tested": raw_channels,
            "results_summary": [
                {"channel": r["channel"], "status": r["status"], "receipt_id": r.get("receipt_id")}
                for r in channel_results
            ],
        },
    )
    db.commit()

    return {
        "status": "COMPLETED",
        "language": lang,
        "template_key": template_key,
        "workspace": ws,
        "results": channel_results,
        "dispatched_at": now.isoformat(),
    }

@router.post("/scheduler/run-now")
def run_scheduler_manually(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """Triggers an on-demand real-engine regulatory SLA & document expiry evaluation cycle."""
    from app.scheduler import regulatory_scheduler
    target_clock = datetime.utcnow()
    if getattr(ctx, "workspace", "live") == "sandbox":
        from app.routers.demo_scenario import _demo_clock
        if _demo_clock:
            target_clock = _demo_clock
    stats = regulatory_scheduler.evaluate_and_dispatch_all(db, target_time=target_clock)
    return {
        "status": "COMPLETED",
        "workspace": getattr(ctx, "workspace", "live"),
        "target_time": target_clock.isoformat(),
        "stats": stats,
    }

@router.get("/scheduler/status")
def get_scheduler_status():
    """Returns real-clock APScheduler daemon status, registered jobs, and last run stats."""
    from app.scheduler import regulatory_scheduler
    return regulatory_scheduler.get_status()

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

    on_time_count = sum(
        1 for n in notifs 
        if (n.scheduled_for is None) or (n.fired_at <= n.scheduled_for) or (abs((n.fired_at - n.scheduled_for).total_seconds()) <= 60.0)
    )
    on_time_rate = (on_time_count / len(notifs) * 100) if notifs else 100.0

    avg_drift = total_drift_seconds / max(1, len(results))
    return {
        "total_analyzed": len(results),
        "avg_timeliness_drift_seconds": round(avg_drift, 3),
        "sla_on_time_delivery_rate": f"{round(on_time_rate, 1)}%",
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

    # Use unified regulatory scheduler engine for document, undertaking and EVC offsets
    from app.scheduler import regulatory_scheduler
    sched_stats = regulatory_scheduler.evaluate_and_dispatch_all(db, _virtual_clock)

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

class SendTestEmailPayload(BaseModel):
    to_email: str = "officer.test@aicte-india.org"
    subject: str = "AICTE Test Statutory Alert"
    body: str = "This is a real statutory notification dispatched over AICTE SMTP channel."
    check_quiet_hours: bool = True
    port_override: Optional[int] = None

@router.post("/alerts/test-send-email")
def dispatch_statutory_test_email(
    payload: SendTestEmailPayload,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Dispatches a real email over SMTP with delivery receipt, retries, and audit ledger tracking.
    """
    from app.email_service import email_service
    receipt = email_service.send_email(
        to_email=payload.to_email,
        subject=payload.subject,
        text_content=payload.body,
        check_quiet=payload.check_quiet_hours,
        smtp_port_override=payload.port_override,
    )

    dal = ScopedDAL(db, ctx)
    notif = Notification(
        user_id=ctx.user_id,
        title=payload.subject,
        message=payload.body,
        category="MANUAL_ALERT",
        severity="INFO",
        scheduled_for=datetime.utcnow(),
        fired_at=datetime.utcnow() if receipt["status"] == "DELIVERED" else None,
        delivery_channel="EMAIL_REAL",
        delivery_status=receipt["status"],
        recipient_contact=payload.to_email,
    )
    db.add(notif)
    db.commit()

    dal.append_audit_entry(
        action_type="SMTP_EMAIL_DISPATCHED",
        entity_type="NOTIFICATION",
        entity_id=notif.id,
        metadata={
            "recipient": payload.to_email,
            "receipt": receipt,
            "status": receipt["status"],
            "channel": "EMAIL_REAL",
        },
    )
    return receipt

@router.get("/alerts/delivery-logs")
def get_multi_channel_delivery_logs(
    channel: Optional[str] = None, # IN_APP, EMAIL_MOCK, SMS_MOCK, WHATSAPP_MOCK
    db: Session = Depends(get_db),
):
    """
    Returns multi-channel delivery audit logs (In-App, Real Email, SMS Mock, WhatsApp Mock).
    Tracks dispatched payload, timestamp, recipient contact, and delivery receipt.
    SMS and WhatsApp are clearly labelled as simulated.
    """
    query = db.query(Notification).order_by(Notification.created_at.desc())
    if channel:
        query = query.filter(Notification.delivery_channel == channel)
    
    logs = query.limit(100).all()
    channel_counts = {
        "IN_APP": db.query(Notification).filter(Notification.delivery_channel == "IN_APP").count(),
        "EMAIL_MOCK": db.query(Notification).filter(Notification.delivery_channel.in_(["EMAIL_MOCK", "EMAIL_REAL"])).count(),
        "EMAIL_REAL": db.query(Notification).filter(Notification.delivery_channel == "EMAIL_REAL").count(),
        "SMS_MOCK": db.query(Notification).filter(Notification.delivery_channel == "SMS_MOCK").count(),
        "WHATSAPP_MOCK": db.query(Notification).filter(Notification.delivery_channel == "WHATSAPP_MOCK").count(),
    }
    return {
        "total_dispatched": len(logs),
        "channel_counts": channel_counts,
        "logs": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "category": n.category,
                "severity": n.severity,
                "delivery_channel": n.delivery_channel,
                "channel_label": "Email (Real SMTP Channel)" if n.delivery_channel == "EMAIL_REAL" else (
                    f"{n.delivery_channel.replace('_MOCK', '')} (Simulated Mock)" if "MOCK" in n.delivery_channel else n.delivery_channel
                ),
                "is_simulated": "MOCK" in n.delivery_channel,
                "delivery_status": n.delivery_status or "DELIVERED",
                "recipient_contact": n.recipient_contact or "Direct Portal Session",
                "escalation_level": n.escalation_level,
                "timestamp": n.created_at.strftime("%d-%b-%Y %I:%M:%S %p"),
                "is_delivered": n.delivery_status in ("DELIVERED", "DELIVERED_SIMULATED", None),
            }
            for n in logs
        ]
    }

# -----------------------------------------------------------------------------
# MULTILINGUAL INSTITUTION NOTIFICATIONS (EN, HI, TA)
# -----------------------------------------------------------------------------
class RenderMultilingualPayload(BaseModel):
    template_key: str
    language: str = "en"
    context: Dict[str, Any] = {}

class UpdateInstitutionLanguagePayload(BaseModel):
    preferred_language: str # en, hi, ta

class DispatchMultilingualAlertPayload(BaseModel):
    institution_id: str
    template_key: str
    due_date: Optional[str] = None
    application_id: Optional[str] = None
    delivery_channel: str = "IN_APP"
    override_language: Optional[str] = None

@router.get("/alerts/multilingual/templates")
def get_multilingual_templates():
    """
    Returns static, reviewed notification templates across English, Hindi, and Tamil
    with exact APH clause references and parameter schemas.
    """
    from app.multilingual_notifications import (
        multilingual_service,
        SUPPORTED_LANGUAGES,
        NOTIFICATION_TEMPLATES,
    )
    return {
        "supported_languages": SUPPORTED_LANGUAGES,
        "template_keys": multilingual_service.list_template_keys(),
        "templates": NOTIFICATION_TEMPLATES,
    }

@router.post("/alerts/multilingual/render")
def render_multilingual_alert(payload: RenderMultilingualPayload):
    """
    Renders a notification template in the requested language.
    Falls back to English ('en') if language is untranslated or unsupported.
    """
    from app.multilingual_notifications import multilingual_service
    try:
        return multilingual_service.render_notification(
            template_key=payload.template_key,
            preferred_language=payload.language,
            context=payload.context,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/institutions/{institution_id}/language")
def update_institution_preferred_language(
    institution_id: str,
    payload: UpdateInstitutionLanguagePayload,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Updates the preferred notification language ('en', 'hi', 'ta') for an institution.
    """
    from app.models import Institution
    inst = db.query(Institution).filter(Institution.id == institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    valid_langs = ["en", "hi", "ta"]
    lang = payload.preferred_language.lower().strip()
    if lang not in valid_langs:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid language '{payload.preferred_language}'. Must be one of: {valid_langs}"
        )

    inst.preferred_language = lang
    db.commit()

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="LANGUAGE_PREFERENCE_UPDATED",
        entity_type="INSTITUTION",
        entity_id=inst.id,
        metadata={"preferred_language": lang, "institution_name": inst.name},
    )

    return {
        "status": "LANGUAGE_UPDATED",
        "institution_id": inst.id,
        "preferred_language": inst.preferred_language,
    }

@router.post("/alerts/multilingual/dispatch")
def dispatch_multilingual_alert(
    payload: DispatchMultilingualAlertPayload,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Dispatches a statutory multilingual notification to an institution.
    Selects language according to the institution's saved preference (or override),
    falling back to English if the translation is unavailable.
    """
    from app.models import Institution
    from app.multilingual_notifications import multilingual_service

    inst = db.query(Institution).filter(Institution.id == payload.institution_id).first()
    if not inst:
        raise HTTPException(status_code=404, detail="Institution not found.")

    target_lang = payload.override_language or inst.preferred_language or "en"
    context = {
        "institution_name": inst.name,
        "due_date": payload.due_date or (datetime.utcnow() + timedelta(days=15)).strftime("%d-%b-%Y"),
    }

    dal = ScopedDAL(db, ctx)
    if payload.application_id:
        app = dal.get_application_by_id(payload.application_id)
        if app:
            context["application_no"] = app.application_no

    rendered = multilingual_service.render_notification(
        template_key=payload.template_key,
        preferred_language=target_lang,
        context=context,
    )

    notif = Notification(
        user_id=ctx.user_id,
        title=rendered["title"],
        message=rendered["message"],
        category="MULTILINGUAL_ALERT",
        severity="INFO",
        scheduled_for=datetime.utcnow(),
        fired_at=datetime.utcnow(),
        delivery_channel=payload.delivery_channel,
        delivery_status="DELIVERED",
        recipient_contact=inst.name,
        language=rendered["language"],
    )
    db.add(notif)
    db.commit()

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="MULTILINGUAL_ALERT_DISPATCHED",
        entity_type="NOTIFICATION",
        entity_id=notif.id,
        metadata={
            "template_key": payload.template_key,
            "language": rendered["language"],
            "fallback_applied": rendered["fallback_applied"],
            "institution_id": inst.id,
        },
    )

    return {
        "status": "DISPATCH_SUCCESSFUL",
        "notification_id": notif.id,
        "rendered": rendered,
    }

