"""
Unit tests for Document-Type Registry, Lease OCR Extraction/Verification,
and External Adapters (DigiLocker and Aadhaar e-Sign).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from tests.http_client import AppTestClient
from app.auth import create_access_token
from app.database import SessionLocal
from app.models import LLMDraft, User, DocumentType, AuditTrail

client = AppTestClient()

@pytest.fixture
def super_admin_token():
    return create_access_token({"sub": "usr-member-sec", "role": "SUPER_ADMIN"})

@pytest.fixture
def regional_officer_token():
    return create_access_token({"sub": "usr-ro-01", "role": "REGIONAL_OFFICER", "region_id": "reg-swro"})

@pytest.fixture
def institution_token():
    return create_access_token({"sub": "usr-inst-01", "role": "INSTITUTION_USER", "institution_id": "inst-01"})

def test_document_type_registry_list_and_create(super_admin_token):
    """Verify listing document types and registering a new statutory document type."""
    # List document types
    r1 = client.get("/api/v1/compliance/document-types")
    assert r1.status_code == 200
    data1 = r1.json()
    assert "registry" in data1
    assert data1["count"] >= 1

    # Create / update document type as Super Admin
    r2 = client.post(
        "/api/v1/compliance/document-types",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "name": "Fire Safety and Evacuation NOC",
            "code": "FIRE_NOC_TEST",
            "category": "SAFETY",
            "validity_years": 1,
            "alert_offsets_days": "60,30,15,7",
            "is_mandatory": True,
        },
    )
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["status"] in ("CREATED", "UPDATED")
    assert data2["code"] == "FIRE_NOC_TEST"

def test_lease_ocr_extraction_with_confidence_scores(regional_officer_token):
    """
    Verify Lease OCR extraction returns structured field confidence scores,
    and Chapter II Clause 2.1(e) deterministic rule evaluation.
    """
    resp = client.post(
        "/api/v1/compliance/ocr/extract-lease",
        headers={"Authorization": f"Bearer {regional_officer_token}"},
        json={
            "institution_id": "inst-01",
            "longest_course_duration_years": 4,
            "is_mega_metro": False,
            "evaluation_date": "2026-10-24",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "EXTRACTED_AWAITING_VERIFICATION"
    assert "draft_id" in data
    assert "fields" in data

    # Validate field confidence scores
    fields = data["fields"]
    assert "lease_start_date" in fields
    assert fields["lease_start_date"]["confidence"] >= 0.90
    assert "lease_end_date" in fields
    assert fields["lease_end_date"]["confidence"] >= 0.90
    assert "course_duration_years" in fields
    assert fields["course_duration_years"]["confidence"] >= 0.95

    # Validate deterministic evaluation per Clause 2.1(e)
    rule = data["rule_evaluation"]
    assert "is_eoa_blocked" in rule
    assert "eoa_block_date" in rule
    assert "eoa_warning_milestones" in rule

def test_lease_ocr_officer_verification_with_sod(super_admin_token, regional_officer_token):
    """
    Verify officer verification gate commits verified parameters and enforces Separation of Duties.
    """
    # 1. Generate OCR draft as Regional Officer
    r_extract = client.post(
        "/api/v1/compliance/ocr/extract-lease",
        headers={"Authorization": f"Bearer {regional_officer_token}"},
        json={"longest_course_duration_years": 4},
    )
    assert r_extract.status_code == 200
    draft_id = r_extract.json()["draft_id"]

    # 2. Requester cannot act as verifier (SoD enforcement)
    r_sod = client.post(
        "/api/v1/compliance/ocr/verify-lease",
        headers={"Authorization": f"Bearer {regional_officer_token}"},
        json={
            "draft_id": draft_id,
            "is_approved": True,
            "verified_start_date": "2015-06-01",
            "verified_end_date": "2045-05-31",
            "verified_course_duration_years": 4,
        },
    )
    assert r_sod.status_code == 403
    assert "SoD Violation" in r_sod.json()["detail"]

    # 3. Super Admin (different user) verifies successfully
    r_verify = client.post(
        "/api/v1/compliance/ocr/verify-lease",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "draft_id": draft_id,
            "is_approved": True,
            "verified_start_date": "2015-06-01",
            "verified_end_date": "2045-05-31",
            "verified_course_duration_years": 4,
            "officer_remarks": "Sub-registrar deed confirmed registered for 30 years.",
        },
    )
    assert r_verify.status_code == 200
    data_v = r_verify.json()
    assert data_v["status"] == "OFFICER_VERIFIED"
    assert data_v["is_approved"] is True

def test_lease_ocr_low_quality_scan_forces_manual_entry(regional_officer_token):
    """
    Item 3: Low-quality degraded scan case where confidence falls below 0.75 threshold
    and forces manual entry plus officer verification.
    """
    resp = client.post(
        "/api/v1/compliance/ocr/extract-lease",
        headers={"Authorization": f"Bearer {regional_officer_token}"},
        json={
            "institution_id": "inst-01",
            "longest_course_duration_years": 4,
            "is_mega_metro": False,
            "is_low_quality_scan": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "LOW_CONFIDENCE_MANUAL_ENTRY_REQUIRED"
    assert data["confidence_threshold_met"] is False
    assert data["requires_manual_entry"] is True
    assert data["average_confidence"] < 0.75
    assert "simulated extraction on synthetic text" in data["ocr_engine"]
    assert "Simulated extraction on synthetic text" in data["governance_note"]
    assert data["rule_evaluation"]["evaluation_status"] == "WITHHELD_DUE_TO_LOW_CONFIDENCE"

def test_digilocker_document_fetch(regional_officer_token):
    """Verify DigiLocker simulated connector pulls cryptographically verified certificate."""
    resp = client.post(
        "/api/v1/adapters/digilocker/fetch",
        headers={"Authorization": f"Bearer {regional_officer_token}"},
        json={"doc_type": "LAND_LEASE"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DIGILOCKER_FETCHED_SUCCESS"
    assert data["connector_type"] == "simulated connector"
    assert "in.gov.digilocker.doc:land_lease:" in data["digilocker_uri"]
    assert len(data["file_hash_sha256"]) == 64
    assert data["is_cryptographically_signed"] is True

def test_esign_signature_stamp(regional_officer_token):
    """Verify e-Sign simulated connector stamps digital signature without Aadhaar claims."""
    resp = client.post(
        "/api/v1/adapters/esign/sign",
        headers={"Authorization": f"Bearer {regional_officer_token}"},
        json={
            "document_id": "doc-test-101",
            "signatory_id_hash": "SHA256:abc123456789",
            "otp": "123456",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ESIGNED_VALID"
    assert data["connector_type"] == "simulated connector"
    assert data["transaction_id"].startswith("ESIGN-TXN-")
    assert "signature_envelope_token" in data

def test_application_import_adapter(super_admin_token):
    """Verify application import adapter from state portal or external ERP (simulated connector)."""
    resp = client.post(
        "/api/v1/adapters/application/import",
        headers={"Authorization": f"Bearer {super_admin_token}"},
        json={
            "institution_pid": "1-109283741",
            "application_type": "INCREASE_INTAKE",
            "academic_year": "2026-2027",
            "source_portal": "KEA_STATE_PORTAL",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "IMPORT_SUCCESS"
    assert data["connector_type"] == "simulated connector"
    assert data["application_no"].startswith("APP-IMP-")
    assert "Scrutiny + EVC" in data["route"]
    assert len(data["stages"]) >= 2

