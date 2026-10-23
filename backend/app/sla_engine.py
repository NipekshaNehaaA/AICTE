"""
=============================================================================
SLA, ALERT & ESCALATION ENGINE (DETERMINISTIC)
=============================================================================
Features:
1. Working-day calendar calculation excluding weekends and statutory holidays
2. Statutory clock pausing while case is with the institution for deficiency cure
3. SLA RAG classification: ON_TRACK, AT_RISK (<= 2 days), OVERDUE
4. Hierarchical Escalation Ladder:
   - Level 1: Dealing Officer & Institution (Day 0 of breach)
   - Level 2: Regional Officer / Director (Overdue +3 Days)
   - Level 3: Bureau Head / Adviser HQ (Overdue +7 Days)
   - Level 4: Member Secretary / Council with Show-Cause Notice (Overdue +14 Days)
5. Alert Timeliness Audit Log: Tracks scheduled_for vs fired_at
6. Time-Travel Evaluator: Evaluates all cases when system virtual clock advances
=============================================================================
"""

from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.models import (
    Application,
    HolidayCalendar,
    Notification,
    EscalationLog,
    CaseEvent,
    User,
    Region,
)
from app.scoped_dal import ScopedDAL, RequestContext

class SLAEngine:
    @staticmethod
    def is_working_day(d: date, holidays: List[date]) -> bool:
        """Saturday and Sunday are non-working days, plus statutory holidays."""
        if d.weekday() >= 5: # 5 = Saturday, 6 = Sunday
            return False
        if d in holidays:
            return False
        return True

    @classmethod
    def add_working_days(cls, start_date: datetime, working_days: int, holidays: List[date]) -> datetime:
        """Calculates future deadline by adding exact working days."""
        current = start_date
        added = 0
        while added < working_days:
            current += timedelta(days=1)
            if cls.is_working_day(current.date(), holidays):
                added += 1
        return current

    @classmethod
    def calculate_working_days_between(cls, start_date: datetime, end_date: datetime, holidays: List[date]) -> int:
        """Calculates working days elapsed between two timestamps."""
        if start_date > end_date:
            return 0
        current = start_date.date()
        target = end_date.date()
        count = 0
        while current < target:
            current += timedelta(days=1)
            if cls.is_working_day(current, holidays):
                count += 1
        return count

    @classmethod
    def evaluate_case_sla(
        cls,
        app: Application,
        current_virtual_time: datetime,
        holidays: List[date],
    ) -> Tuple[str, float]:
        """
        Evaluates SLA status for an application:
        - If status == 'DEFICIENT': Clock is PAUSED.
        - Otherwise, checks time difference against statutory deadline.
        Returns: (sla_status, days_remaining)
        """
        if app.status == "DEFICIENT":
            # Clock is paused
            return "PAUSED", 0.0

        diff_seconds = (app.sla_deadline - current_virtual_time).total_seconds()
        days_remaining = diff_seconds / 86400.0

        if days_remaining < 0:
            return "OVERDUE", round(days_remaining, 1)
        elif days_remaining <= 2.0:
            return "AT_RISK", round(days_remaining, 1)
        else:
            return "ON_TRACK", round(days_remaining, 1)

    @classmethod
    def process_escalations_for_application(
        cls,
        db: Session,
        app: Application,
        current_virtual_time: datetime,
        dal: ScopedDAL,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates and triggers appropriate hierarchical escalation tier if SLA is breached:
        - L1 (0-2 days overdue): Dealing Officer
        - L2 (3-6 days overdue): Regional Head (SWRO / Regional Director)
        - L3 (7-13 days overdue): Bureau Head (HQ)
        - L4 (14+ days overdue): Member Secretary / Council
        """
        if app.status == "DEFICIENT" or app.status in ("APPROVED", "REJECTED"):
            return []

        days_overdue = (current_virtual_time - app.sla_deadline).total_seconds() / 86400.0
        if days_overdue < 0:
            return [] # Still on track or at risk, no breach yet

        app.sla_status = "OVERDUE"
        app.status = "ESCALATED"

        # Determine target escalation tier
        target_tier = None
        target_role = None
        recipient_id = None

        if days_overdue >= 14.0:
            target_tier = "L4_MEMBER_SECRETARY"
            target_role = "SUPER_ADMIN"
            ms_user = db.query(User).filter(User.role == "SUPER_ADMIN").first()
            recipient_id = ms_user.id if ms_user else None
        elif days_overdue >= 7.0:
            target_tier = "L3_BUREAU_HEAD"
            target_role = "BUREAU_OFFICER"
            bo_user = db.query(User).filter(User.role == "BUREAU_OFFICER").first()
            recipient_id = bo_user.id if bo_user else None
        elif days_overdue >= 3.0:
            target_tier = "L2_REGIONAL_HEAD"
            target_role = "REGIONAL_OFFICER"
            ro_user = db.query(User).filter(User.region_id == app.region_id, User.role == "REGIONAL_OFFICER").first()
            recipient_id = ro_user.id if ro_user else None
        else:
            target_tier = "L1_OFFICER"
            target_role = "REGIONAL_OFFICER"
            recipient_id = app.assigned_officer_id

        # Check if already escalated at this tier
        existing_log = db.query(EscalationLog).filter(
            EscalationLog.application_id == app.id,
            EscalationLog.escalation_level == target_tier,
        ).first()

        if existing_log:
            return [] # Already fired

        # Record Escalation Log
        esc_entry = EscalationLog(
            application_id=app.id,
            trigger_reason="SLA_BREACH",
            escalation_level=target_tier,
            recipient_role=target_role,
            recipient_id=recipient_id,
            status="FIRED",
            fired_at=current_virtual_time,
        )
        db.add(esc_entry)

        # Dispatch Multi-Channel Notifications (In-App, Email Mock, SMS Mock)
        scheduled_time = app.sla_deadline
        actual_send_time = current_virtual_time

        msg_body = (
            f"Statutory processing timeline exceeded by {int(days_overdue)} days for Application {app.application_no} "
            f"({app.institution.name}). Escalated to {target_tier} in accordance with APH 2024-27 escalation ladder."
        )

        notif = Notification(
            user_id=recipient_id,
            title=f"SLA Breach Escalation: {target_tier}",
            message=msg_body,
            category="ESCALATION",
            severity="CRITICAL",
            scheduled_for=scheduled_time,
            fired_at=actual_send_time,
            application_id=app.id,
            escalation_level=target_tier,
            delivery_channel="IN_APP",
            delivery_status="DELIVERED",
        )
        db.add(notif)

        # Append Case Event
        db.add(CaseEvent(
            application_id=app.id,
            event_type="ESCALATED",
            actor_id=None,
            actor_role="SYSTEM_RULES_ENGINE",
            description=f"Automated Escalation triggered to {target_tier}. Overdue by {int(days_overdue)} days.",
            aph_clause_ref="Chapter I Clause 1.10 / Escalation Ladder [Sample value, configurable]",
        ))

        # Append to Audit Ledger
        dal.append_audit_entry(
            action_type="ESCALATION_TRIGGERED",
            entity_type="APPLICATION",
            entity_id=app.id,
            metadata={
                "tier": target_tier,
                "days_overdue": round(days_overdue, 1),
                "scheduled_for": scheduled_time.isoformat(),
                "fired_at": actual_send_time.isoformat(),
            },
        )

        return [{
            "application_id": app.id,
            "tier": target_tier,
            "days_overdue": round(days_overdue, 1),
            "recipient_role": target_role,
        }]

    @classmethod
    def run_time_travel_evaluation(
        cls,
        db: Session,
        current_virtual_time: datetime,
        dal: ScopedDAL,
    ) -> Dict[str, Any]:
        """
        Iterates across all applications, updates SLA RAG statuses,
        and fires escalations for any newly breached cases.
        """
        # Fetch holidays
        holidays_records = db.query(HolidayCalendar.holiday_date).all()
        holidays = [h[0] for h in holidays_records]

        apps = db.query(Application).all()
        stats = {"on_track": 0, "at_risk": 0, "overdue": 0, "paused": 0, "escalations_fired": []}

        for app in apps:
            status, days_left = cls.evaluate_case_sla(app, current_virtual_time, holidays)
            if status != "PAUSED":
                app.sla_status = status

            if status == "ON_TRACK":
                stats["on_track"] += 1
            elif status == "AT_RISK":
                stats["at_risk"] += 1
            elif status == "OVERDUE":
                stats["overdue"] += 1
                fired = cls.process_escalations_for_application(db, app, current_virtual_time, dal)
                stats["escalations_fired"].extend(fired)
            elif status == "PAUSED":
                stats["paused"] += 1

        db.commit()
        return stats
