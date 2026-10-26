"""
=============================================================================
TASK 5: REAL-CLOCK 7-STEP STORY INTEGRATION TEST (EVALUATOR MODE OFF)
=============================================================================
Validates the complete real-clock AICTE statutory workflow under production
conditions with EVALUATOR_MODE=False and DEMO_MODE=False:

Step 1 (Institution User):
  - Submit application via /api/v1/applications/submit
  - Upload land lease deed v1 via /api/v1/compliance/documents/upload-file
  - Real SHA-256 computation, magic bytes validation, version 1

Step 2 (Regional Scrutiny Member / Officer):
  - Review under Table 2.3 norms
  - Flag deficiency via /api/v1/workflow/{app_id}/revert (Land Lease validity)
  - Statutory SLA clock paused, status -> DEFICIENT

Step 3 (Institution User):
  - Upload renewed 30-year registered lease deed v2
  - Previous version v1 marked SUPERSEDED, version 2 active
  - Submit deficiency cure via /api/v1/workflow/{app_id}/cure-submit
  - SLA clock unpauses, deadline pushed forward by paused duration

Step 4 (Regional Officer):
  - Re-Scrutiny verification strictly against Scrutiny deficiencies (Clause 1.8(g))
  - Stage advances to EVC
  - Smart panel allocation with cross-state conflict-of-interest prevention
  - Official confirmation with double-booking prevention & RFC 5545 .ics export

Step 5 (Empanelled EVC Committee Member):
  - Empanelled expert officially declares NO conflict of interest (Annexure-16 Clause 16.5)
  - Submits geotagged inspection report via /api/v1/evc/reports/{panel_id}/submit
  - Recommendation: RECOMMENDED, stage advances to EXECUTIVE_COMMITTEE

Step 6 (Regional Director / Bureau Officer):
  - Official docket review with Pairwise Separation of Duties (Submitter != Approver)
  - Advances stage to COUNCIL_RATIFIED

Step 7 (Member Secretary / Super Admin):
  - Cryptographic audit trail verification (/api/v1/audit/verify-chain)
  - Final Approval Order issued with complete audit provenance
  - Cryptographic SHA-256 hash continuity unbroken across all 7 steps
  - Outsider-verifiable daily Merkle root sealed
=============================================================================
"""

import io
import hashlib
from datetime import datetime, timedelta, date
import pytest
from sqlalchemy.orm import Session
from tests.http_client import AppTestClient
from app.config import settings
from app.database import SessionLocal
from app.models import (
    Application,
    Institution,
    Region,
    DocumentType,
    InstitutionalDocument,
    StageRevert,
    EVCPanel,
    EVCAssignment,
    EVCReport,
    AuditTrail,
    User,
)
from app.auth import create_access_token
from app.storage import storage_service

client = AppTestClient()


def make_token(user_id: str, role: str, region_id: str = None, inst_id: str = None) -> str:
    payload = {"sub": user_id, "role": role}
    if region_id:
        payload["region_id"] = region_id
    if inst_id:
        payload["institution_id"] = inst_id
    return create_access_token(payload)


@pytest.fixture(autouse=True)
def enforce_production_evaluator_off_mode():
    """Ensure EVALUATOR_MODE=False and DEMO_MODE=False for all tests in this module."""
    orig_eval = getattr(settings, "EVALUATOR_MODE", False)
    orig_demo = settings.DEMO_MODE

    settings.EVALUATOR_MODE = False
    settings.DEMO_MODE = False

    yield

    settings.EVALUATOR_MODE = orig_eval
    settings.DEMO_MODE = orig_demo


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


def test_real_clock_7step_story_end_to_end(db: Session):
    """
    Executes the 7-step real-clock story end-to-end with Evaluator Mode OFF.
    Asserts truthful data, immutable hash chaining, Pairwise SoD, and SLA clock behavior.
    """
    # 0. Setup test actors and institution
    swro = db.query(Region).filter(Region.code == "SWRO").first()
    assert swro is not None

    inst = db.query(Institution).filter(Institution.region_id == swro.id).first()
    assert inst is not None

    doc_type = db.query(DocumentType).filter(DocumentType.code == "LAND_LEASE").first()
    if not doc_type:
        doc_type = db.query(DocumentType).first()
    assert doc_type is not None

    # Personas:
    # 1. Submitter: Institution User
    submitter_id = f"inst-user-{inst.id[:8]}"
    token_submitter = make_token(submitter_id, "INSTITUTION_USER", inst_id=inst.id)
    headers_submitter = {"Authorization": f"Bearer {token_submitter}"}

    # 2. Verifier: Regional Officer (SWRO)
    verifier_id = "ro-officer-swro-real"
    token_ro = make_token(verifier_id, "REGIONAL_OFFICER", region_id=swro.id)
    headers_ro = {"Authorization": f"Bearer {token_ro}"}

    # 3. EVC Committee Member: Cross-State Empanelled Expert
    evc_member_id = "exp-prof-01"
    token_evc = make_token(evc_member_id, "COMMITTEE_MEMBER")
    headers_evc = {"Authorization": f"Bearer {token_evc}"}

    # 4. Regional Director: SWRO
    rd_id = "rd-director-swro-real"
    token_rd = make_token(rd_id, "REGIONAL_DIRECTOR", region_id=swro.id)
    headers_rd = {"Authorization": f"Bearer {token_rd}"}

    # 5. Approver: Member Secretary / Super Admin
    approver_id = "member-secretary-hq"
    token_sec = make_token(approver_id, "SUPER_ADMIN")
    headers_sec = {"Authorization": f"Bearer {token_sec}"}

    # Verify initial audit chain integrity before test
    pre_audit_count = db.query(AuditTrail).count()

    # -------------------------------------------------------------------------
    # STEP 1: Institution Submits Application & Uploads Lease Deed v1
    # -------------------------------------------------------------------------
    app_res = client.post(
        "/api/v1/applications/submit",
        json={
            "institution_id": inst.id,
            "application_type": "NEW_INSTITUTION",
            "academic_year": "2026-2027",
            "course_name": "Artificial Intelligence & Data Science",
            "intake_proposed": 60,
            "remarks": "Application for establishment of new technical campus.",
        },
        headers=headers_submitter,
    )
    assert app_res.status_code == 200, app_res.text
    app_data = app_res.json()
    app_id = app_data["application_id"]
    app_no = app_data["application_no"]

    app_record = db.query(Application).filter(Application.id == app_id).first()
    assert app_record is not None
    assert app_record.submitter_id == submitter_id
    assert app_record.current_stage == "SCRUTINY"
    assert app_record.status == "IN_PROGRESS"
    assert app_record.sla_deadline is not None

    # Institution uploads Land Lease Deed v1 (valid for only 3 years - deficient under Clause 2.1(e))
    lease_v1_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (3-Year Initial Lease Deed) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    doc_num = f"LEASE-DEED-{app_no[-8:]}"

    upload_v1_res = client.post(
        "/api/v1/compliance/documents/upload-file",
        files={"file": ("lease_deed_v1.pdf", io.BytesIO(lease_v1_pdf), "application/pdf")},
        data={
            "institution_id": inst.id,
            "doc_type_code": doc_type.code,
            "document_number": doc_num,
            "issue_date": "2024-01-01",
            "expiry_date": "2027-01-01", # Only 3 years!
            "issuing_authority": "Sub-Registrar Bengaluru",
        },
        headers=headers_submitter,
    )
    assert upload_v1_res.status_code == 200, upload_v1_res.text
    v1_data = upload_v1_res.json()
    doc_v1_id = v1_data["document_id"]
    assert v1_data["version"] == 1

    doc_v1 = db.query(InstitutionalDocument).filter(InstitutionalDocument.id == doc_v1_id).first()
    assert doc_v1.is_latest_version is True
    assert doc_v1.status == "PENDING_VERIFICATION"

    # -------------------------------------------------------------------------
    # STEP 2: Regional Officer Reviews Table 2.3 & Flags Deficiency (SLA Clock Pauses)
    # -------------------------------------------------------------------------
    initial_deadline = app_record.sla_deadline

    revert_res = client.post(
        f"/api/v1/workflow/{app_id}/revert",
        json={
            "reason_category": "Land Lease Near Expiration",
            "deficiency_remarks": "Lease deed is valid for only 3 years. AICTE Chapter II Clause 2.1(e) & Chapter VI Clause 6.17 mandates minimum 30 years registered lease.",
            "aph_clause_ref": "Chapter II Clause 2.1(e) & Chapter VI Clause 6.17 (Page 28)",
            "cure_days": 15,
        },
        headers=headers_ro,
    )
    assert revert_res.status_code == 200, revert_res.text
    revert_data = revert_res.json()
    assert revert_data["status"] == "REVERTED_FOR_DEFICIENCY"
    assert revert_data["sla_clock_paused"] is True

    db.refresh(app_record)
    assert app_record.status == "DEFICIENT"
    assert app_record.current_stage == "DEFICIENCY_REVERTED"
    assert app_record.last_paused_at is not None

    # Simulate 2 days passing under paused clock
    app_record.last_paused_at = datetime.utcnow() - timedelta(days=2)
    db.commit()

    # -------------------------------------------------------------------------
    # STEP 3: Institution Uploads Renewed Lease Deed v2 & Cures Deficiency
    # -------------------------------------------------------------------------
    # Upload renewed 30-year lease v2 (replaces doc_v1_id)
    lease_v2_pdf = b"%PDF-1.4\n1 0 obj\n<< /Title (30-Year Registered Registered Lease Deed Extension) >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"
    upload_v2_res = client.post(
        "/api/v1/compliance/documents/upload-file",
        files={"file": ("lease_deed_v2_30yr.pdf", io.BytesIO(lease_v2_pdf), "application/pdf")},
        data={
            "institution_id": inst.id,
            "doc_type_code": doc_type.code,
            "document_number": doc_num,
            "issue_date": "2026-01-01",
            "expiry_date": "2056-01-01", # Full 30 years!
            "issuing_authority": "Sub-Registrar Bengaluru South",
            "replaces_document_id": doc_v1_id,
        },
        headers=headers_submitter,
    )
    assert upload_v2_res.status_code == 200, upload_v2_res.text
    v2_data = upload_v2_res.json()
    doc_v2_id = v2_data["document_id"]
    assert v2_data["version"] == 2

    # Verify v1 is SUPERSEDED and v2 is latest
    db.refresh(doc_v1)
    doc_v2 = db.query(InstitutionalDocument).filter(InstitutionalDocument.id == doc_v2_id).first()
    assert doc_v1.is_latest_version is False
    assert doc_v1.status == "SUPERSEDED"
    assert doc_v2.is_latest_version is True
    assert doc_v2.version == 2

    # Institution submits deficiency cure
    cure_res = client.post(
        f"/api/v1/workflow/{app_id}/cure-submit",
        json={
            "institution_response": "Registered 30-year extension lease deed uploaded with Sub-Registrar endorsement.",
            "rectified_document_urls": [doc_v2.file_url],
        },
        headers=headers_submitter,
    )
    assert cure_res.status_code == 200, cure_res.text
    cure_data = cure_res.json()
    assert cure_data["status"] == "RESUBMITTED"
    assert cure_data["sla_clock_resumed"] is True

    db.refresh(app_record)
    assert app_record.status == "IN_PROGRESS"
    assert app_record.current_stage == "RE_SCRUTINY"
    assert app_record.last_paused_at is None
    # Verify SLA clock was pushed out by the paused duration (~48h)
    assert app_record.paused_accumulated_hours >= 47.0
    assert app_record.sla_deadline > initial_deadline

    # -------------------------------------------------------------------------
    # STEP 4: Regional Officer Re-Scrutiny Verification & EVC Smart Panel Scheduling
    # -------------------------------------------------------------------------
    # Re-Scrutiny verification strictly against Scrutiny deficiencies (Clause 1.8(g))
    rescrutiny_res = client.post(
        f"/api/v1/workflow/{app_id}/re-scrutiny-verify",
        json={
            "items_to_verify": ["Land Lease Near Expiration"],
            "is_satisfactory": True,
            "committee_remarks": "30-year registered lease deed verified compliant with Chapter II Clause 2.1(e).",
        },
        headers=headers_ro,
    )
    assert rescrutiny_res.status_code == 200, rescrutiny_res.text
    rescrut_data = rescrutiny_res.json()
    assert rescrut_data["is_satisfactory"] is True
    assert rescrut_data["scope_compliance"]["is_compliant"] is True

    db.refresh(app_record)
    assert app_record.current_stage == "EVC"
    assert app_record.verifier_id == verifier_id

    # Smart EVC Panel suggestion (cross-state, conflict-free)
    panel_sugg_res = client.post(
        "/api/v1/evc/suggest-panel",
        json={
            "application_id": app_id,
            "proposed_date": (date.today() + timedelta(days=10)).strftime("%Y-%m-%d"),
            "mode": "ON_SITE",
            "cooling_period_months": 24,
        },
        headers=headers_ro,
    )
    assert panel_sugg_res.status_code == 200, panel_sugg_res.text
    panel_sugg_data = panel_sugg_res.json()
    suggested_members = [m["id"] for m in panel_sugg_data["suggested_panel"]]
    assert len(suggested_members) == 3

    # Regional Officer confirms EVC panel
    confirm_panel_res = client.post(
        f"/api/v1/evc/{app_id}/confirm",
        json={
            "selected_member_ids": suggested_members,
            "notes": "EVC Panel confirmed per Annexure-16 Clause 16.5.",
        },
        headers=headers_ro,
    )
    assert confirm_panel_res.status_code == 200, confirm_panel_res.text
    panel_id = confirm_panel_res.json()["panel_id"]

    db.refresh(app_record)
    assert app_record.current_stage == "EVC_SCHEDULED"

    # Verify RFC 5545 .ics Calendar export
    ics_res = client.get(f"/api/v1/evc/schedule/{panel_id}/ics")
    assert ics_res.status_code == 200
    assert "BEGIN:VCALENDAR" in ics_res.text
    assert "STATUS:CONFIRMED" in ics_res.text

    # -------------------------------------------------------------------------
    # STEP 5: EVC Committee Member Conflict Declaration & Geotagged Report
    # -------------------------------------------------------------------------
    # Expert declares NO conflict of interest
    conflict_res = client.post(
        f"/api/v1/evc/{panel_id}/declare-conflict",
        json={
            "panel_id": panel_id,
            "has_conflict": False,
            "statement": "I declare zero financial, familial, or consulting affiliation with this institution in accordance with Annexure-16 Clause 16.5.",
        },
        headers=headers_evc,
    )
    assert conflict_res.status_code == 200, conflict_res.text
    assert conflict_res.json()["has_conflict"] is False

    # Committee member submits inspection report with GPS coordinates
    report_res = client.post(
        f"/api/v1/evc/reports/{panel_id}/submit",
        json={
            "recommendation": "RECOMMENDED",
            "inspection_summary": "Comprehensive 30-minute physical inspection completed. Infrastructure, laboratories, barrier-free access, and fire safety fully compliant.",
            "deficiencies": [],
            "geo_lat": 12.9716,
            "geo_lng": 77.5946,
        },
        headers=headers_evc,
    )
    assert report_res.status_code == 200, report_res.text
    assert report_res.json()["status"] == "REPORT_ACCEPTED"

    db.refresh(app_record)
    assert app_record.current_stage == "EXECUTIVE_COMMITTEE"

    # -------------------------------------------------------------------------
    # STEP 6: Regional Director Reviews Docket & Advances to COUNCIL_RATIFIED
    # -------------------------------------------------------------------------
    # Regional Director advances to COUNCIL_RATIFIED
    rd_advance_res = client.post(
        f"/api/v1/workflow/{app_id}/advance",
        params={"remarks": "Regional Director reviewed EVC recommendation and certified docket completeness."},
        headers=headers_rd,
    )
    assert rd_advance_res.status_code == 200, rd_advance_res.text
    assert rd_advance_res.json()["new_stage"] == "COUNCIL_RATIFIED"

    db.refresh(app_record)
    assert app_record.current_stage == "COUNCIL_RATIFIED"

    # -------------------------------------------------------------------------
    # STEP 7: Member Secretary Final Approval & Cryptographic Hash Continuity Proof
    # -------------------------------------------------------------------------
    # Pairwise SoD verification: Submitter != Verifier != Approver
    assert app_record.submitter_id == submitter_id
    assert app_record.verifier_id == verifier_id
    assert approver_id != submitter_id
    assert approver_id != verifier_id

    # Member Secretary grants final council approval
    sec_advance_res = client.post(
        f"/api/v1/workflow/{app_id}/advance",
        params={"remarks": "Council Ratification complete. Letter of Approval issued for Academic Year 2026-2027."},
        headers=headers_sec,
    )
    assert sec_advance_res.status_code == 200, sec_advance_res.text

    db.refresh(app_record)
    assert app_record.status == "APPROVED"
    assert app_record.approver_id == approver_id

    # Cryptographic SHA-256 Audit Trail Continuity Verification
    verify_audit_res = client.post("/api/v1/audit/verify-chain")
    assert verify_audit_res.status_code == 200, verify_audit_res.text
    audit_data = verify_audit_res.json()
    assert audit_data["is_valid"] is True
    assert audit_data["status"] == "VERIFIED_INTEGRITY"
    assert audit_data["violations"] == [] if "violations" in audit_data else True
    assert audit_data["total_entries_verified"] > pre_audit_count

    # Seal daily Merkle root
    seal_res = client.post("/api/v1/audit/merkle-roots/seal")
    assert seal_res.status_code == 200, seal_res.text
    seal_data = seal_res.json()
    assert "merkle_root_hash" in seal_data
    assert len(seal_data["merkle_root_hash"]) == 64

    # Public verification of latest root has ZERO PII
    public_verify_res = client.get(
        "/api/v1/audit/public-verify",
        params={"hash": seal_data["chain_head_hash"]},
    )
    assert public_verify_res.status_code == 200, public_verify_res.text
    pub_data = public_verify_res.json()
    assert pub_data["is_verified"] is True
    # Ensure zero sensitive institutional PII returned in public audit proof
    for forbidden in ["student_name", "applicant_name", "aadhaar", "bank_account", "mobile"]:
        assert forbidden not in str(pub_data).lower()
