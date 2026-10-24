"""
Tests for Group D: Roles and Tracking Verification
13. Roles: Regional Director, Bureau Head ("assumed escalation levels"), Scrutiny Committee member, SAC/SHC member.
14. Notification centre (in-app + mock email/SMS/WhatsApp delivery logs).
15. Institution portal: stage timeline, My Items, status lookup by application ID + OTP.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import Application, Notification, Region, User
from app.auth import create_access_token, decode_token
from app.scoped_dal import ScopedDAL, RequestContext
from app.routers.intake_workflow import public_status_lookup, StatusLookupRequest
from app.routers.alerts_escalation import get_multi_channel_delivery_logs

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_roles_jwt_and_scoping(db):
    """
    Clause 13: Verify newly added roles:
    REGIONAL_DIRECTOR, BUREAU_HEAD, SCRUTINY_MEMBER, SAC_SHC_MEMBER
    """
    swro = db.query(Region).filter(Region.code == "SWRO").first()
    assert swro is not None

    # 1. Bureau Head (Assumed Escalation Level L3) -> Pan-India Read Scope
    bh_token = create_access_token({"sub": "usr-bh-test", "role": "BUREAU_HEAD"})
    bh_claims = decode_token(bh_token)
    assert bh_claims["role"] == "BUREAU_HEAD"
    bh_dal = ScopedDAL(db, RequestContext(user_id="usr-bh-test", role="BUREAU_HEAD"))
    bh_apps = bh_dal.get_applications()
    all_count = db.query(Application).count()
    assert len(bh_apps) == all_count, "Bureau Head must have Pan-India read scope"

    # 2. Regional Director (Assumed Escalation Level L2) -> Own Region Scoping
    rd_token = create_access_token({"sub": "usr-rd-test", "role": "REGIONAL_DIRECTOR", "region_id": swro.id})
    rd_claims = decode_token(rd_token)
    assert rd_claims["role"] == "REGIONAL_DIRECTOR"
    rd_dal = ScopedDAL(db, RequestContext(user_id="usr-rd-test", role="REGIONAL_DIRECTOR", region_id=swro.id))
    rd_apps = rd_dal.get_applications()
    assert len(rd_apps) > 0
    assert all(a.region_id == swro.id for a in rd_apps), "Regional Director must be scoped to own regional office"

    # 3. Scrutiny Member -> Scoped only to assigned cases
    sm_dal = ScopedDAL(db, RequestContext(user_id="usr-sm-unassigned", role="SCRUTINY_MEMBER"))
    assert len(sm_dal.get_applications()) == 0, "Unassigned Scrutiny Member cannot see unassigned cases"

    # 4. SAC/SHC Member -> Scoped only to assigned hearing cases
    sac_dal = ScopedDAL(db, RequestContext(user_id="usr-sac-unassigned", role="SAC_SHC_MEMBER"))
    assert len(sac_dal.get_applications()) == 0, "Unassigned SAC Member cannot see unassigned cases"

def test_notification_centre_multi_channel_delivery_logs(db):
    """
    Clause 14: Notification centre with in-app + mock email/SMS/WhatsApp delivery logs.
    """
    # Query multi-channel delivery logs
    logs_res = get_multi_channel_delivery_logs(db=db)
    assert "channel_counts" in logs_res
    assert "logs" in logs_res
    counts = logs_res["channel_counts"]

    # Verify all 4 required delivery channels are tracked in delivery center
    assert "IN_APP" in counts
    assert "EMAIL_MOCK" in counts
    assert "SMS_MOCK" in counts
    assert "WHATSAPP_MOCK" in counts
    assert counts["WHATSAPP_MOCK"] > 0, "Must have seeded WhatsApp delivery logs"
    assert counts["SMS_MOCK"] > 0, "Must have seeded SMS delivery logs"
    assert counts["EMAIL_MOCK"] > 0, "Must have seeded Email delivery logs"

    # Verify channel filter works
    wa_res = get_multi_channel_delivery_logs(channel="WHATSAPP_MOCK", db=db)
    assert all(l["delivery_channel"] == "WHATSAPP_MOCK" for l in wa_res["logs"])

def test_institution_portal_status_lookup_and_timeline(db):
    """
    Clause 15 & Requirement 5: Status lookup by application ID + OTP.
    Timeline is dynamically built from Table 2.3 route:
    - SAC shown ONLY for appeals
    - SHC shown ONLY when compliance verification applies
    - Neither shown universally for every application
    """
    app = db.query(Application).first()
    assert app is not None

    # Negative test: invalid OTP rejected with 401
    bad_req = StatusLookupRequest(application_no=app.application_no, otp="999999")
    with pytest.raises(Exception):
        public_status_lookup(payload=bad_req, db=db)

    # 1. Standard application without appeal: SAC and SHC must NOT be present
    app.current_stage = "SCRUTINY"
    db.commit()

    good_req = StatusLookupRequest(application_no=app.application_no, otp="123456")
    resp = public_status_lookup(payload=good_req, db=db)

    assert resp["application_no"] == app.application_no
    assert "timeline" in resp
    stages = [step["stage"] for step in resp["timeline"]]
    assert "PORTAL_SUBMISSION" in stages
    # Standard application does NOT show SAC or SHC
    assert "SAC_APPEAL" not in stages, "SAC must NOT be shown unless an appeal is filed"
    assert "SHC_VERIFICATION" not in stages, "SHC must NOT be shown unless compliance verification applies"

    # 2. Application under appeal: SAC stage MUST be included
    app.current_stage = "SAC_HEARING"
    db.commit()
    resp_appeal = public_status_lookup(payload=good_req, db=db)
    stages_appeal = [step["stage"] for step in resp_appeal["timeline"]]
    assert "SAC_APPEAL" in stages_appeal, "SAC must be shown when an appeal is active"
    assert "SHC_VERIFICATION" not in stages_appeal

    # 3. Application under compliance hearing: SHC stage MUST be included
    app.current_stage = "SHC_HEARING"
    db.commit()
    resp_shc = public_status_lookup(payload=good_req, db=db)
    stages_shc = [step["stage"] for step in resp_shc["timeline"]]
    assert "SHC_VERIFICATION" in stages_shc, "SHC must be shown when compliance hearing applies"
    assert "SAC_APPEAL" not in stages_shc

    # Reset stage
    app.current_stage = "SCRUTINY"
    db.commit()
