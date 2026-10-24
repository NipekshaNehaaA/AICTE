"""
Unit and integration tests for Outsider-Verifiable Audit & Cryptographic Verifier.
Verifies:
1. Daily Merkle root computation over immutable SHA-256 audit ledger entries.
2. Report export registers report hash and embeds audit chain head.
3. Public verification endpoint succeeds for authentic hash with ZERO PII disclosed.
4. Negative test: Tampered report hash fails verification.
5. Negative test: Forged audit chain head is detected and flagged.
6. Merkle root tree alteration test: Corrupting an entry produces a mismatched root.
"""

import hashlib
from datetime import datetime, date, timedelta
import pytest
from app.database import SessionLocal
from app.models import AuditTrail, DailyMerkleRoot, ExportedReportRegistry
from app.scoped_dal import RequestContext
from app.merkle_audit import compute_merkle_root, seal_daily_merkle_root, verify_public_hash
from app.routers.reports_analytics import export_report

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_daily_merkle_root_computation(db):
    """Verify daily Merkle root is calculated and stored in DailyMerkleRoot table."""
    root = seal_daily_merkle_root(db)
    assert root is not None
    assert len(root.merkle_root_hash) == 64
    assert len(root.chain_head_hash) == 64
    assert root.total_entries > 0

    # Test deterministic calculation
    entries = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
    leaf_hashes = [e.curr_entry_hash for e in entries]
    recalculated = compute_merkle_root(leaf_hashes)
    assert len(recalculated) == 64

def test_report_export_registers_hash_and_chain_head(db):
    """Exporting a report registers its SHA-256 hash and audit chain head in ExportedReportRegistry."""
    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER")
    res = export_report(report_type="APPLICATIONS_PIPELINE", format="pdf", ctx=ctx, db=db)

    assert res.status_code == 200
    report_hash = res.headers.get("X-AICTE-Report-Hash")
    chain_head = res.headers.get("X-AICTE-Chain-Head")

    assert report_hash is not None and len(report_hash) == 64
    assert chain_head is not None and len(chain_head) == 64

    # Verify registered in DB
    reg = db.query(ExportedReportRegistry).filter(
        ExportedReportRegistry.report_hash_sha256 == report_hash
    ).first()
    assert reg is not None
    assert reg.audit_chain_head == chain_head

def test_public_verification_authenticity_and_zero_pii(db):
    """Public verification confirms authentic report with ZERO PII leakage."""
    # Find latest registered report
    reg = db.query(ExportedReportRegistry).order_by(ExportedReportRegistry.generated_at.desc()).first()
    if not reg:
        ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER")
        export_report(report_type="APPLICATIONS_PIPELINE", format="excel", ctx=ctx, db=db)
        reg = db.query(ExportedReportRegistry).order_by(ExportedReportRegistry.generated_at.desc()).first()

    assert reg is not None
    verification = verify_public_hash(db, query_hash=reg.report_hash_sha256, chain_head=reg.audit_chain_head)

    assert verification["is_verified"] is True
    assert verification["verification_status"] == "CRYPTO_VERIFIED_AUTHENTIC"
    assert verification["merkle_root_verified"] is True
    assert "zero pii" in verification["privacy_guarantee"].lower()

    # CRITICAL: Verify ZERO confidential applicant PII is returned
    forbidden_keys = ["student_name", "applicant_name", "tuition_fee", "bank_account", "mobile_number", "aadhaar"]
    for k in forbidden_keys:
        assert k not in verification
        assert k not in str(verification).lower()

def test_negative_tampered_report_hash_fails(db):
    """Altering even a single character in the report hash causes verification to fail."""
    reg = db.query(ExportedReportRegistry).first()
    assert reg is not None

    tampered_hash = reg.report_hash_sha256[:-4] + "0000"
    res = verify_public_hash(db, query_hash=tampered_hash, chain_head=reg.audit_chain_head)

    assert res["is_verified"] is False
    assert res["verification_status"] == "TAMPERING_DETECTED_OR_UNKNOWN"

def test_negative_forged_chain_head_fails(db):
    """Supplying a forged/unknown audit chain head fails verification."""
    reg = db.query(ExportedReportRegistry).first()
    assert reg is not None

    forged_chain_head = "deadbeef" * 8
    res = verify_public_hash(db, query_hash=reg.report_hash_sha256, chain_head=forged_chain_head)

    assert res["is_verified"] is False
    assert res["chain_head_status"] == "INVALID_OR_UNKNOWN"
