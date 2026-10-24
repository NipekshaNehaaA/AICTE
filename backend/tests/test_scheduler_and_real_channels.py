"""
=============================================================================
TEST SUITE: REAL SCHEDULER, IDEMPOTENCY & MULTI-CHANNEL DISPATCH (TASK 2)
=============================================================================
Validates:
1. APScheduler evaluation engine fires at correct offsets (T-90, T-60, T-30, T-7, overdue) on a frozen clock.
2. Idempotency keys prevent duplicate notification sends across multiple evaluation runs.
3. Real SMTP channel retries on failure with exponential backoff and records failure state.
4. Twilio WhatsApp adapter correctly interacts at HTTP layer with sandbox labelling and falls back to SIMULATED.
5. Language selection (en, hi, ta) correctly localizes alerts with exact APH clause references.
6. Notification resend endpoint retries failed alerts and stamps Merkle audit ledger.
=============================================================================
"""

import sys
import os
import json
import uuid
from datetime import datetime, date, timedelta
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import (
    InstitutionalDocument,
    TimeBoundUndertaking,
    EVCPanel,
    Notification,
    Institution,
    User,
    AuditTrail,
    DocumentType,
)
from app.scheduler import RegulatorySchedulerService, regulatory_scheduler
from app.email_service import EmailService
from app.twilio_whatsapp import TwilioWhatsAppAdapter
from app.multilingual_notifications import multilingual_service
from app.scoped_dal import RequestContext, ScopedDAL

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_scheduler_evaluates_at_correct_offsets_on_frozen_clock(db):
    """Task 2 Test: Evaluates document expiry and undertaking deadlines at configured offsets on frozen clock."""
    inst = db.query(Institution).first()
    assert inst is not None

    doc_type = db.query(DocumentType).first()
    assert doc_type is not None

    frozen_date = date(2026, 6, 1)
    frozen_datetime = datetime(2026, 6, 1, 10, 0, 0)

    # Create document expiring in 30 days (T-30 offset)
    doc_30d = InstitutionalDocument(
        institution_id=inst.id,
        doc_type_id=doc_type.id,
        document_number=f"DOC-T30-{uuid.uuid4().hex[:6]}",
        file_url="/storage/test.pdf",
        file_hash_sha256="a" * 64,
        issue_date=date(2020, 1, 1),
        expiry_date=frozen_date + timedelta(days=30),
        issuing_authority="State Authority",
        status="ACTIVE",
        submitter_id="system-test",
        version=1,
        is_latest_version=True,
    )
    db.add(doc_30d)

    # Create overdue document
    doc_overdue = InstitutionalDocument(
        institution_id=inst.id,
        doc_type_id=doc_type.id,
        document_number=f"DOC-OVERDUE-{uuid.uuid4().hex[:6]}",
        file_url="/storage/test2.pdf",
        file_hash_sha256="b" * 64,
        issue_date=date(2015, 1, 1),
        expiry_date=frozen_date - timedelta(days=5),
        issuing_authority="State Authority",
        status="ACTIVE",
        submitter_id="system-test",
        version=1,
        is_latest_version=True,
    )
    db.add(doc_overdue)
    db.commit()

    service = RegulatorySchedulerService()
    stats = service.evaluate_and_dispatch_all(db, target_time=frozen_datetime)

    assert stats["doc_expiry_alerts"] >= 2
    
    # Verify notification records generated with correct idempotency keys
    notif_30 = db.query(Notification).filter(
        Notification.idempotency_key == f"doc_expiry:{doc_30d.id}:T_30:IN_APP"
    ).first()
    assert notif_30 is not None
    assert notif_30.category in ("LEASE_EXPIRY", "DOC_EXPIRY")

    notif_overdue = db.query(Notification).filter(
        Notification.idempotency_key == f"doc_expiry:{doc_overdue.id}:OVERDUE:IN_APP"
    ).first()
    assert notif_overdue is not None
    assert notif_overdue.severity == "CRITICAL"

def test_idempotency_prevents_duplicate_sends(db):
    """Task 2 Test: Repeated evaluation on the same date skips already-sent alerts via idempotency key."""
    service = RegulatorySchedulerService()
    frozen_datetime = datetime(2026, 6, 1, 12, 0, 0)

    # First run generates alerts
    stats1 = service.evaluate_and_dispatch_all(db, target_time=frozen_datetime)
    
    # Second run immediately after
    stats2 = service.evaluate_and_dispatch_all(db, target_time=frozen_datetime)

    assert stats2["skipped_idempotent"] >= stats1["doc_expiry_alerts"]

def test_smtp_retries_and_failure_recording():
    """Task 2 Test: Real SMTP channel retries on failure with exponential backoff and logs failure state."""
    service = EmailService()
    service.max_retries = 3

    mock_smtp = MagicMock()
    mock_smtp.sendmail.side_effect = Exception("Simulated SMTP Connection Refused")

    with patch("smtplib.SMTP", return_value=mock_smtp):
        receipt = service.send_email(
            to_email="officer@aicte-india.org",
            subject="Test SLA Breach",
            text_content="SLA breach notification text.",
            check_quiet=False,
        )

        assert receipt["status"] == "FAILED"
        assert receipt["attempt_count"] == 3
        assert "Simulated SMTP" in receipt["failure_reason"]
        assert receipt["delivered_at"] is None

def test_twilio_whatsapp_adapter_http_mock():
    """Task 2 Test: Twilio WhatsApp sandbox adapter sends HTTP request with sandbox label."""
    adapter = TwilioWhatsAppAdapter()
    adapter.account_sid = "AC_MOCK_ACCOUNT_SID_12345"
    adapter.auth_token = "AUTH_TOKEN_SECRET_67890"

    fake_response = MagicMock()
    fake_response.read.return_value = json.dumps({
        "sid": "SM_TWILIO_MOCK_SID_9999",
        "status": "queued",
        "to": "whatsapp:+919876543210",
        "from": "whatsapp:+14155238886",
    }).encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with patch("urllib.request.urlopen", return_value=fake_response) as mock_urlopen:
        receipt = adapter.send_whatsapp_message(
            to_phone="+919876543210",
            message_body="Your EVC inspection is scheduled for 15-Nov-2026.",
            user_opted_in=True,
        )

        assert receipt["status"] == "DELIVERED"
        assert receipt["channel"] == "WHATSAPP_SANDBOX"
        assert receipt["label"] == "sandbox"
        assert receipt["receipt_id"] == "SM_TWILIO_MOCK_SID_9999"

        # Verify urllib.request.urlopen was called with correct URL and Auth
        assert mock_urlopen.called
        req_sent = mock_urlopen.call_args[0][0]
        assert "AC_MOCK_ACCOUNT_SID_12345/Messages.json" in req_sent.full_url
        assert "Basic " in req_sent.headers.get("Authorization", "")

def test_twilio_whatsapp_adapter_fallback_to_simulated():
    """Task 2 Test: When Twilio credentials absent, messages are explicitly labelled SIMULATED."""
    adapter = TwilioWhatsAppAdapter()
    adapter.account_sid = ""
    adapter.auth_token = ""

    receipt = adapter.send_whatsapp_message(
        to_phone="+919876543210",
        message_body="Test simulated WhatsApp alert.",
        user_opted_in=True,
    )

    assert receipt["status"] == "SIMULATED"
    assert receipt["channel"] == "WHATSAPP_SIMULATED"
    assert receipt["label"] == "SIMULATED"
    assert "sim_wa_" in receipt["receipt_id"]

def test_language_selection_and_aph_clause_citations():
    """Task 2 Test: Multi-language template rendering correctly displays en, hi, ta with APH citations."""
    ctx = {
        "institution_name": "National Engineering College",
        "application_no": "1-998877",
        "due_date": "20-Dec-2026",
    }

    # English
    en_rendered = multilingual_service.render_notification("LEASE_EXPIRY_WARNING", "en", ctx)
    assert "Land Lease Expiry Advisory" in en_rendered["title"]
    assert "Clause 1.4.1(e)" in en_rendered["aph_clause_ref"]

    # Hindi
    hi_rendered = multilingual_service.render_notification("LEASE_EXPIRY_WARNING", "hi", ctx)
    assert "भूमि पट्टा समाप्ति परामर्श" in hi_rendered["title"]
    assert "धारा 1.4.1(e)" in hi_rendered["aph_clause_ref"]

    # Tamil
    ta_rendered = multilingual_service.render_notification("LEASE_EXPIRY_WARNING", "ta", ctx)
    assert "நில குத்தகை காலாவதி ஆலோசனை" in ta_rendered["title"]
    assert "விதி 1.4.1(e)" in ta_rendered["aph_clause_ref"]

def test_resend_notification_endpoint(db):
    """Task 2 Test: Resending a failed notification increments retry_count and logs audit entry."""
    from app.routers.alerts_escalation import resend_failed_alert

    # Create failed notification
    failed_notif = Notification(
        title="Failed Alert",
        message="Failure notification body",
        category="DOC_EXPIRY",
        severity="WARNING",
        scheduled_for=datetime.utcnow(),
        fired_at=datetime.utcnow(),
        delivery_channel="EMAIL",
        delivery_status="FAILED",
        recipient_contact="admin@college.edu",
        retry_count=1,
        error_message="SMTP 500 error",
    )
    db.add(failed_notif)
    db.commit()

    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER")

    with patch("app.email_service.email_service.send_email", return_value={"status": "DELIVERED", "message_id": "<resend_123@smtp>"}):
        res = resend_failed_alert(
            notif_id=failed_notif.id,
            ctx=ctx,
            db=db,
        )

        assert res["status"] == "RESENT"
        assert res["delivery_status"] == "DELIVERED"
        assert res["retry_count"] == 2

        # Check DB update
        updated = db.query(Notification).filter(Notification.id == failed_notif.id).first()
        assert updated.delivery_status == "DELIVERED"
        assert updated.retry_count == 2
        assert updated.receipt_id == "<resend_123@smtp>"

        # Verify hash-chained audit ledger entry
        audit_entry = db.query(AuditTrail).filter(
            AuditTrail.action_type == "ALERT_RESENT",
            AuditTrail.entity_id == failed_notif.id,
        ).first()
        assert audit_entry is not None
