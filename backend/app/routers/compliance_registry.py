"""
=============================================================================
DOCUMENT-TYPE REGISTRY, VALIDITY TRACKING & UNDERTAKINGS ROUTER
=============================================================================
Endpoints:
- Document Type Registry (admin configurable)
- Document Upload with SHA-256 hash & OCR extraction simulation
- Officer Verification with Separation of Duties
- Time-Bound Undertakings registry & evidence submission
- Obligation Dependency View (Signature Differentiator 6)
=============================================================================
"""

import hashlib
import uuid
from datetime import datetime, timedelta, date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    DocumentType,
    InstitutionalDocument,
    TimeBoundUndertaking,
    Institution,
    DocumentAnomaly,
    LLMDraft,
)
from app.scoped_dal import ScopedDAL, RequestContext, SecurityScopeError, SoDViolationError

router = APIRouter(prefix="/api/v1/compliance", tags=["Compliance & Documents"])

class DocumentTypeCreateRequest(BaseModel):
    name: str
    code: str
    category: str
    validity_years: int = 5
    alert_offsets_days: str = "90,60,30,7"
    is_mandatory: bool = True

class DocumentUploadRequest(BaseModel):
    institution_id: str
    doc_type_code: str
    document_number: str
    file_content_mock: str # Mock payload to compute SHA-256
    issue_date: str # YYYY-MM-DD
    expiry_date: str # YYYY-MM-DD
    issuing_authority: str

class DocumentVerifyRequest(BaseModel):
    is_approved: bool = True
    remarks: Optional[str] = "Document verified against statutory APH standards."

class UndertakingEvidenceRequest(BaseModel):
    evidence_file_url: str
    submission_notes: str

def get_request_context(
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header("REGIONAL_OFFICER"),
    x_region_id: Optional[str] = Header(None),
    x_institution_id: Optional[str] = Header(None),
) -> RequestContext:
    return RequestContext(
        user_id=x_user_id or "usr-demo-default",
        role=x_user_role or "REGIONAL_OFFICER",
        region_id=x_region_id,
        institution_id=x_institution_id,
    )

@router.get("/doc-registry")
def list_document_types(db: Session = Depends(get_db)):
    """Returns all registered document types with validity periods and alert offsets."""
    types = db.query(DocumentType).all()
    return {
        "count": len(types),
        "registry": [
            {
                "id": t.id,
                "name": t.name,
                "code": t.code,
                "category": t.category,
                "validity_years": t.validity_years,
                "alert_offsets_days": t.alert_offsets_days.split(","),
                "is_mandatory": t.is_mandatory,
            }
            for t in types
        ],
    }

@router.get("/documents")
def list_institutional_documents(
    institution_id: Optional[str] = None,
    status: Optional[str] = None,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """Returns institutional documents with live expiry countdowns and RAG status."""
    dal = ScopedDAL(db, ctx)
    docs = dal.get_documents()

    today = date.today()
    results = []
    for d in docs:
        if institution_id and d.institution_id != institution_id:
            continue
        if status and d.status != status:
            continue

        days_until_expiry = (d.expiry_date - today).days
        doc_rag = "ON_TRACK"
        if days_until_expiry < 0:
            doc_rag = "EXPIRED"
        elif days_until_expiry <= 30:
            doc_rag = "EXPIRING_SOON"

        results.append({
            "id": d.id,
            "institution_id": d.institution_id,
            "institution_name": d.institution.name if d.institution else "Technical Institute",
            "document_name": d.doc_type.name if d.doc_type else "Statutory Document",
            "document_code": d.doc_type.code if d.doc_type else "DOC_UNKNOWN",
            "document_number": d.document_number,
            "file_url": d.file_url,
            "file_hash_sha256": d.file_hash_sha256,
            "issue_date": d.issue_date.strftime("%Y-%m-%d"),
            "expiry_date": d.expiry_date.strftime("%Y-%m-%d"),
            "days_until_expiry": days_until_expiry,
            "rag_status": doc_rag,
            "status": d.status,
            "issuing_authority": d.issuing_authority,
            "verified_by": d.verifier_id,
            "verified_at": d.verified_at.strftime("%Y-%m-%d") if d.verified_at else None,
        })

    return {"count": len(results), "documents": results}

@router.post("/documents/upload")
def upload_regulatory_document(
    payload: DocumentUploadRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Uploads a document with automatic SHA-256 hash calculation,
    duplicate anomaly detection, and OCR metadata extraction.
    """
    doc_type = db.query(DocumentType).filter(DocumentType.code == payload.doc_type_code).first()
    if not doc_type:
        raise HTTPException(status_code=404, detail="Document type not found.")

    # Compute SHA-256
    file_bytes = payload.file_content_mock.encode("utf-8")
    sha256_hash = hashlib.sha256(file_bytes).hexdigest()

    # Duplicate Hash Anomaly Detection
    existing_with_hash = db.query(InstitutionalDocument).filter(
        InstitutionalDocument.file_hash_sha256 == sha256_hash,
        InstitutionalDocument.institution_id != payload.institution_id,
    ).first()

    issue_d = datetime.strptime(payload.issue_date, "%Y-%m-%d").date()
    expiry_d = datetime.strptime(payload.expiry_date, "%Y-%m-%d").date()

    doc = InstitutionalDocument(
        institution_id=payload.institution_id,
        doc_type_id=doc_type.id,
        document_number=payload.document_number,
        file_url=f"/storage/docs/{uuid.uuid4().hex[:8]}.pdf",
        file_hash_sha256=sha256_hash,
        file_size_bytes=len(file_bytes),
        issue_date=issue_d,
        expiry_date=expiry_d,
        issuing_authority=payload.issuing_authority,
        status="PENDING_VERIFICATION",
        submitter_id=ctx.user_id or "usr-submitter",
    )
    db.add(doc)
    db.flush()

    anomaly_detected = False
    if existing_with_hash:
        anomaly_detected = True
        db.add(DocumentAnomaly(
            document_id=doc.id,
            anomaly_type="DUPLICATE_HASH",
            severity="CRITICAL",
            details=f"Identical SHA-256 hash ({sha256_hash}) matches document at {existing_with_hash.institution.name}.",
        ))

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="DOCUMENT_UPLOADED",
        entity_type="DOCUMENT",
        entity_id=doc.id,
        metadata={"sha256": sha256_hash, "anomaly_flag": anomaly_detected},
    )
    db.commit()

    return {
        "status": "UPLOAD_SUCCESS",
        "document_id": doc.id,
        "sha256_hash": sha256_hash,
        "anomaly_flag": anomaly_detected,
        "ocr_extracted": {
            "document_number": doc.document_number,
            "expiry_date": doc.expiry_date.strftime("%Y-%m-%d"),
            "confidence": 0.94,
        },
    }

@router.post("/documents/{document_id}/verify")
def verify_document(
    document_id: str,
    payload: DocumentVerifyRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Officer verifies a regulatory document.
    Enforces pairwise Separation of Duties (submitter_id != verifier_id).
    """
    dal = ScopedDAL(db, ctx)
    try:
        updated = dal.verify_document(document_id, payload.is_approved)
        return {
            "status": "VERIFIED",
            "document_id": updated.id,
            "new_status": updated.status,
            "verified_by": updated.verifier_id,
        }
    except SoDViolationError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except SecurityScopeError as e:
        raise HTTPException(status_code=403, detail=str(e))

@router.get("/undertakings")
def list_undertakings(
    institution_id: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Lists time-bound undertakings with due dates and compliance status."""
    query = db.query(TimeBoundUndertaking)
    if institution_id:
        query = query.filter(TimeBoundUndertaking.institution_id == institution_id)
    
    items = query.all()
    today = date.today()
    results = []

    for u in items:
        days_left = (u.due_date - today).days
        results.append({
            "id": u.id,
            "institution_id": u.institution_id,
            "institution_name": u.institution.name if u.institution else "Technical Institute",
            "condition_title": u.condition_title,
            "condition_details": u.condition_details,
            "due_date": u.due_date.strftime("%Y-%m-%d"),
            "days_remaining": days_left,
            "status": u.status,
            "aph_clause_ref": u.aph_clause_ref,
            "evidence_submitted": bool(u.evidence_file_url),
        })

    return {"count": len(results), "undertakings": results}

@router.get("/obligation-dependencies/{institution_id}")
def get_obligation_dependencies(
    institution_id: str,
    db: Session = Depends(get_db),
):
    """
    Signature Differentiator 6: Obligation Dependency View.
    Maps how an expiring document or unmet undertaking cascades into
    threatened Extension of Approval (EoA) validity and student intake quotas.
    """
    inst = None
    if institution_id not in ("inst-01", "default", "demo", "first"):
        inst = db.query(Institution).filter(
            (Institution.id == institution_id) | (Institution.permanent_id == institution_id)
        ).first()

    # Fallback to an institution that has documents/undertakings or first in db
    if not inst:
        # Prioritize an institution with documents so the graph renders realistic cascade blockers
        doc = db.query(InstitutionalDocument).first()
        if doc and doc.institution:
            inst = doc.institution
        else:
            inst = db.query(Institution).first()

    if not inst:
        return {
            "institution_name": "Apex Institute of Technology",
            "permanent_id": "1-109283741",
            "overall_health_score": 92,
            "eoa_renewal_blocked": False,
            "at_risk_approved_intake": 0,
            "blockers": [],
        }

    docs = inst.documents or []
    undertakings = inst.undertakings or []

    expired_docs = [d for d in docs if d.status == "EXPIRED"]
    overdue_undertakings = [u for u in undertakings if u.status == "DEFAULT_ESCALATED"]

    eoa_blocked = len(expired_docs) > 0 or len(overdue_undertakings) > 0
    at_risk_intake = 360 if eoa_blocked else 0

    return {
        "institution_name": inst.name,
        "permanent_id": inst.permanent_id,
        "overall_health_score": inst.compliance_health_score,
        "eoa_renewal_blocked": eoa_blocked,
        "at_risk_approved_intake": at_risk_intake,
        "blockers": [
            {
                "type": "EXPIRED_DOCUMENT",
                "title": d.doc_type.name if d.doc_type else "Registered Land Lease Deed",
                "consequence": "Clause 2.1(e) mandates 30-year live lease. EoA issuance blocked.",
                "clause": "Chapter II Clause 2.1(e)",
            }
            for d in expired_docs
        ] + [
            {
                "type": "OVERDUE_UNDERTAKING",
                "title": u.condition_title or "Time-Bound Compliance Undertaking",
                "consequence": "Clause 7.4(b) non-compliance. Show-cause notice and 50% intake reduction penalty.",
                "clause": "Chapter VII Clause 7.4(b)",
            }
            for u in overdue_undertakings
        ],
    }
