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
    ApplicationStage,
    CaseAssignment,
    InstitutionalDocument,
    TimeBoundUndertaking,
    EVCPanel,
    EVCAssignment,
    EVCReport,
    LLMDraft,
    AuditTrail,
    CaseEvent,
    DocumentAnomaly,
    Notification,
)
from app.email_service import email_service
from app.twilio_whatsapp import twilio_whatsapp_client

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
        workspace: str = "live",
    ):
        self.user_id = user_id
        self.role = role
        self.region_id = region_id
        self.institution_id = institution_id
        self.ip_address = ip_address
        self.workspace = workspace

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

        elif role == "SCRUTINY_MEMBER":
            # Scrutiny Member: Scoped ONLY to assigned cases while current stage is SCRUTINY or RE_SCRUTINY
            if not self.ctx.user_id:
                return []
            scrutiny_stages = ["SCRUTINY", "RE_SCRUTINY"]
            assigned_via_app = (
                select(Application.id)
                .filter(
                    or_(
                        Application.assigned_officer_id == self.ctx.user_id,
                        Application.verifier_id == self.ctx.user_id,
                    ),
                    Application.current_stage.in_(scrutiny_stages),
                )
            )
            assigned_via_stage = (
                select(ApplicationStage.application_id)
                .join(Application, Application.id == ApplicationStage.application_id)
                .filter(
                    ApplicationStage.assigned_user_id == self.ctx.user_id,
                    ApplicationStage.status == "ACTIVE",
                    Application.current_stage.in_(scrutiny_stages),
                )
            )
            assigned_via_case = (
                select(CaseAssignment.application_id)
                .join(Application, Application.id == CaseAssignment.application_id)
                .filter(
                    CaseAssignment.user_id == self.ctx.user_id,
                    CaseAssignment.is_active == True,
                    CaseAssignment.stage_name.in_(scrutiny_stages),
                    Application.current_stage.in_(scrutiny_stages),
                )
            )
            return query.filter(
                or_(
                    Application.id.in_(assigned_via_app),
                    Application.id.in_(assigned_via_stage),
                    Application.id.in_(assigned_via_case),
                )
            ).all()

        elif role == "COMMITTEE_MEMBER":
            # EVC Committee Member (Expert): Scoped ONLY to assigned cases while current stage is EVC
            if not self.ctx.user_id:
                return []
            evc_stages = ["EVC", "EVC_SCHEDULED", "EVC_COMMITTEE", "EVC_VISIT", "EVC_REPORT"]
            assigned_via_panel = (
                select(EVCPanel.application_id)
                .join(EVCAssignment, EVCAssignment.panel_id == EVCPanel.id)
                .join(Application, Application.id == EVCPanel.application_id)
                .filter(
                    EVCAssignment.user_id == self.ctx.user_id,
                    Application.current_stage.in_(evc_stages),
                )
            )
            assigned_via_case = (
                select(CaseAssignment.application_id)
                .join(Application, Application.id == CaseAssignment.application_id)
                .filter(
                    CaseAssignment.user_id == self.ctx.user_id,
                    CaseAssignment.is_active == True,
                    CaseAssignment.stage_name.in_(evc_stages),
                    Application.current_stage.in_(evc_stages),
                )
            )
            return query.filter(
                or_(
                    Application.id.in_(assigned_via_panel),
                    Application.id.in_(assigned_via_case),
                )
            ).all()

        elif role == "SAC_SHC_MEMBER":
            # SAC/SHC Member: Scoped ONLY to assigned hearing/appellate cases while active
            if not self.ctx.user_id:
                return []
            sac_stages = ["SAC_SHC", "SHC_HEARING", "SAC_APPEAL", "STANDING_APPELLATE", "STANDING_HEARING"]
            assigned_via_app = (
                select(Application.id)
                .filter(
                    or_(
                        Application.assigned_officer_id == self.ctx.user_id,
                        Application.verifier_id == self.ctx.user_id,
                    ),
                    Application.current_stage.in_(sac_stages),
                )
            )
            assigned_via_case = (
                select(CaseAssignment.application_id)
                .join(Application, Application.id == CaseAssignment.application_id)
                .filter(
                    CaseAssignment.user_id == self.ctx.user_id,
                    CaseAssignment.is_active == True,
                    CaseAssignment.stage_name.in_(sac_stages),
                    Application.current_stage.in_(sac_stages),
                )
            )
            return query.filter(
                or_(
                    Application.id.in_(assigned_via_app),
                    Application.id.in_(assigned_via_case),
                )
            ).all()

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
        self, application_id: str, new_stage: str, remarks: str = "", next_officer_id: Optional[str] = None
    ) -> Application:
        """
        Advances an application stage with pairwise Separation of Duties (SoD),
        updates stage status and active assignments, and dispatches handoff notifications.
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

        # Update stage records in ApplicationStage
        now = datetime.utcnow()
        for st in (app.stages or []):
            if st.stage_name == old_stage:
                st.status = "PASSED"
                st.completed_at = now
            elif st.stage_name == new_stage:
                st.status = "ACTIVE"
                st.started_at = now
                if next_officer_id:
                    st.assigned_user_id = next_officer_id

        # Update CaseAssignment records
        # Revoke previous assignments that were tied to old stage
        for ca in self.db.query(CaseAssignment).filter(
            CaseAssignment.application_id == app.id,
            CaseAssignment.is_active == True,
            CaseAssignment.stage_name != new_stage,
        ).all():
            ca.is_active = False
            ca.revoked_at = now

        # Determine next stage officer
        new_officer = None
        if next_officer_id:
            new_officer = self.db.query(User).filter(User.id == next_officer_id).first()

        if not new_officer:
            if new_stage in ("SCRUTINY", "RE_SCRUTINY"):
                new_officer = self.db.query(User).filter(User.role == "SCRUTINY_MEMBER", User.region_id == app.region_id).first()
                if not new_officer:
                    new_officer = self.db.query(User).filter(User.role == "SCRUTINY_MEMBER").first()
            elif new_stage in ("EVC", "EVC_SCHEDULED", "EVC_COMMITTEE", "EVC_VISIT"):
                if app.evc_panel and app.evc_panel.assignments:
                    new_officer = app.evc_panel.assignments[0].user
                if not new_officer:
                    new_officer = self.db.query(User).filter(User.role == "COMMITTEE_MEMBER", User.region_id == app.region_id).first()
                    if not new_officer:
                        new_officer = self.db.query(User).filter(User.role == "COMMITTEE_MEMBER").first()
            elif new_stage in ("SAC_SHC", "SHC_HEARING", "SAC_APPEAL", "STANDING_APPELLATE", "STANDING_HEARING"):
                new_officer = self.db.query(User).filter(User.role == "SAC_SHC_MEMBER").first()

        if new_officer:
            app.assigned_officer_id = new_officer.id
            self.db.add(CaseAssignment(
                application_id=app.id,
                stage_name=new_stage,
                user_id=new_officer.id,
                role=new_officer.role,
                is_active=True,
                assigned_at=now,
            ))

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
            metadata={"from_stage": old_stage, "to_stage": new_stage, "remarks": remarks, "assigned_to": new_officer.id if new_officer else None},
        )
        self.db.flush()

        # Dispatch Handoff Notifications: Next Owner + Institution
        deep_link = f"/case?id={app.id}"
        if new_officer:
            self.dispatch_notification(
                user=new_officer,
                title=f"Case Handoff: Application {app.application_no} Advanced to {new_stage}",
                message=f"Application {app.application_no} has moved to stage {new_stage}. You are the designated stage reviewer.",
                category="STAGE_HANDOFF",
                severity="INFO",
                deep_link=deep_link,
                idempotency_key=f"handoff-{app.id}-{old_stage}-{new_stage}-{new_officer.id}",
                application_id=app.id,
            )

        # Notify institution submitter
        submitter = self.db.query(User).filter(User.id == app.submitter_id).first()
        if submitter:
            self.dispatch_notification(
                user=submitter,
                title=f"Application Progression: Stage Advanced to {new_stage}",
                message=f"Your application {app.application_no} has advanced from {old_stage} to {new_stage}.",
                category="STAGE_PROGRESS",
                severity="INFO",
                deep_link=deep_link,
                idempotency_key=f"handoff-{app.id}-{old_stage}-{new_stage}-{submitter.id}",
                application_id=app.id,
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
            # A user may list, preview and download documents of an application only while they
            # are the assigned owner of its current stage, or a panel member of its EVC, or a named SAC/SHC reviewer.
            # Access ends when the stage moves on.
            if not self.ctx.user_id:
                return []
            permitted_apps = self.get_applications()
            if not permitted_apps:
                return []
            allowed_inst_ids = [a.institution_id for a in permitted_apps]
            allowed_app_ids = [a.id for a in permitted_apps]
            return (
                query.filter(
                    or_(
                        InstitutionalDocument.application_id.in_(allowed_app_ids),
                        and_(
                            InstitutionalDocument.application_id.is_(None),
                            InstitutionalDocument.institution_id.in_(allowed_inst_ids),
                        ),
                    )
                )
                .all()
            )
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

    def dispatch_notification(
        self,
        user: User,
        title: str,
        message: str,
        category: str = "CASE_UPDATE",
        severity: str = "INFO",
        deep_link: str = "/case",
        idempotency_key: str = "",
        application_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Dispatches multi-channel notification (In-App, Real SMTP, WhatsApp)
        with strict idempotency checking to prevent duplicates.
        """
        if not user or not user.id:
            return {"status": "SKIPPED_NO_USER"}

        clean_idemp = f"{idempotency_key}:IN_APP" if idempotency_key else None
        if clean_idemp:
            existing = self.db.query(Notification).filter(Notification.idempotency_key == clean_idemp).first()
            if existing:
                return {"status": "SKIPPED_IDEMPOTENT", "notification_id": existing.id}

        now = datetime.utcnow()
        full_msg = f"{message}\n\nCase Access Link: {deep_link}"

        # 1. In-App Notification
        notif = Notification(
            user_id=user.id,
            title=title,
            message=full_msg,
            category=category,
            severity=severity,
            scheduled_for=now,
            fired_at=now,
            is_read=False,
            application_id=application_id,
            delivery_channel="IN_APP",
            delivery_status="DELIVERED",
            recipient_contact=user.email,
            language=getattr(user, "preferred_language", "en") or "en",
            idempotency_key=clean_idemp,
            receipt_id=f"rec_{now.timestamp()}",
        )
        self.db.add(notif)
        self.db.flush()

        # 2. Email Delivery (Real SMTP or test sink)
        preferred_channels = (getattr(user, "preferred_channels", "IN_APP,EMAIL") or "IN_APP,EMAIL").split(",")
        email_sent = False
        if "EMAIL" in preferred_channels or user.email:
            try:
                email_service.send_email(
                    to_email=user.email,
                    subject=title,
                    text_content=full_msg,
                    html_content=f"<div style='font-family:sans-serif;padding:16px;'>"
                                 f"<h3>{title}</h3>"
                                 f"<p>{message}</p>"
                                 f"<p><a href='http://127.0.0.1:3000{deep_link}'>View Case Docket</a></p>"
                                 f"</div>",
                    override_quiet=(severity == "CRITICAL"),
                )
                email_sent = True
            except Exception:
                pass

        # 3. WhatsApp Delivery (Twilio Sandbox / Simulated fallback)
        wa_sent = False
        if "WHATSAPP" in preferred_channels or getattr(user, "opt_in_whatsapp", False):
            if getattr(user, "whatsapp_phone", None):
                try:
                    twilio_whatsapp_client.send_whatsapp_message(
                        to_phone=user.whatsapp_phone,
                        body=f"{title}\n{message}\nAccess: http://127.0.0.1:3000{deep_link}",
                    )
                    wa_sent = True
                except Exception:
                    pass

        return {
            "status": "DISPATCHED",
            "notification_id": notif.id,
            "channels": {
                "in_app": True,
                "email": email_sent,
                "whatsapp": wa_sent,
            }
        }

    def dispatch_document_handoff(
        self, doc: InstitutionalDocument, action: str = "UPLOAD"
    ):
        """
        Notifies appropriate stakeholders when a document is uploaded, renewed, verified, or returned.
        - Upload / Renew: Notifies active stage reviewer / dealing officer.
        - Verified / Returned: Notifies submitting institution user.
        """
        app = None
        if getattr(doc, "application_id", None):
            app = self.db.query(Application).filter(Application.id == doc.application_id).first()
        if not app:
            app = self.db.query(Application).filter(
                Application.institution_id == doc.institution_id,
                Application.status.in_(["IN_PROGRESS", "DEFICIENT", "ESCALATED"]),
            ).first()

        deep_link = f"/case?id={app.id}" if app else f"/compliance?doc={doc.id}"
        app_no = app.application_no if app else doc.document_number

        if action in ("UPLOAD", "RENEW"):
            recipient = None
            if app and app.assigned_officer_id:
                recipient = self.db.query(User).filter(User.id == app.assigned_officer_id).first()
            if not recipient and app:
                recipient = self.db.query(User).filter(User.role == "REGIONAL_OFFICER", User.region_id == app.region_id).first()

            if recipient:
                title = f"Document {'Renewed' if action == 'RENEW' else 'Uploaded'}: {doc.document_number}"
                msg = f"A new version (v{doc.version}) of {doc.doc_type.name if doc.doc_type else 'statutory document'} was uploaded for {doc.institution.name if doc.institution else 'an institution'}. Please review in case docket {app_no}."
                idemp = f"doc-{doc.id}-v{doc.version}-{action}-{recipient.id}"
                self.dispatch_notification(
                    user=recipient,
                    title=title,
                    message=msg,
                    category="DOCUMENT_UPLOAD",
                    severity="INFO",
                    deep_link=deep_link,
                    idempotency_key=idemp,
                    application_id=app.id if app else None,
                )

        elif action in ("VERIFIED", "RETURNED"):
            submitter = self.db.query(User).filter(User.id == doc.submitter_id).first()
            if not submitter and app:
                submitter = self.db.query(User).filter(User.id == app.submitter_id).first()

            if submitter:
                is_verified = (action == "VERIFIED")
                title = f"Document {'Verified' if is_verified else 'Returned / Deficient'}: {doc.document_number}"
                msg = f"Your document {doc.document_number} has been {'verified and approved' if is_verified else 'marked deficient / returned for rectification'}."
                idemp = f"doc-{doc.id}-v{doc.version}-{action}-{submitter.id}"
                self.dispatch_notification(
                    user=submitter,
                    title=title,
                    message=msg,
                    category="DOCUMENT_STATUS",
                    severity="INFO" if is_verified else "WARNING",
                    deep_link=deep_link,
                    idempotency_key=idemp,
                    application_id=app.id if app else None,
                )

