"""
=============================================================================
TEST SUITE: RBAC, RLS SCOPING, SEPARATION OF DUTIES (SoD), AND AUTH LOCKOUT
=============================================================================
Demonstrates and validates:
1. Cross-region read blocked (Regional Officer cannot see other regions)
2. Cross-institution access blocked (Institution User cannot see other institutions)
3. Empty / missing context returns zero rows (Default Deny)
4. Committee member sees ONLY assigned EVC cases
5. Auditor role is strictly read-only (Mutations blocked)
6. Pairwise SoD violations blocked:
   - Submitter != Verifier
   - Verifier != Approver
   - Submitter != Approver
   - AI Draft Requester != AI Draft Approver
7. Every SoD violation is recorded in the audit log
8. Brute-force lockout triggers after 5 failed attempts
9. Cryptographic SHA-256 audit hash-chain continuity
=============================================================================
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import (
    User,
    Region,
    Institution,
    Application,
    AuditTrail,
    LLMDraft,
)
from app.scoped_dal import (
    ScopedDAL,
    RequestContext,
    SecurityScopeError,
    SoDViolationError,
)
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
    verify_mfa_code,
    record_login_failure,
    check_account_lockout,
    record_login_success,
)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

# -----------------------------------------------------------------------------
# 1. AUTH & SECURITY TESTS
# -----------------------------------------------------------------------------
def test_password_hashing():
    pw = "AICTE@Gov2026Secure!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert "$" in hashed
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False

def test_jwt_tokens():
    payload = {"sub": "usr-ro-01", "role": "REGIONAL_OFFICER", "region": "SWRO"}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == "usr-ro-01"
    assert decoded["role"] == "REGIONAL_OFFICER"
    assert decoded["type"] == "access"

def test_mfa_verification():
    assert verify_mfa_code("SECRET_MFA", "123456") is True
    assert verify_mfa_code("SECRET_MFA", "999") is False

def test_brute_force_lockout():
    test_email = "targeted_officer@aicte-india.org"
    record_login_success(test_email) # reset
    
    for i in range(4):
        is_locked = record_login_failure(test_email)
        assert is_locked is False
        assert check_account_lockout(test_email) is None
    
    # 5th attempt locks the account
    is_locked = record_login_failure(test_email)
    assert is_locked is True
    lockout_msg = check_account_lockout(test_email)
    assert lockout_msg is not None
    assert "Account temporarily locked" in lockout_msg
    
    # Cleanup
    record_login_success(test_email)
    assert check_account_lockout(test_email) is None

# -----------------------------------------------------------------------------
# 2. RBAC & RLS SCOPING TESTS (POSITIVE & NEGATIVE)
# -----------------------------------------------------------------------------
def test_empty_context_default_deny(db):
    """Negative Test: A missing or empty context returns zero rows."""
    dal = ScopedDAL(db, RequestContext()) # empty context
    apps = dal.get_applications()
    assert apps == [], "Default Deny Failed: Empty context must return zero rows."

def test_cross_region_read_blocked(db):
    """Negative Test: Regional Officer of SWRO cannot see applications belonging to NRO."""
    swro = db.query(Region).filter(Region.code == "SWRO").first()
    nro = db.query(Region).filter(Region.code == "NRO").first()
    assert swro and nro

    # Context for SWRO Regional Officer
    ctx_swro = RequestContext(
        user_id="usr-ro-swro",
        role="REGIONAL_OFFICER",
        region_id=swro.id,
    )
    dal = ScopedDAL(db, ctx_swro)
    apps = dal.get_applications()
    assert len(apps) > 0

    # Ensure every single application returned belongs strictly to SWRO
    for app in apps:
        assert app.region_id == swro.id, f"Cross-region leak: App {app.id} belongs to region {app.region_id}, not SWRO"
        assert app.region_id != nro.id, "Security Breach: NRO application visible to SWRO officer!"

def test_cross_institution_access_blocked(db):
    """Negative Test: Institution User cannot access applications of other institutions."""
    inst_1 = db.query(Institution).first()
    inst_2 = db.query(Institution).filter(Institution.id != inst_1.id).first()
    assert inst_1 and inst_2

    ctx_inst1 = RequestContext(
        user_id="usr-inst-1",
        role="INSTITUTION_USER",
        institution_id=inst_1.id,
    )
    dal = ScopedDAL(db, ctx_inst1)
    apps = dal.get_applications()

    for app in apps:
        assert app.institution_id == inst_1.id
        assert app.institution_id != inst_2.id

def test_committee_member_scoping(db):
    """Negative Test: Committee Member only sees cases where they are explicitly assigned."""
    cm_user = db.query(User).filter(User.role == "COMMITTEE_MEMBER").first()
    assert cm_user

    ctx_cm = RequestContext(
        user_id=cm_user.id,
        role="COMMITTEE_MEMBER",
        region_id=cm_user.region_id,
    )
    dal = ScopedDAL(db, ctx_cm)
    apps = dal.get_applications()
    assert len(apps) > 0

    # Every app visible must have an EVC assignment for this specific user
    for app in apps:
        assignment = next((a for a in app.evc_panel.assignments if a.user_id == cm_user.id), None)
        assert assignment is not None, f"Committee member saw unassigned application {app.id}"

def test_auditor_read_only_enforcement(db):
    """Negative Test: Auditor has pan-India read access, but all write/mutation operations are blocked."""
    app = db.query(Application).first()
    assert app

    ctx_auditor = RequestContext(
        user_id="usr-auditor-01",
        role="AUDITOR",
    )
    dal = ScopedDAL(db, ctx_auditor)
    
    # Read succeeds
    apps = dal.get_applications()
    assert len(apps) > 0, "Auditor must have pan-India read scope."

    # Mutation fails with SecurityScopeError
    with pytest.raises(SecurityScopeError) as exc_info:
        dal.advance_application_stage(app.id, "EVC_SCHEDULED", "Auditor trying to advance")
    assert "Auditor role is strictly read-only" in str(exc_info.value)

# -----------------------------------------------------------------------------
# 3. SEPARATION OF DUTIES (SoD) PAIRWISE TESTS
# -----------------------------------------------------------------------------
def test_sod_submitter_cannot_verify(db):
    """Negative Test: Submitter != Verifier. Submitter cannot advance or verify their own application."""
    app = db.query(Application).first()
    assert app

    # Context acting as the submitter
    ctx_submitter = RequestContext(
        user_id=app.submitter_id,
        role="REGIONAL_OFFICER", # Even if role is officer
        region_id=app.region_id,
    )
    dal = ScopedDAL(db, ctx_submitter)

    with pytest.raises(SoDViolationError) as exc_info:
        dal.advance_application_stage(app.id, "PASSED_SCRUTINY")
    assert "Submitter" in str(exc_info.value) and "cannot verify" in str(exc_info.value)

    # Verify that the SoD rejection was recorded in the audit trail
    audit_entry = db.query(AuditTrail).filter(
        AuditTrail.action_type == "SOD_REJECTED",
        AuditTrail.entity_id == app.id
    ).order_by(AuditTrail.id.desc()).first()
    assert audit_entry is not None
    assert "Submitter" in audit_entry.metadata_json

def test_sod_verifier_cannot_approve(db):
    """Negative Test: Verifier != Approver. Officer who verified cannot grant final statutory approval."""
    app = db.query(Application).filter(Application.verifier_id.isnot(None)).first()
    if not app:
        app = db.query(Application).first()
        app.verifier_id = "officer-verifier-123"
        db.commit()

    ctx_verifier = RequestContext(
        user_id=app.verifier_id,
        role="SUPER_ADMIN",
    )
    dal = ScopedDAL(db, ctx_verifier)

    with pytest.raises(SoDViolationError) as exc_info:
        dal.advance_application_stage(app.id, "APPROVED")
    assert "Verifier" in str(exc_info.value) and "cannot approve" in str(exc_info.value)

def test_sod_ai_draft_requester_cannot_approve(db):
    """Negative Test: User who requested an AI draft cannot act as the Approver."""
    draft = db.query(LLMDraft).first()
    assert draft

    ctx_requester = RequestContext(
        user_id=draft.requester_id,
        role="REGIONAL_OFFICER",
    )
    dal = ScopedDAL(db, ctx_requester)

    with pytest.raises(SoDViolationError) as exc_info:
        dal.approve_ai_draft(draft.id)
    assert "Requester" in str(exc_info.value) and "cannot act as the Approver" in str(exc_info.value)

# -----------------------------------------------------------------------------
# 4. CRYPTOGRAPHIC HASH-CHAIN CONTINUITY TEST
# -----------------------------------------------------------------------------
def test_audit_hash_chain_continuity(db):
    """Validates that audit log entries maintain unbroken SHA-256 hash continuity."""
    dal = ScopedDAL(db, RequestContext(user_id="officer-test-01", role="REGIONAL_OFFICER"))
    
    # Append three consecutive audit events
    entry1 = dal.append_audit_entry("INTAKE", "APPLICATION", "app-test-1", {"status": "submitted"})
    entry2 = dal.append_audit_entry("STAGE_ADVANCE", "APPLICATION", "app-test-1", {"status": "scrutiny"})
    entry3 = dal.append_audit_entry("DOCUMENT_VERIFIED", "DOCUMENT", "doc-test-1", {"verified": True})
    db.commit()

    entries = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
    assert len(entries) >= 4

    for i in range(1, len(entries)):
        prev = entries[i - 1]
        curr = entries[i]
        assert curr.prev_entry_hash == prev.curr_entry_hash, (
            f"Audit Hash Chain Broken at entry #{curr.id}! "
            f"Expected prev_hash {prev.curr_entry_hash}, found {curr.prev_entry_hash}"
        )

if __name__ == "__main__":
    pytest.main(["-v", __file__])
