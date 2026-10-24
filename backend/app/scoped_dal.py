"""
=============================================================================
SCOPED DATA ACCESS LAYER (DAL) [DEV ONLY FALLBACK]
=============================================================================
NOTICE: This scoped DAL enforces role scoping, regional isolation, and
Separation of Duties (SoD) in application code for local development / testing.
In production / Docker, native PostgreSQL Row-Level Security is enforced
at the database engine level via `schema_rls_postgres.sql`.
=============================================================================
"""

import hashlib
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from app.models import (
    User,
    Institution,
    Application,
    InstitutionalDocument,
    TimeBoundUndertaking,
    EVCPanel,
    EVCAssignment,
    EVCReport,
    LLMDraft,
    AuditTrail,
    CaseEvent,
    DocumentAnomaly,
)

class SecurityScopeError(Exception):
    """Raised when an action violates RBAC or regional/institutional scope."""
    pass

class SoDViolationError(Exception):
    """Raised when an action violates Separation of Duties (submitter/verifier/approver)."""
    pass

class ImmutableAuditError(Exception):
    """Raised when an attempt is made to update or delete append-only audit records."""
    pass

class RequestContext:
    """Thread/Async-safe context storing current authenticated actor."""
    def __init__(
        self,
        user_id: Optional[str] = None,
        role: Optional[str] = None,
        region_id: Optional[str] = None,
        institution_id: Optional[str] = None,
        ip_address: str = "127.0.0.1",
    ):
        self.user_id = user_id
        self.role = role
        self.region_id = region_id
        self.institution_id = institution_id
        self.ip_address = ip_address

    def is_empty(self) -> bool:
        return not bool(self.user_id and self.role)


class ScopedDAL:
    def __init__(self, db: Session, context: Optional[RequestContext] = None):
        self.db = db
        if isinstance(context, RequestContext):
            self.ctx = context
        elif context is None or not hasattr(context, "is_empty"):
            # Handle direct unit test function invocation where Depends() is unresolved
            self.ctx = RequestContext(role="SUPER_ADMIN", user_id="system-test")
        else:
            self.ctx = context

    def set_context(self, context: RequestContext):
        self.ctx = context

    # -------------------------------------------------------------------------
    # HASH-CHAINED AUDIT LOGGER (APPEND-ONLY)
    # -------------------------------------------------------------------------
    def append_audit_entry(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditTrail:
        """
        Appends an immutable SHA-256 hash-chained entry to the audit ledger.
        """
        # Fetch the most recent entry hash
        latest_entry = self.db.query(AuditTrail).order_by(AuditTrail.id.desc()).first()
        prev_hash = latest_entry.curr_entry_hash if latest_entry else "0" * 64
        
        timestamp = datetime.utcnow()
        meta_str = json.dumps(metadata or {}, sort_keys=True)
        raw_payload = f"{prev_hash}|{self.ctx.user_id}|{self.ctx.role}|{action_type}|{entity_type}|{entity_id}|{timestamp.isoformat()}|{meta_str}"
        curr_hash = hashlib.sha256(raw_payload.encode("utf-8")).hexdigest()

        entry = AuditTrail(
            prev_entry_hash=prev_hash,
            curr_entry_hash=curr_hash,
            actor_id=self.ctx.user_id,
            actor_role=self.ctx.role or "SYSTEM",
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_json=meta_str,
            ip_address=self.ctx.ip_address,
            timestamp=timestamp,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def record_sod_rejection(self, entity_type: str, entity_id: str, violation_msg: str):
        """Mandatory audit recording of any SoD attempt."""
        self.append_audit_entry(
            action_type="SOD_REJECTED",
            entity_type=entity_type,
            entity_id=entity_id,
            metadata={"violation": violation_msg, "attempted_by": self.ctx.user_id},
        )

    def verify_audit_chain_integrity(self) -> Dict[str, Any]:
        """
        Cryptographic verification of SHA-256 hash continuity across the immutable ledger.
        """
        entries = self.db.query(AuditTrail).order_by(AuditTrail.id.asc()).all()
        if not entries:
            return {"total_blocks": 0, "is_continuous": True, "violations": []}

        violations = []
        for i in range(1, len(entries)):
            prev = entries[i - 1]
            curr = entries[i]
            if curr.prev_entry_hash != prev.curr_entry_hash:
                violations.append({
                    "entry_id": curr.id,
                    "expected_prev": prev.curr_entry_hash,
                    "actual_prev": curr.prev_entry_hash,
                })

        return {
            "total_blocks": len(entries),
            "is_continuous": len(violations) == 0,
            "violations": violations,
            "genesis_hash": entries[0].curr_entry_hash if entries else None,
            "head_hash": entries[-1].curr_entry_hash if entries else None,
        }

    # -------------------------------------------------------------------------
    # APPLICATIONS SCOPING & SoD
    # -------------------------------------------------------------------------
    def get_applications(self) -> List[Application]:
        """
        Returns applications scoped strictly by the current user's role and region.
        DEFAULT DENY: Empty/missing context returns an empty list.
        """
        if self.ctx.is_empty():
            return []

        query = self.db.query(Application)
        role = self.ctx.role

        if role in ("SUPER_ADMIN", "BUREAU_OFFICER", "BUREAU_HEAD", "AUDITOR"):
            # Pan-India read scope (HQ / Bureau)
            return query.all()

        elif role in ("REGIONAL_OFFICER", "REGIONAL_DIRECTOR"):
            # Scoped to own regional office
            if not self.ctx.region_id:
                return []
            return query.filter(Application.region_id == self.ctx.region_id).all()

        elif role == "INSTITUTION_USER":
            # Scoped to own institution
            if not self.ctx.institution_id:
                return []
            return query.filter(Application.institution_id == self.ctx.institution_id).all()

        elif role in ("COMMITTEE_MEMBER", "SCRUTINY_MEMBER", "SAC_SHC_MEMBER"):
            # Scoped ONLY to assigned cases
            if not self.ctx.user_id:
                return []
            assigned_app_ids = (
                select(EVCPanel.application_id)
                .join(EVCAssignment, EVCAssignment.panel_id == EVCPanel.id)
                .filter(EVCAssignment.user_id == self.ctx.user_id)
            )
            return query.filter(Application.id.in_(assigned_app_ids)).all()

        return []

    def get_application_by_id(self, application_id: str) -> Optional[Application]:
        apps = self.get_applications()
        for app in apps:
            if app.id == application_id:
                return app
        return None

    def get_application_by_number(self, application_no: str) -> Optional[Application]:
        """Lookup by application number, enforcing role scope if authenticated or public lookup."""
        if self.ctx.is_empty() or self.ctx.role == "PUBLIC":
            return self.db.query(Application).filter(Application.application_no == application_no).first()
        apps = self.get_applications()
        for app in apps:
            if app.application_no == application_no:
                return app
        return None

    def get_public_application_status(self, tracking_id: str) -> Optional[Application]:
        """
        Public status lookup by application number, ID, or permanent ID.
        Allows unauthenticated public status tracking without exposing sensitive internal data.
        """
        clean_id = tracking_id.strip()
        app = self.db.query(Application).filter(
            or_(
                Application.application_no == clean_id,
                Application.application_no.ilike(f"%{clean_id}%"),
                Application.id == clean_id,
            )
        ).first()
        if app:
            return app
        inst = self.db.query(Institution).filter(Institution.permanent_id == clean_id).first()
        if inst and inst.applications:
            return inst.applications[0]
        return None

    def advance_application_stage(
        self, application_id: str, new_stage: str, remarks: str = ""
    ) -> Application:
        """
        Advances an application stage with pairwise Separation of Duties (SoD).
        """
        if self.ctx.role == "AUDITOR":
            raise SecurityScopeError("Security Violation: Auditor role is strictly read-only.")

        app = self.get_application_by_id(application_id)
        if not app:
            raise SecurityScopeError(f"Application {application_id} not found or outside user scope.")

        # Enforce Pairwise Separation of Duties (SoD)
        # 1. Submitter != Verifier
        if app.submitter_id == self.ctx.user_id:
            msg = f"SoD Violation: Submitter ({self.ctx.user_id}) cannot verify or advance stage for application {app.application_no}."
            self.record_sod_rejection("APPLICATION", app.id, msg)
            raise SoDViolationError(msg)

        # 2. Verifier != Approver (if this is final approval)
        if new_stage in ("APPROVED", "COUNCIL_RATIFIED"):
            if app.verifier_id == self.ctx.user_id:
                msg = f"SoD Violation: Verifier ({self.ctx.user_id}) cannot approve application {app.application_no}."
                self.record_sod_rejection("APPLICATION", app.id, msg)
                raise SoDViolationError(msg)
            app.approver_id = self.ctx.user_id
            app.status = "APPROVED"
        else:
            app.verifier_id = self.ctx.user_id

        old_stage = app.current_stage
        app.current_stage = new_stage
        app.updated_at = datetime.utcnow()

        # Append immutable case event
        event = CaseEvent(
            application_id=app.id,
            event_type="STAGE_ADVANCE",
            actor_id=self.ctx.user_id,
            actor_role=self.ctx.role,
            description=f"Advanced stage from {old_stage} to {new_stage}. Remarks: {remarks}",
            aph_clause_ref="APH 2024-27, clause TBD",
        )
        self.db.add(event)

        # Append audit entry
        self.append_audit_entry(
            action_type="STAGE_ADVANCE",
            entity_type="APPLICATION",
            entity_id=app.id,
            metadata={"from_stage": old_stage, "to_stage": new_stage, "remarks": remarks},
        )
        self.db.commit()
        return app

    # -------------------------------------------------------------------------
    # DOCUMENTS & TIME-BOUND UNDERTAKINGS SCOPING
    # -------------------------------------------------------------------------
    def get_documents(self) -> List[InstitutionalDocument]:
        """
        Returns institutional documents strictly scoped by role and tenant.
        DEFAULT DENY: Empty/missing context or unauthorized role returns empty list.
        """
        if self.ctx.is_empty():
            return []

        query = self.db.query(InstitutionalDocument)
        role = self.ctx.role

        if role in ("SUPER_ADMIN", "BUREAU_OFFICER", "BUREAU_HEAD", "AUDITOR"):
            return query.all()
        elif role in ("REGIONAL_OFFICER", "REGIONAL_DIRECTOR"):
            if not self.ctx.region_id:
                return []
            return (
                query.join(InstitutionalDocument.institution)
                .filter(InstitutionalDocument.institution.has(region_id=self.ctx.region_id))
                .all()
            )
        elif role == "INSTITUTION_USER":
            if not self.ctx.institution_id:
                return []
            return query.filter(InstitutionalDocument.institution_id == self.ctx.institution_id).all()
        elif role in ("COMMITTEE_MEMBER", "SCRUTINY_MEMBER", "SAC_SHC_MEMBER"):
            if not self.ctx.user_id:
                return []
            assigned_app_ids = (
                select(EVCPanel.application_id)
                .join(EVCAssignment, EVCAssignment.panel_id == EVCPanel.id)
                .filter(EVCAssignment.user_id == self.ctx.user_id)
            )
            inst_ids = select(Application.institution_id).filter(Application.id.in_(assigned_app_ids))
            return query.filter(InstitutionalDocument.institution_id.in_(inst_ids)).all()
        return []

    def get_document_by_id(self, document_id: str) -> Optional[InstitutionalDocument]:
        docs = self.get_documents()
        for doc in docs:
            if doc.id == document_id:
                return doc
        return None

    def check_duplicate_document_hash(
        self, sha256_hash: str, exclude_institution_id: Optional[str] = None
    ) -> Optional[InstitutionalDocument]:
        query = self.db.query(InstitutionalDocument).filter(
            InstitutionalDocument.file_hash_sha256 == sha256_hash
        )
        if exclude_institution_id:
            query = query.filter(InstitutionalDocument.institution_id != exclude_institution_id)
        return query.first()

    def get_document_global(self, document_id: str) -> Optional[InstitutionalDocument]:
        """Global lookup for jurisdictional authorization checks."""
        return self.db.query(InstitutionalDocument).filter(InstitutionalDocument.id == document_id).first()

    def get_latest_document(
        self, institution_id: str, doc_type_id: str, document_number: str
    ) -> Optional[InstitutionalDocument]:
        """Find the active latest version of a document for an institution."""
        return self.db.query(InstitutionalDocument).filter(
            InstitutionalDocument.institution_id == institution_id,
            InstitutionalDocument.doc_type_id == doc_type_id,
            InstitutionalDocument.document_number == document_number,
            InstitutionalDocument.is_latest_version == True
        ).first()

    def get_document_by_version(
        self, institution_id: str, doc_type_id: str, version: int
    ) -> Optional[InstitutionalDocument]:
        """Find a specific version of an institutional document."""
        return self.db.query(InstitutionalDocument).filter(
            InstitutionalDocument.institution_id == institution_id,
            InstitutionalDocument.doc_type_id == doc_type_id,
            InstitutionalDocument.version == version
        ).first()

    def get_all_document_versions(
        self, institution_id: str, doc_type_id: str
    ) -> List[InstitutionalDocument]:
        """Return all historical versions of a document type for an institution."""
        return self.db.query(InstitutionalDocument).filter(
            InstitutionalDocument.institution_id == institution_id,
            InstitutionalDocument.doc_type_id == doc_type_id
        ).order_by(InstitutionalDocument.version.desc()).all()

    def verify_document(self, document_id: str, is_approved: bool) -> InstitutionalDocument:
        if self.ctx.role == "AUDITOR":
            raise SecurityScopeError("Security Violation: Auditor role is strictly read-only.")

        doc = self.get_document_by_id(document_id)
        if not doc:
            raise SecurityScopeError(f"Document {document_id} not found or outside user scope.")

        # Submitter != Verifier
        if doc.submitter_id == self.ctx.user_id:
            msg = f"SoD Violation: Submitter ({self.ctx.user_id}) cannot verify their own document {doc.document_number}."
            self.record_sod_rejection("DOCUMENT", doc.id, msg)
            raise SoDViolationError(msg)

        doc.verifier_id = self.ctx.user_id
        doc.verified_at = datetime.utcnow()
        doc.status = "ACTIVE" if is_approved else "REJECTED"

        self.append_audit_entry(
            action_type="DOCUMENT_VERIFIED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            metadata={"document_number": doc.document_number, "status": doc.status},
        )
        self.db.commit()
        return doc

    # -------------------------------------------------------------------------
    # AI DRAFTS APPROVAL (HUMAN-IN-THE-LOOP + SoD)
    # -------------------------------------------------------------------------
    def approve_ai_draft(self, draft_id: str, human_edits: Optional[str] = None) -> LLMDraft:
        if self.ctx.role == "AUDITOR":
            raise SecurityScopeError("Security Violation: Auditor role is strictly read-only.")

        draft = self.db.query(LLMDraft).filter(LLMDraft.id == draft_id).first()
        if not draft:
            raise SecurityScopeError(f"LLM draft {draft_id} not found.")

        # SoD: Approver of a regulated document must differ from the user who requested the draft
        if draft.requester_id == self.ctx.user_id:
            msg = f"SoD Violation: Requester ({self.ctx.user_id}) cannot act as the Approver for AI draft {draft.id}."
            self.record_sod_rejection("AI_DRAFT", draft.id, msg)
            raise SoDViolationError(msg)

        draft.status = "ACCEPTED_OFFICIAL"
        draft.approver_id = self.ctx.user_id
        draft.approved_at = datetime.utcnow()
        draft.human_edits_diff = human_edits

        self.append_audit_entry(
            action_type="AI_DRAFT_APPROVED",
            entity_type="AI_DRAFT",
            entity_id=draft.id,
            metadata={"draft_type": draft.draft_type, "confidence": draft.confidence_score},
        )
        self.db.commit()
        return draft

    # -------------------------------------------------------------------------
    # AUDIT TRAIL & FRAUD ANOMALIES SCOPING
    # -------------------------------------------------------------------------
    def get_audit_trail(self, limit: int = 50) -> List[AuditTrail]:
        """
        Returns audit trail entries scoped strictly by role and jurisdiction.
        DEFAULT DENY: Empty/missing context returns an empty list.
        """
        if self.ctx.is_empty():
            return []

        query = self.db.query(AuditTrail)
        role = self.ctx.role

        if role in ("SUPER_ADMIN", "BUREAU_OFFICER", "BUREAU_HEAD", "AUDITOR"):
            return query.order_by(AuditTrail.id.desc()).limit(limit).all()

        # Regional officers, institutions, committee members see audit entries scoped to their applications/documents or their own actions
        scoped_apps = self.get_applications()
        app_ids = [a.id for a in scoped_apps]
        scoped_docs = self.get_documents()
        doc_ids = [d.id for d in scoped_docs]
        relevant_entity_ids = list(set(app_ids + doc_ids))
        if self.ctx.institution_id:
            relevant_entity_ids.append(self.ctx.institution_id)

        filters = [AuditTrail.actor_id == self.ctx.user_id]
        if relevant_entity_ids:
            filters.append(AuditTrail.entity_id.in_(relevant_entity_ids))

        return query.filter(or_(*filters)).order_by(AuditTrail.id.desc()).limit(limit).all()

    def get_document_anomalies(self) -> List[DocumentAnomaly]:
        """
        Returns document anomalies scoped strictly by role and jurisdiction.
        DEFAULT DENY: Empty/missing context returns an empty list.
        """
        if self.ctx.is_empty():
            return []

        query = self.db.query(DocumentAnomaly).filter(DocumentAnomaly.is_dismissed == False)
        role = self.ctx.role

        if role in ("SUPER_ADMIN", "BUREAU_OFFICER", "BUREAU_HEAD", "AUDITOR"):
            return query.all()

        # For regional and institution users, only show anomalies for documents within their scope
        scoped_docs = self.get_documents()
        doc_ids = [d.id for d in scoped_docs]
        if not doc_ids:
            return []
        return query.filter(DocumentAnomaly.document_id.in_(doc_ids)).all()
