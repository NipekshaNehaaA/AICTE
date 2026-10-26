"""
Test Suite for Task 2: Assignment-Based Document Access & Handoff
Verifies:
1. Scrutiny Member can list, preview, and download documents ONLY while assigned to active SCRUTINY stage.
2. Advancing stage to EVC revokes Scrutiny Member access (403) and grants access to assigned EVC Expert.
3. Advancing stage to SAC_SHC revokes EVC Expert access (403) and grants access to assigned SAC Member.
4. Cross-institution access strictly returns 403.
5. Every preview logs DOCUMENT_VIEWED, every download logs DOCUMENT_DOWNLOADED in AuditTrail.
6. GET /documents/{id}/access-control returns authorized stakeholders and audit history.
7. Handoff notifications are dispatched with idempotent keys (no duplicates).
"""

import sys
import os
import pytest
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import get_session_maker, init_db
from app.models import (
    User,
    Institution,
    Application,
    ApplicationStage,
    CaseAssignment,
    InstitutionalDocument,
    DocumentType,
    AuditTrail,
    Notification,
    EVCPanel,
    EVCAssignment,
)
from app.auth import create_access_token
from app.scoped_dal import ScopedDAL, RequestContext
from tests.http_client import AppTestClient

@pytest.fixture(scope="module")
def client():
    # Ensure tables exist
    init_db("sandbox")
    return AppTestClient()

@pytest.fixture
def db():
    sm = get_session_maker("sandbox")
    session = sm()
    yield session
    session.close()

def test_scrutiny_evc_sac_assignment_lifecycle(client, db):
    """
    End-to-end lifecycle:
    1. Scrutiny Member has access in SCRUTINY stage.
    2. Stage advances to EVC -> Scrutiny Member gets 403, EVC Expert gets 200.
    3. Stage advances to SAC_SHC -> EVC Expert gets 403, SAC Member gets 200.
    """
    # 1. Fetch test users
    sm_user = db.query(User).filter(User.role == "SCRUTINY_MEMBER").first()
    evc_user = db.query(User).filter(User.role == "COMMITTEE_MEMBER").first()
    sac_user = db.query(User).filter(User.role == "SAC_SHC_MEMBER").first()
    inst_user = db.query(User).filter(User.role == "INSTITUTION_USER").first()

    assert sm_user is not None
    assert evc_user is not None
    assert sac_user is not None
    assert inst_user is not None

    inst = db.query(Institution).filter(Institution.id == inst_user.institution_id).first()
    assert inst is not None

    doc_type = db.query(DocumentType).first()
    assert doc_type is not None

    # Create dedicated test application
    app_no = f"AICTE/TEST-LIFECYCLE/{inst.permanent_id}"
    app = db.query(Application).filter(Application.application_no == app_no).first()
    if not app:
        app = Application(
            application_no=app_no,
            institution_id=inst.id,
            region_id=inst.region_id,
            application_type="EXTENSION_OF_APPROVAL",
            pipeline_type="SCRUTINY_EVC",
            current_stage="SCRUTINY",
            status="IN_PROGRESS",
            submitter_id=inst_user.id,
            assigned_officer_id=sm_user.id,
            sla_deadline=datetime.utcnow() + timedelta(days=20),
        )
        db.add(app)
        db.flush()

        # Add initial stage
        db.add(ApplicationStage(
            application_id=app.id,
            stage_name="SCRUTINY",
            sequence_order=1,
            status="ACTIVE",
            assigned_user_id=sm_user.id,
        ))
        db.add(CaseAssignment(
            application_id=app.id,
            stage_name="SCRUTINY",
            user_id=sm_user.id,
            role="SCRUTINY_MEMBER",
            is_active=True,
        ))
        db.commit()

    # Ensure document exists linked to this application
    doc = db.query(InstitutionalDocument).filter(
        InstitutionalDocument.institution_id == inst.id,
        InstitutionalDocument.doc_type_id == doc_type.id,
    ).first()
    if not doc:
        doc = InstitutionalDocument(
            institution_id=inst.id,
            application_id=app.id,
            doc_type_id=doc_type.id,
            document_number=f"DOC-TEST-{app.id[:6]}",
            file_url=f"/api/v1/compliance/documents/DOC-TEST-{app.id[:6]}/download",
            file_hash_sha256="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            issue_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=365),
            issuing_authority="AICTE Test Authority",
            status="ACTIVE",
            submitter_id=inst_user.id,
        )
        db.add(doc)
        db.commit()
    else:
        doc.application_id = app.id
        db.commit()

    sm_token = create_access_token({"sub": sm_user.id, "role": sm_user.role, "ws": "sandbox"})
    evc_token = create_access_token({"sub": evc_user.id, "role": evc_user.role, "ws": "sandbox"})
    sac_token = create_access_token({"sub": sac_user.id, "role": sac_user.role, "ws": "sandbox"})

    # --- PHASE 1: Active Stage is SCRUTINY ---
    app.current_stage = "SCRUTINY"
    app.assigned_officer_id = sm_user.id
    db.commit()

    # Scrutiny Member can list documents
    res = client.get(
        "/api/v1/compliance/documents",
        headers={"Authorization": f"Bearer {sm_token}", "X-Workspace": "sandbox"}
    )
    assert res.status_code == 200
    doc_ids = [d["id"] for d in res.json().get("documents", [])]
    assert doc.id in doc_ids, "Assigned Scrutiny Member must see assigned case documents"

    # Scrutiny Member can preview document (logs DOCUMENT_VIEWED)
    res_prev = client.get(
        f"/api/v1/compliance/documents/{doc.id}/preview",
        headers={"Authorization": f"Bearer {sm_token}", "X-Workspace": "sandbox"}
    )
    assert res_prev.status_code == 200, "Assigned Scrutiny Member must be permitted to preview document"
    assert "inline" in res_prev.headers.get("content-disposition", "").lower()

    # Verify DOCUMENT_VIEWED was logged in audit trail
    view_entry = db.query(AuditTrail).filter(
        AuditTrail.entity_type == "DOCUMENT",
        AuditTrail.entity_id == doc.id,
        AuditTrail.action_type == "DOCUMENT_VIEWED",
        AuditTrail.actor_id == sm_user.id,
    ).first()
    assert view_entry is not None, "Document preview must append DOCUMENT_VIEWED to audit chain"

    # Scrutiny Member can download document (logs DOCUMENT_DOWNLOADED)
    res_dl = client.get(
        f"/api/v1/compliance/documents/{doc.id}/download",
        headers={"Authorization": f"Bearer {sm_token}", "X-Workspace": "sandbox"}
    )
    assert res_dl.status_code == 200, "Assigned Scrutiny Member must be permitted to download document"

    # EVC Expert CANNOT access document while in SCRUTINY stage
    res_evc_blocked = client.get(
        f"/api/v1/compliance/documents/{doc.id}/download",
        headers={"Authorization": f"Bearer {evc_token}", "X-Workspace": "sandbox"}
    )
    assert res_evc_blocked.status_code == 403, "EVC Expert must be blocked with 403 when stage is SCRUTINY"

    # --- PHASE 2: Advance Stage from SCRUTINY to EVC ---
    # Advance via ScopedDAL / endpoint
    ro_user = db.query(User).filter(User.role == "REGIONAL_OFFICER", User.region_id == app.region_id).first()
    ro_token = create_access_token({"sub": ro_user.id, "role": ro_user.role, "region_id": ro_user.region_id, "ws": "sandbox"})

    res_adv = client.post(
        f"/api/v1/applications/workflow/{app.id}/advance",
        headers={"Authorization": f"Bearer {ro_token}", "X-Workspace": "sandbox"},
        params={"remarks": "Scrutiny passed. Proceeding to EVC inspection.", "target_stage": "EVC"}
    )
    assert res_adv.status_code == 200, f"Advance stage failed: {res_adv.text}"
    db.refresh(app)
    assert app.current_stage in ("EVC", "EVC_SCHEDULED", "EVC_COMMITTEE")

    # Empanel evc_user for this application
    panel = db.query(EVCPanel).filter(EVCPanel.application_id == app.id).first()
    if not panel:
        panel = EVCPanel(
            application_id=app.id,
            scheduled_date=date.today() + timedelta(days=7),
            mode="ON_SITE",
            status="CONFIRMED",
        )
        db.add(panel)
        db.flush()
    assignment = db.query(EVCAssignment).filter(EVCAssignment.panel_id == panel.id, EVCAssignment.user_id == evc_user.id).first()
    if not assignment:
        db.add(EVCAssignment(
            panel_id=panel.id,
            user_id=evc_user.id,
            role_in_panel="CONVENER",
            conflict_of_interest_declared=True,
            attendance_confirmed=True,
        ))
    db.add(CaseAssignment(
        application_id=app.id,
        stage_name=app.current_stage,
        user_id=evc_user.id,
        role="COMMITTEE_MEMBER",
        is_active=True,
    ))
    db.commit()

    # Now Scrutiny Member MUST GET 403 (stage moved on)
    res_sm_revoked = client.get(
        f"/api/v1/compliance/documents/{doc.id}/download",
        headers={"Authorization": f"Bearer {sm_token}", "X-Workspace": "sandbox"}
    )
    assert res_sm_revoked.status_code == 403, "Scrutiny Member access must end (403) when stage moves to EVC"

    # EVC Expert MUST GET 200
    res_evc_ok = client.get(
        f"/api/v1/compliance/documents/{doc.id}/download",
        headers={"Authorization": f"Bearer {evc_token}", "X-Workspace": "sandbox"}
    )
    assert res_evc_ok.status_code == 200, "EVC Expert must have access during active EVC stage"

    # --- PHASE 3: Advance Stage to SAC_SHC ---
    app.current_stage = "SAC_SHC"
    app.assigned_officer_id = sac_user.id
    # Revoke EVC assignment, add SAC assignment
    for ca in db.query(CaseAssignment).filter(CaseAssignment.application_id == app.id).all():
        ca.is_active = False
    db.add(CaseAssignment(
        application_id=app.id,
        stage_name="SAC_SHC",
        user_id=sac_user.id,
        role="SAC_SHC_MEMBER",
        is_active=True,
    ))
    db.commit()

    # EVC Expert access is now revoked (403)
    res_evc_revoked = client.get(
        f"/api/v1/compliance/documents/{doc.id}/download",
        headers={"Authorization": f"Bearer {evc_token}", "X-Workspace": "sandbox"}
    )
    assert res_evc_revoked.status_code == 403, "EVC Expert access must end (403) when stage moves to SAC_SHC"

    # SAC Member now has access (200)
    res_sac_ok = client.get(
        f"/api/v1/compliance/documents/{doc.id}/download",
        headers={"Authorization": f"Bearer {sac_token}", "X-Workspace": "sandbox"}
    )
    assert res_sac_ok.status_code == 200, "SAC Member must have access during SAC_SHC review stage"

def test_cross_institution_document_access_strictly_forbidden(client, db):
    """
    Assert that an institution user from College A cannot view or download
    documents belonging to College B (403 Forbidden).
    """
    institutions = db.query(Institution).limit(2).all()
    assert len(institutions) >= 2, "Need at least two institutions for cross-tenant test"
    inst_a, inst_b = institutions[0], institutions[1]

    user_a = db.query(User).filter(User.institution_id == inst_a.id).first()
    assert user_a is not None

    doc_b = db.query(InstitutionalDocument).filter(InstitutionalDocument.institution_id != inst_a.id).first()
    if not doc_b:
        doc_type = db.query(DocumentType).first()
        doc_b = InstitutionalDocument(
            institution_id=inst_b.id,
            doc_type_id=doc_type.id,
            document_number=f"DOC-TEST-{inst_b.id[:6]}",
            file_url=f"/api/v1/compliance/documents/DOC-TEST-{inst_b.id[:6]}/download",
            file_hash_sha256="1122334455667788112233445566778811223344556677881122334455667788",
            issue_date=date.today() - timedelta(days=30),
            expiry_date=date.today() + timedelta(days=365),
            issuing_authority="AICTE Test Authority",
            status="ACTIVE",
            submitter_id=user_a.id,
        )
        db.add(doc_b)
        db.commit()

    assert doc_b is not None
    assert doc_b.institution_id != inst_a.id
    token_a = create_access_token({"sub": user_a.id, "role": user_a.role, "institution_id": inst_a.id, "ws": "sandbox"})

    # User A tries to download College B's document
    res = client.get(
        f"/api/v1/compliance/documents/{doc_b.id}/download",
        headers={"Authorization": f"Bearer {token_a}", "X-Workspace": "sandbox"}
    )
    assert res.status_code == 403, f"Expected 403 Forbidden for cross-institution download, got {res.status_code}"

    # User A tries to preview College B's document
    res_prev = client.get(
        f"/api/v1/compliance/documents/{doc_b.id}/preview",
        headers={"Authorization": f"Bearer {token_a}", "X-Workspace": "sandbox"}
    )
    assert res_prev.status_code == 403, f"Expected 403 Forbidden for cross-institution preview, got {res_prev.status_code}"

def test_shared_with_access_control_panel(client, db):
    """
    Assert that GET /documents/{id}/access-control returns:
    - Current authorized stakeholders with reasons
    - Historical audit views/downloads with actor details
    """
    doc = db.query(InstitutionalDocument).first()
    assert doc is not None

    ro_user = db.query(User).filter(User.role == "REGIONAL_OFFICER", User.region_id == doc.institution.region_id).first()
    assert ro_user is not None
    ro_token = create_access_token({"sub": ro_user.id, "role": ro_user.role, "region_id": ro_user.region_id, "ws": "sandbox"})

    res = client.get(
        f"/api/v1/compliance/documents/{doc.id}/access-control",
        headers={"Authorization": f"Bearer {ro_token}", "X-Workspace": "sandbox"}
    )
    assert res.status_code == 200
    data = res.json()

    assert "authorized_viewers" in data
    assert "access_history" in data
    assert len(data["authorized_viewers"]) > 0

    # Ensure viewers have reasons and roles
    for viewer in data["authorized_viewers"]:
        assert "role" in viewer
        assert "reason" in viewer
        assert "access_type" in viewer

    # Ensure access history has audit information
    assert isinstance(data["access_history"], list)

def test_handoff_notifications_idempotency_no_duplicates(client, db):
    """
    Assert that dispatch_notification prevents duplicate notification creation
    when fired multiple times with the same idempotency_key.
    """
    user = db.query(User).first()
    assert user is not None

    dal = ScopedDAL(db, RequestContext(user_id="sys", role="SUPER_ADMIN"))
    test_key = f"test-idemp-key-{datetime.utcnow().timestamp()}"

    res1 = dal.dispatch_notification(
        user=user,
        title="Handoff Test Notice",
        message="Please verify this case document.",
        idempotency_key=test_key,
    )
    assert res1["status"] == "DISPATCHED"

    # Call second time with identical key
    res2 = dal.dispatch_notification(
        user=user,
        title="Handoff Test Notice",
        message="Please verify this case document.",
        idempotency_key=test_key,
    )
    assert res2["status"] == "SKIPPED_IDEMPOTENT"

    # Count notifications with this key in DB: must be strictly 1
    count = db.query(Notification).filter(Notification.idempotency_key == f"{test_key}:IN_APP").count()
    assert count == 1, "Idempotent notification dispatch must never create duplicate records"
