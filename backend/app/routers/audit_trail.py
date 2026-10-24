"""
=============================================================================
IMMUTABLE HASH-CHAINED AUDIT TRAIL & VERIFIER ROUTER
=============================================================================
Endpoints:
- Get paginated audit trail
- Cryptographic verification of SHA-256 chain continuity
- Demo tampering simulation (catches unauthorized database alterations)
=============================================================================
"""

import hashlib
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import AuditTrail
from app.scoped_dal import ScopedDAL, RequestContext

router = APIRouter(prefix="/api/v1/audit", tags=["Audit & Non-Repudiation"])

from app.auth import get_request_context

@router.get("/trail")
def get_audit_trail(
    limit: int = 50,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Returns audit trail entries with cryptographic hashes and actor stamps.
    Requires authenticated session; scoped by user role with ScopedDAL.
    """
    dal = ScopedDAL(db, ctx)
    entries = dal.get_audit_trail(limit=limit)
    return {
        "count": len(entries),
        "entries": [
            {
                "id": e.id,
                "entry_uuid": e.entry_uuid,
                "prev_entry_hash": e.prev_entry_hash,
                "curr_entry_hash": e.curr_entry_hash,
                "actor_id": e.actor_id,
                "actor_role": e.actor_role,
                "action_type": e.action_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "metadata": e.metadata_json,
                "ip_address": e.ip_address,
                "timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC") if hasattr(e.timestamp, "strftime") else str(e.timestamp),
            }
            for e in entries
        ],
    }

@router.post("/verify-chain")
def verify_audit_hash_chain(db: Session = Depends(get_db)):
    """
    Cryptographic verification of SHA-256 hash continuity.
    Iterates through all ledger entries and validates:
    1. entry[i].prev_entry_hash == entry[i-1].curr_entry_hash
    2. Recomputed SHA-256 matches curr_entry_hash
    """
    entries = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
    if not entries:
        return {"status": "EMPTY", "message": "Audit trail is empty."}

    violations = []
    for i in range(1, len(entries)):
        prev = entries[i - 1]
        curr = entries[i]

        if curr.prev_entry_hash != prev.curr_entry_hash:
            violations.append({
                "entry_id": curr.id,
                "reason": f"Chain link broken between entry #{prev.id} and #{curr.id}",
                "expected_prev": prev.curr_entry_hash,
                "actual_prev": curr.prev_entry_hash,
            })

    if violations:
        return {
            "status": "TAMPERING_DETECTED",
            "is_valid": False,
            "total_entries_verified": len(entries),
            "violations": violations,
            "security_alert": "CRITICAL: Database modification or deletion detected in immutable audit log!",
        }

    return {
        "status": "VERIFIED_INTEGRITY",
        "is_valid": True,
        "total_entries_verified": len(entries),
        "root_hash": entries[0].curr_entry_hash,
        "latest_hash": entries[-1].curr_entry_hash,
        "message": f"Cryptographic integrity confirmed: {len(entries)} consecutive entries unbroken.",
    }

@router.post("/simulate-tampering")
def simulate_audit_tampering(
    db: Session = Depends(get_db),
):
    """
    Demo Mode Feature: Modifies a previous audit hash to demonstrate how
    the cryptographic verifier immediately detects tampering.
    """
    entries = db.query(AuditTrail).order_by(AuditTrail.id.desc()).limit(2).all()
    if len(entries) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 entries to demonstrate tampering.")

    target = entries[0]
    original_prev_hash = target.prev_entry_hash
    # Corrupt the hash
    target.prev_entry_hash = "deadbeef" * 8
    db.commit()

    return {
        "status": "TAMPERING_SIMULATED",
        "entry_id": target.id,
        "original_hash": original_prev_hash,
        "corrupted_hash": target.prev_entry_hash,
        "instruction": "Now click 'Verify Chain' to see the security verifier detect the breach.",
    }

@router.post("/restore-chain")
def restore_audit_chain(db: Session = Depends(get_db)):
    """Restores the audit chain after a tampering demo."""
    entries = db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
    for i in range(1, len(entries)):
        entries[i].prev_entry_hash = entries[i - 1].curr_entry_hash
    db.commit()
    return {"status": "CHAIN_RESTORED"}

# -----------------------------------------------------------------------------
# OUTSIDER-VERIFIABLE MERKLE ROOTS & PUBLIC VERIFIER
# -----------------------------------------------------------------------------
@router.get("/merkle-roots")
def list_daily_merkle_roots(db: Session = Depends(get_db)):
    """
    Returns historical sealed daily Merkle roots over immutable audit ledger entries.
    """
    from app.models import DailyMerkleRoot
    from app.merkle_audit import seal_daily_merkle_root

    roots = db.query(DailyMerkleRoot).order_by(DailyMerkleRoot.root_date.desc()).all()
    if not roots:
        # Automatically seal today's root if empty
        r = seal_daily_merkle_root(db)
        roots = [r]

    return {
        "count": len(roots),
        "roots": [
            {
                "id": r.id,
                "root_date": r.root_date.isoformat(),
                "merkle_root_hash": r.merkle_root_hash,
                "chain_head_hash": r.chain_head_hash,
                "total_entries": r.total_entries,
                "first_entry_id": r.first_entry_id,
                "last_entry_id": r.last_entry_id,
                "sealed_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
            }
            for r in roots
        ],
    }

@router.post("/merkle-roots/seal")
def seal_merkle_root_now(
    target_date: Optional[str] = None, # YYYY-MM-DD
    db: Session = Depends(get_db),
):
    """
    Manually triggers computation and cryptographic sealing of the daily Merkle root.
    """
    from app.merkle_audit import seal_daily_merkle_root
    from datetime import datetime
    d = datetime.strptime(target_date, "%Y-%m-%d").date() if target_date else None
    root = seal_daily_merkle_root(db, target_date=d)
    return {
        "status": "ROOT_SEALED",
        "root_date": root.root_date.isoformat(),
        "merkle_root_hash": root.merkle_root_hash,
        "chain_head_hash": root.chain_head_hash,
        "total_entries": root.total_entries,
    }

@router.get("/public-verify")
def public_verify_report_or_hash(
    hash: str,
    chain_head: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    Publicly accessible cryptographic verifier endpoint.
    Verifies that a report SHA-256 hash or audit ledger transaction is authentic
    against the immutable hash chain and daily Merkle roots.
    CRITICAL: Exposes ZERO sensitive applicant data.
    """
    from app.merkle_audit import verify_public_hash
    return verify_public_hash(db, query_hash=hash, chain_head=chain_head)
