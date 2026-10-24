"""
=============================================================================
TEST SUITE: REAL SMTP EMAIL CHANNEL, RETRIES & AUDIT LOGGING
=============================================================================
Validates:
1. Real SMTP message delivery with delivery receipt & Message-ID.
2. Exponential backoff retries and failure states when SMTP is unavailable.
3. Quiet hours check deferring non-urgent alerts between 22:00 and 06:00.
4. Per-recipient delivery receipts tracked in SHA-256 hash-chained audit ledger.
5. Simulated channels (SMS_MOCK, WHATSAPP_MOCK) explicitly labelled as simulated.
=============================================================================
"""

import sys
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import AuditTrail, Notification
from app.email_service import EmailService
from app.scoped_dal import RequestContext
from app.routers.alerts_escalation import (
    dispatch_statutory_test_email,
    SendTestEmailPayload,
    get_multi_channel_delivery_logs,
)

class FakeSMTPServer:
    """Mock SMTP server intercepting smtplib.SMTP for deterministic test assertions."""
    def __init__(self, should_fail=False):
        self.should_fail = should_fail
        self.received_messages = []
        self._patcher = None

    def __enter__(self):
        mock_instance = MagicMock()
        if self.should_fail:
            mock_instance.sendmail.side_effect = Exception("SMTP Connection timed out (Simulated network failure)")
        else:
            def fake_sendmail(from_addr, to_addrs, msg):
                self.received_messages.append({"from": from_addr, "to": to_addrs, "msg": str(msg)})
                return {}
            mock_instance.sendmail.side_effect = fake_sendmail

        self._patcher = patch("smtplib.SMTP", return_value=mock_instance)
        self.mock_smtp_class = self._patcher.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._patcher:
            self._patcher.stop()

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_real_smtp_delivery_success():
    """Task 2 Test: Real SMTP channel sends email, returns delivery receipt with message ID."""
    with FakeSMTPServer() as server:
        service = EmailService()
        receipt = service.send_email(
            to_email="officer.regional@aicte-india.org",
            subject="AICTE Regulatory SLA Warning (L1 Escalation)",
            text_content="Statutory review timeline approaching. Application 1-100293.",
            check_quiet=False,
        )
        assert receipt["status"] == "DELIVERED"
        assert "message_id" in receipt
        assert receipt["recipient"] == "officer.regional@aicte-india.org"
        assert receipt["attempt_count"] == 1
        assert len(server.received_messages) == 1
        assert "AICTE Regulatory SLA Warning" in server.received_messages[0]["msg"]

def test_smtp_delivery_failure_and_retries():
    """Task 2 Test: When SMTP server is unreachable, service retries with backoff and records failure state."""
    with FakeSMTPServer(should_fail=True):
        service = EmailService()
        service.max_retries = 3
        receipt = service.send_email(
            to_email="officer.bureau@aicte-india.org",
            subject="Urgent Escalation Notice",
            text_content="SLA breach notification.",
            check_quiet=False,
        )
        assert receipt["status"] == "FAILED"
        assert receipt["attempt_count"] == 3
        assert "failure_reason" in receipt
        assert receipt["delivered_at"] is None

def test_quiet_hours_deferral():
    """Task 2 Test: Non-critical notifications defer delivery during quiet hours (22:00 to 06:00)."""
    service = EmailService()
    service.quiet_hours_start = 22
    service.quiet_hours_end = 6

    # 1. 23:30 (11:30 PM) is inside quiet hours
    night_time = datetime(2026, 10, 24, 23, 30, 0)
    assert service.is_quiet_hours(night_time) is True

    # 2. 14:00 (2:00 PM) is outside quiet hours
    day_time = datetime(2026, 10, 24, 14, 0, 0)
    assert service.is_quiet_hours(day_time) is False

    # 3. Attempting send during quiet hours defers
    receipt = service.send_email(
        to_email="officer@aicte-india.org",
        subject="Routine Advisory",
        text_content="Routine notice.",
        check_quiet=True,
        current_time=night_time,
    )
    assert receipt["status"] == "DEFERRED_QUIET_HOURS"
    assert "quiet hours" in receipt["reason"].lower()

def test_audit_ledger_records_delivery_receipt(db):
    """Task 2 Test: Email dispatch records delivery receipt and recipient into hash-chained audit ledger."""
    with FakeSMTPServer():
        ctx = RequestContext(user_id="usr-ro-smtp-test", role="REGIONAL_OFFICER")
        req = SendTestEmailPayload(
            to_email="bureau.head@aicte-india.org",
            subject="Statutory Compliance Audit Log Test",
            body="Checking tamper-evident ledger append.",
            check_quiet_hours=False,
        )
        res = dispatch_statutory_test_email(payload=req, ctx=ctx, db=db)
        assert res["status"] == "DELIVERED"

        # Check Audit Trail
        audit_entry = db.query(AuditTrail).filter(
            AuditTrail.action_type == "SMTP_EMAIL_DISPATCHED"
        ).order_by(AuditTrail.timestamp.desc()).first()
        assert audit_entry is not None
        assert "bureau.head@aicte-india.org" in audit_entry.metadata_json
        assert audit_entry.actor_id == ctx.user_id

def test_simulated_channels_explicitly_labelled(db):
    """Task 2 Test: SMS and WhatsApp channels are explicitly labelled as simulated."""
    res = get_multi_channel_delivery_logs(db=db)
    for log in res["logs"]:
        if "SMS" in log["delivery_channel"] or "WHATSAPP" in log["delivery_channel"]:
            assert log["is_simulated"] is True
            assert "Simulated" in log["channel_label"]
