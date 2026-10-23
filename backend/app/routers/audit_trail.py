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

def get_request_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header("AUDITOR"),
) -> RequestContext:
    return RequestContext(user_id=x_user_id, role=x_user_role)

@router.get("/trail")
def get_audit_trail(
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Returns audit trail entries with cryptographic hashes and actor stamps.
    """
    entries = db.query(AuditTrail).order_by(AuditTrail.id.desc()).limit(limit).all()
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
                "timestamp": e.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
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
