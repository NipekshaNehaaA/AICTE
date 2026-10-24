"""
Unit and integration tests for Multilingual Institution Alerts (EN / HI / TA).
Verifies:
1. Static, reviewed templates in English, Hindi, and Tamil with exact APH clause references and due dates.
2. Parameter rendering across all three languages.
3. Fallback to English ('en') when an untranslated or unsupported language is requested.
4. Institution preference update (en, hi, ta) and audit ledger recording.
5. Dispatching a multilingual alert uses the institution's saved language preference.
"""

from datetime import datetime, timedelta, date
import pytest
from app.database import SessionLocal
from app.models import Institution, Application, Notification, AuditTrail
from app.scoped_dal import RequestContext
from app.multilingual_notifications import multilingual_service, SUPPORTED_LANGUAGES, NOTIFICATION_TEMPLATES
from app.routers.alerts_escalation import (
    render_multilingual_alert,
    update_institution_preferred_language,
    dispatch_multilingual_alert,
    RenderMultilingualPayload,
    UpdateInstitutionLanguagePayload,
    DispatchMultilingualAlertPayload,
)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_template_catalog_has_all_three_languages():
    """Verify templates exist in en, hi, ta with exact statutory clause citations."""
    templates = NOTIFICATION_TEMPLATES
    required_keys = ["DEFICIENCY_CURE_NOTICE", "LEASE_EXPIRY_WARNING", "EVC_SCHEDULE_NOTIFICATION", "SLA_BREACH_ALERT"]
    
    for key in required_keys:
        assert key in templates
        for lang in ["en", "hi", "ta"]:
            assert lang in templates[key]
            entry = templates[key][lang]
            assert "title" in entry
            assert "message" in entry
            assert "aph_clause_ref" in entry
            assert len(entry["aph_clause_ref"]) > 0

def test_render_english_hindi_tamil_deficiency_notice():
    """Verify parameter interpolation and exact clause citations in en, hi, ta."""
    ctx = {
        "application_no": "APP-2026-ENG-999",
        "institution_name": "Apex Engineering Institute",
        "due_date": "15-Nov-2026",
    }

    # English
    en_res = multilingual_service.render_notification("DEFICIENCY_CURE_NOTICE", "en", ctx)
    assert en_res["language"] == "en"
    assert "APP-2026-ENG-999" in en_res["title"]
    assert "15-Nov-2026" in en_res["message"]
    assert "Chapter I Clause 1.8(f)" in en_res["aph_clause_ref"]
    assert en_res["fallback_applied"] is False

    # Hindi
    hi_res = multilingual_service.render_notification("DEFICIENCY_CURE_NOTICE", "hi", ctx)
    assert hi_res["language"] == "hi"
    assert "कमी सुधार सूचना" in hi_res["title"]
    assert "15-Nov-2026" in hi_res["message"]
    assert "धारा 1.8(f)" in hi_res["aph_clause_ref"]
    assert hi_res["fallback_applied"] is False

    # Tamil
    ta_res = multilingual_service.render_notification("DEFICIENCY_CURE_NOTICE", "ta", ctx)
    assert ta_res["language"] == "ta"
    assert "குறைபாடு திருத்த அறிவிப்பு" in ta_res["title"]
    assert "15-Nov-2026" in ta_res["message"]
    assert "விதி 1.8(f)" in ta_res["aph_clause_ref"]
    assert ta_res["fallback_applied"] is False

def test_fallback_to_english_on_unsupported_language():
    """Requesting an unsupported language (e.g. French 'fr') falls back to English with fallback_applied=True."""
    ctx = {"institution_name": "Horizon College", "due_date": "30-Nov-2026"}
    res = multilingual_service.render_notification("LEASE_EXPIRY_WARNING", "fr", ctx)

    assert res["language"] == "en"
    assert res["fallback_applied"] is True
    assert "fallback" in res["fallback_reason"].lower()
    assert "Land Lease Expiry Advisory" in res["title"]

def test_update_institution_language_preference(db):
    """Updating institution preferred language saves to DB and logs audit ledger."""
    inst = db.query(Institution).first()
    assert inst is not None

    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=inst.region_id)
    res = update_institution_preferred_language(
        institution_id=inst.id,
        payload=UpdateInstitutionLanguagePayload(preferred_language="ta"),
        ctx=ctx,
        db=db,
    )
    assert res["status"] == "LANGUAGE_UPDATED"
    assert res["preferred_language"] == "ta"

    db.refresh(inst)
    assert inst.preferred_language == "ta"

    # Verify audit trail
    latest_audit = db.query(AuditTrail).filter(
        AuditTrail.action_type == "LANGUAGE_PREFERENCE_UPDATED",
        AuditTrail.entity_id == inst.id
    ).first()
    assert latest_audit is not None

def test_dispatch_multilingual_alert_uses_institution_preference(db):
    """Dispatching alert respects institution's saved language preference."""
    inst = db.query(Institution).first()
    assert inst is not None
    inst.preferred_language = "hi"
    db.commit()

    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=inst.region_id)
    res = dispatch_multilingual_alert(
        payload=DispatchMultilingualAlertPayload(
            institution_id=inst.id,
            template_key="LEASE_EXPIRY_WARNING",
            due_date="20-Dec-2026",
        ),
        ctx=ctx,
        db=db,
    )
    assert res["status"] == "DISPATCH_SUCCESSFUL"
    assert res["rendered"]["language"] == "hi"
    assert "भूमि पट्टा समाप्ति परामर्श" in res["rendered"]["title"]

    # Verify saved notification
    notif = db.query(Notification).filter(Notification.id == res["notification_id"]).first()
    assert notif is not None
    assert notif.language == "hi"
    assert "भूमि पट्टा समाप्ति परामर्श" in notif.title
