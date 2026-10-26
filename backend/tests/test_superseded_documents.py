"""
Automated Test Suite for Task 3: Superseded Document Versions & Truthful Compliance Data.

Verifies:
1. Uploading a renewal document marks previous document version as SUPERSEDED.
2. Superseded document v1 remains downloadable via authenticated download endpoint.
3. Version history endpoint returns all versions with correct SUPERSEDED / latest status.
4. APScheduler / regulatory evaluation ignores SUPERSEDED documents for expiry alerts.
"""

import os
import sys
from datetime import date, timedelta, datetime
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tests.http_client import AppTestClient
from app.auth import create_access_token
from app.database import SessionLocal
from app.models import InstitutionalDocument, Institution, DocumentType
from app.scheduler import RegulatorySchedulerService

client = AppTestClient()


@pytest.fixture
def test_institution():
    db = SessionLocal()
    inst = db.query(Institution).first()
    db.close()
    return inst


@pytest.fixture
def institution_token(test_institution):
    return create_access_token({
        "sub": "usr-test-inst",
        "role": "INSTITUTION_USER",
        "institution_id": test_institution.id,
    })


@pytest.fixture
def officer_token(test_institution):
    return create_access_token({
        "sub": "usr-test-ro",
        "role": "REGIONAL_OFFICER",
        "region_id": test_institution.region_id,
    })


def test_superseded_document_renewal_flow(test_institution, institution_token, officer_token):
    """
    1. Upload document v1.
    2. Upload renewal document v2 replacing v1.
    3. Assert v1 has status == 'SUPERSEDED' and is_latest_version == False.
    4. Assert v2 has version == 2 and is_latest_version == True.
    5. Assert v1 is still downloadable via GET /compliance/documents/{v1_id}/download.
    6. Assert version history lists both versions correctly.
    7. Assert scheduler evaluation skips v1.
    """
    db = SessionLocal()
    doc_type = db.query(DocumentType).first()
    assert doc_type is not None, "DocumentType registry must have at least one type"

    today_str = date.today().strftime("%Y-%m-%d")
    expiry_v1 = (date.today() + timedelta(days=20)).strftime("%Y-%m-%d")

    # Step 1: Upload version 1
    resp1 = client.post(
        "/api/v1/compliance/documents/upload",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "institution_id": test_institution.id,
            "doc_type_code": doc_type.code,
            "document_number": f"TEST-RENEWAL-DOC-{datetime.utcnow().timestamp()}",
            "file_content_mock": "%PDF-1.4\nTest Original Document v1 Content\nEOF",
            "issue_date": today_str,
            "expiry_date": expiry_v1,
            "issuing_authority": "Karnataka State Land Authority",
        },
    )
    assert resp1.status_code == 200, resp1.text
    data1 = resp1.json()
    doc1_id = data1["document_id"]
    assert data1["version"] == 1

    # Verify v1 state in DB
    db.expire_all()
    v1_record = db.query(InstitutionalDocument).filter(InstitutionalDocument.id == doc1_id).first()
    assert v1_record.is_latest_version is True
    assert v1_record.status == "PENDING_VERIFICATION"

    # Step 2: Upload renewal document v2
    expiry_v2 = (date.today() + timedelta(days=365)).strftime("%Y-%m-%d")
    resp2 = client.post(
        "/api/v1/compliance/documents/upload",
        headers={"Authorization": f"Bearer {institution_token}"},
        json={
            "institution_id": test_institution.id,
            "doc_type_code": doc_type.code,
            "document_number": v1_record.document_number,
            "file_content_mock": "%PDF-1.4\nTest Renewal Document v2 Content\nEOF",
            "issue_date": today_str,
            "expiry_date": expiry_v2,
            "issuing_authority": "Karnataka State Land Authority",
        },
    )
    assert resp2.status_code == 200, resp2.text
    data2 = resp2.json()
    doc2_id = data2["document_id"]
    assert data2["version"] == 2

    # Step 3: Assert v1 has status == 'SUPERSEDED' and is_latest_version == False
    db.expire_all()
    v1_updated = db.query(InstitutionalDocument).filter(InstitutionalDocument.id == doc1_id).first()
    v2_record = db.query(InstitutionalDocument).filter(InstitutionalDocument.id == doc2_id).first()

    assert v1_updated.status == "SUPERSEDED", f"Expected v1 status SUPERSEDED, got {v1_updated.status}"
    assert v1_updated.is_latest_version is False

    assert v2_record.version == 2
    assert v2_record.is_latest_version is True
    assert v2_record.status == "PENDING_VERIFICATION"

    # Step 4: Verify v1 remains downloadable via GET /api/v1/compliance/documents/{id}/download
    download_v1_resp = client.get(
        f"/api/v1/compliance/documents/{doc1_id}/download",
        headers={"Authorization": f"Bearer {institution_token}"},
    )
    assert download_v1_resp.status_code == 200
    assert len(download_v1_resp.content) > 0
    assert download_v1_resp.headers.get("X-Document-Version") == "1"

    # Download v2
    download_v2_resp = client.get(
        f"/api/v1/compliance/documents/{doc2_id}/download",
        headers={"Authorization": f"Bearer {institution_token}"},
    )
    assert download_v2_resp.status_code == 200
    assert download_v2_resp.headers.get("X-Document-Version") == "2"

    # Step 5: Verify version history endpoint returns both versions
    versions_resp = client.get(
        f"/api/v1/compliance/documents/{doc2_id}/versions",
        headers={"Authorization": f"Bearer {institution_token}"},
    )
    assert versions_resp.status_code == 200
    v_data = versions_resp.json()
    assert v_data["total_versions"] >= 2
    ver_status_map = {v["version"]: v["status"] for v in v_data["versions"]}
    assert ver_status_map[1] == "SUPERSEDED"

    # Step 6: Verify scheduler evaluation explicitly ignores SUPERSEDED documents
    scheduler = RegulatorySchedulerService()
    # If v1 was active (with expiry within 20 days), it would trigger alert.
    # But because it is SUPERSEDED, scheduler must not evaluate it.
    eval_stats = scheduler.evaluate_and_dispatch_all(db=db, dry_run=True)
    # Check that doc1_id is NOT in notifications
    for notif in eval_stats.get("notifications_dispatched", []):
        assert notif.get("entity_id") != doc1_id, "SUPERSEDED document must not trigger expiry alert"

    db.close()
