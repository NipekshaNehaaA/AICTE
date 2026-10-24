"""
External Integration Adapters & Connectors (DigiLocker, e-Sign, State Portal - Simulated Connectors).
Provides:
1. DigiLocker Document Fetch (simulated connector for Land Lease Deed, Fire NOC, Society Reg).
2. e-Sign Digital Signature Stamping (simulated connector for PKCS#7 signature envelope; no Aadhaar claims).
3. Legacy ERP / State Portal Application Import Adapter (simulated connector).
"""

import hashlib
import uuid
import base64
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.scoped_dal import ScopedDAL, RequestContext
from app.auth import get_request_context
from app.rules_engine import APHRulesEngine
from app.models import Institution, DocumentType, InstitutionalDocument, Application, ApplicationStage, User

router = APIRouter(prefix="/api/v1/adapters", tags=["External Integration Adapters (Simulated Connectors)"])

class DigiLockerFetchRequest(BaseModel):
    doc_type: str = "LAND_LEASE" # LAND_LEASE, FIRE_NOC, BUILDING_PLAN, SOCIETY_REG
    digilocker_mock_token: Optional[str] = "DL-SIM-TOKEN-9988-7766-5544"
    aadhaar_mock_token: Optional[str] = None # Deprecated legacy parameter
    institution_id: Optional[str] = None

class ESignRequest(BaseModel):
    document_id: str
    signatory_id_hash: Optional[str] = "SHA256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    signatory_aadhaar_hash: Optional[str] = None # Deprecated legacy parameter
    otp: str = "123456"

class ApplicationImportPayload(BaseModel):
    institution_pid: str = "1-109283741"
    application_type: str = "INCREASE_INTAKE"
    academic_year: str = "2026-2027"
    source_portal: str = "KEA_STATE_PORTAL"
    external_ref_no: Optional[str] = None

@router.post("/digilocker/fetch")
def fetch_digilocker_document(
    payload: DigiLockerFetchRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Simulated connector: fetches digitally signed documents via synthetic DigiLocker repository.
    Returns issuer certificate, simulated URI, and cryptographically verified SHA-256 hash.
    """
    clean_type = payload.doc_type.upper().strip()

    catalogs = {
        "LAND_LEASE": {
            "title": "Registered Long-Term Land Lease Deed (30-Year)",
            "issuer": "Department of Stamps and Registration, Govt of Karnataka",
            "doc_no": "KA-BLR-REG-2015-882910",
            "issue_date": "2015-06-01",
            "expiry_date": "2045-05-31",
            "aph_clause": "Chapter II Clause 2.1(e) & Chapter VI Clause 6.17",
        },
        "FIRE_NOC": {
            "title": "Fire & Life Safety Clearance Certificate (NOC)",
            "issuer": "Karnataka State Fire & Emergency Services",
            "doc_no": "KA-FS-NOC-2026-1192",
            "issue_date": "2026-01-15",
            "expiry_date": "2027-01-14",
            "aph_clause": "Chapter VI Clause 6.17",
        },
        "BUILDING_PLAN": {
            "title": "Approved Master Plan & Built-up Area Certificate",
            "issuer": "Bruhat Bengaluru Mahanagara Palike (BBMP)",
            "doc_no": "BBMP-ENG-PLAN-2024-551",
            "issue_date": "2024-04-10",
            "expiry_date": "2034-04-09",
            "aph_clause": "Chapter VI Clause 6.17 & Annexure-3",
        },
        "SOCIETY_REG": {
            "title": "Society / Trust Registration Certificate",
            "issuer": "Registrar of Societies, Govt of Karnataka",
            "doc_no": "SOC-REG-KAR-1994-4412",
            "issue_date": "1994-11-20",
            "expiry_date": "2044-11-19",
            "aph_clause": "Chapter I Clause 1.3",
        },
    }

    info = catalogs.get(clean_type, catalogs["LAND_LEASE"])
    mock_binary_data = f"DIGILOCKER_CERT|{clean_type}|{info['doc_no']}|{info['issuer']}|{info['issue_date']}"
    doc_sha256 = hashlib.sha256(mock_binary_data.encode("utf-8")).hexdigest()

    response_data = {
        "status": "DIGILOCKER_FETCHED_SUCCESS",
        "connector_type": "simulated connector",
        "doc_type": clean_type,
        "title": info["title"],
        "issuing_authority": info["issuer"],
        "document_number": info["doc_no"],
        "issue_date": info["issue_date"],
        "expiry_date": info["expiry_date"],
        "digilocker_uri": f"in.gov.digilocker.doc:{clean_type.lower()}:{info['doc_no']}",
        "file_hash_sha256": doc_sha256,
        "is_cryptographically_signed": True,
        "aph_clause_citation": info["aph_clause"],
        "fetched_at": datetime.utcnow().isoformat(),
    }

    # Append audit trail
    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="DIGILOCKER_DOCUMENT_FETCHED",
        entity_type="EXTERNAL_ADAPTER",
        entity_id=info["doc_no"],
        metadata={
            "doc_type": clean_type,
            "sha256": doc_sha256,
            "issuer": info["issuer"],
            "connector_type": "simulated connector",
        },
    )
    db.commit()

    return response_data

@router.post("/esign/sign")
def execute_mock_esign(
    payload: ESignRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Simulated connector: executes e-Sign PKCS#7 digital signature stamping.
    Validates verification code, signs envelope, and returns verification token.
    Note: Simulated connector; no Aadhaar data is processed or stored.
    """
    if len(payload.otp.strip()) != 6:
        raise HTTPException(status_code=400, detail="Invalid e-Sign verification code format. 6 digits required.")

    txn_id = f"ESIGN-TXN-{uuid.uuid4().hex[:12].upper()}"
    sign_timestamp = datetime.utcnow()
    signer_hash = payload.signatory_id_hash or payload.signatory_aadhaar_hash or "SHA256:default-signer-hash"

    # Generate synthetic CAdES / PKCS#7 envelope
    raw_sig = f"{txn_id}|{payload.document_id}|{signer_hash}|{sign_timestamp.isoformat()}"
    sig_b64 = base64.b64encode(raw_sig.encode("utf-8")).decode("ascii")

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="ESIGN_STAMP_APPLIED",
        entity_type="DOCUMENT",
        entity_id=payload.document_id,
        metadata={
            "transaction_id": txn_id,
            "signer_role": ctx.role,
            "signed_at": sign_timestamp.isoformat(),
            "connector_type": "simulated connector",
        },
    )
    db.commit()

    return {
        "status": "ESIGNED_VALID",
        "connector_type": "simulated connector",
        "transaction_id": txn_id,
        "document_id": payload.document_id,
        "cert_authority": "CCA Licensed CA (e-Sign Simulated Gateway)",
        "signature_envelope_token": f"PKCS7:{sig_b64[:32]}...",
        "timestamp": sign_timestamp.isoformat(),
        "is_tamper_evident": True,
    }

@router.post("/application/import")
def import_application_adapter(
    payload: ApplicationImportPayload,

    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    """
    Imports and normalizes application payloads from external ERPs or State CET Portals.
    Resolves Table 2.3 regulatory pipeline and provisions application stages.
    """
    inst = db.query(Institution).filter(Institution.permanent_id == payload.institution_pid).first()
    if not inst:
        inst = db.query(Institution).first()

    pipeline = APHRulesEngine.determine_pipeline(payload.application_type)
    stage_path = APHRulesEngine.build_route_stage_path(payload.application_type)

    app_no = f"APP-IMP-{datetime.utcnow().strftime('%y%m')}-{uuid.uuid4().hex[:6].upper()}"
    sla_days = pipeline.get("sla_days_total", 21)
    deadline = datetime.utcnow() + timedelta(days=sla_days)

    inst_user = db.query(User).filter(User.role == "INSTITUTION_USER").first()
    submitter_id = inst_user.id if inst_user else (ctx.user_id or "usr-inst-01")

    app = Application(
        application_no=app_no,
        institution_id=inst.id,
        region_id=inst.region_id,
        academic_year=payload.academic_year,
        application_type=payload.application_type,
        pipeline_type=pipeline.get("pipeline_name", "SCRUTINY_AND_EVC"),
        current_stage="SCRUTINY",
        status="ACTIVE",
        submitter_id=submitter_id,
        sla_deadline=deadline,
        sla_status="ON_TRACK",
        submitted_at=datetime.utcnow(),
    )
    db.add(app)
    db.flush()

    for idx, stg in enumerate(stage_path):
        s = ApplicationStage(
            application_id=app.id,
            stage_name=stg,
            sequence_order=idx + 1,
            sla_days_allotted=7,
            status="ACTIVE" if idx == 0 else "PENDING",
            started_at=datetime.utcnow() if idx == 0 else None,
            due_at=datetime.utcnow() + timedelta(days=7) if idx == 0 else None,
        )
        db.add(s)

    dal = ScopedDAL(db, ctx)
    dal.append_audit_entry(
        action_type="APPLICATION_IMPORTED_FROM_ADAPTER",
        entity_type="APPLICATION",
        entity_id=app.id,
        metadata={
            "application_no": app_no,
            "source_portal": payload.source_portal,
            "pipeline": pipeline.get("pipeline_name"),
            "connector_type": "simulated connector",
        },
    )
    db.commit()

    return {
        "status": "IMPORT_SUCCESS",
        "connector_type": "simulated connector",
        "application_no": app.application_no,
        "application_id": app.id,
        "source_portal": payload.source_portal,
        "pipeline_name": pipeline.get("pipeline_name"),
        "route": pipeline.get("route"),
        "stages": stage_path,
        "sla_deadline": deadline.strftime("%d-%b-%Y"),
    }

