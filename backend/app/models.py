"""
SQLAlchemy ORM models for the AICTE Approval Workflow & Compliance System.
Enforces separation of duties, role scoping, immutable audit trail, and APH provenance.
"""

from datetime import datetime
import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

def generate_uuid() -> str:
    return str(uuid.uuid4())

# ============================================================================
# 1. REGIONS & INSTITUTIONS
# ============================================================================
class Region(Base):
    """
    Configurable AICTE Regional Offices.
    Sample list, configurable. HQ is NOT a region (HQ is Bureau/Council scope).
    """
    __tablename__ = "regions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(10), unique=True, nullable=False) # e.g. SWRO, SRO, WRO, NRO, ERO, CRO, NWRO
    name = Column(String(150), nullable=False)
    city = Column(String(100), nullable=False)
    jurisdiction_states = Column(Text, nullable=True) # JSON list of states
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    institutions = relationship("Institution", back_populates="region")
    users = relationship("User", back_populates="region")
    applications = relationship("Application", back_populates="region")


class Institution(Base):
    """
    Technical Institutions (Engineering, Management, Pharmacy, etc.)
    All demo data is labeled synthetic.
    """
    __tablename__ = "institutions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    permanent_id = Column(String(50), unique=True, nullable=False, index=True) # e.g. 1-109283741
    name = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    state = Column(String(100), nullable=False)
    region_id = Column(String(36), ForeignKey("regions.id"), nullable=False, index=True)
    category = Column(String(100), nullable=False) # Engineering & Tech, Management, etc.
    status = Column(String(50), default="ACTIVE") # ACTIVE, SUSPENDED, DEFICIENT
    compliance_health_score = Column(Float, default=100.0) # 0 to 100
    is_synthetic = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    region = relationship("Region", back_populates="institutions")
    users = relationship("User", back_populates="institution")
    applications = relationship("Application", back_populates="institution")
    documents = relationship("InstitutionalDocument", back_populates="institution")
    undertakings = relationship("TimeBoundUndertaking", back_populates="institution")


# ============================================================================
# 2. USERS, ROLES, AND AUTHENTICATION
# ============================================================================
class User(Base):
    """
    System Users with RBAC and Regional/Institutional Scope.
    Roles:
      - INSTITUTION_USER: Restricted to own institution
      - REGIONAL_OFFICER: Restricted to own region
      - COMMITTEE_MEMBER: Restricted to assigned cases
      - BUREAU_OFFICER / SUPER_ADMIN: Pan-India read; cannot approve own cases (SoD)
      - AUDITOR: Read-only everywhere (no write access)
    """
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(150), nullable=False)
    role = Column(String(50), nullable=False, index=True) # INSTITUTION_USER, REGIONAL_OFFICER, etc.
    region_id = Column(String(36), ForeignKey("regions.id"), nullable=True, index=True)
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=True, index=True)
    
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(64), nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    region = relationship("Region", back_populates="users")
    institution = relationship("Institution", back_populates="users")
    evc_assignments = relationship("EVCAssignment", back_populates="user")


# ============================================================================
# 3. APPLICATIONS & WORKFLOW PIPELINES
# ============================================================================
class Application(Base):
    """
    Approval Applications submitted by Technical Institutions.
    Separation of Duties (SoD) enforces:
      submitter_id != verifier_id
      verifier_id != approver_id
      submitter_id != approver_id
    """
    __tablename__ = "applications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_no = Column(String(50), unique=True, nullable=False, index=True)
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=False, index=True)
    region_id = Column(String(36), ForeignKey("regions.id"), nullable=False, index=True)
    application_type = Column(String(50), nullable=False) # NEW_INSTITUTION, EXTENSION_OF_APPROVAL, INCREASE_INTAKE, NEW_PROGRAMME, CLOSURE
    academic_year = Column(String(20), default="2026-2027")
    pipeline_type = Column(String(50), nullable=False) # ONLY_SCRUTINY, SCRUTINY_EVC, EVC_SAC_SHC, ONLY_EVC, CUSTOM_APH
    
    current_stage = Column(String(50), nullable=False, default="SCRUTINY")
    status = Column(String(50), nullable=False, default="IN_PROGRESS") # IN_PROGRESS, PAUSED, DEFICIENT, APPROVED, REJECTED, ESCALATED
    
    # Actors enforcing Separation of Duties (SoD)
    submitter_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    assigned_officer_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verifier_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    
    sla_deadline = Column(DateTime, nullable=False)
    sla_status = Column(String(20), default="ON_TRACK") # ON_TRACK, AT_RISK, OVERDUE
    paused_accumulated_hours = Column(Float, default=0.0)
    last_paused_at = Column(DateTime, nullable=True)
    
    submitted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    institution = relationship("Institution", back_populates="applications")
    region = relationship("Region", back_populates="applications")
    stages = relationship("ApplicationStage", back_populates="application", order_by="ApplicationStage.sequence_order")
    events = relationship("CaseEvent", back_populates="application")
    evc_panel = relationship("EVCPanel", back_populates="application", uselist=False)
    undertakings = relationship("TimeBoundUndertaking", back_populates="application")


class ApplicationStage(Base):
    """
    Stage instances within an application's pipeline.
    """
    __tablename__ = "application_stages"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False, index=True)
    stage_name = Column(String(50), nullable=False) # SCRUTINY, RE_SCRUTINY, EVC, SAC_SHC, COUNCIL_DECISION
    sequence_order = Column(Integer, nullable=False)
    status = Column(String(20), default="PENDING") # PENDING, ACTIVE, PASSED, REVERTED, FAILED
    
    started_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    sla_days_allotted = Column(Integer, default=7) # sample value, configurable
    sla_days_spent = Column(Float, default=0.0)
    handler_role = Column(String(50), default="REGIONAL_OFFICER")

    application = relationship("Application", back_populates="stages")


class CaseEvent(Base):
    """
    Append-only timeline of all actions and observations on an application.
    NEVER UPDATE OR DELETE.
    """
    __tablename__ = "case_events"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False) # INTAKE, STAGE_ADVANCE, STAGE_REVERT, CURE_SUBMISSION, EVC_SCHEDULED, ESCALATED, APPROVED
    actor_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    actor_role = Column(String(50), nullable=False)
    description = Column(Text, nullable=False)
    aph_clause_ref = Column(String(100), default="APH 2024-27, clause TBD")
    metadata_json = Column(Text, nullable=True) # JSON extra context
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="events")


class StageRevert(Base):
    """
    Formal return/revert of application with recorded deficiencies.
    Pauses statutory SLA clock.
    """
    __tablename__ = "stage_reverts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False, index=True)
    stage_id = Column(String(36), ForeignKey("application_stages.id"), nullable=False)
    reverted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    reason_category = Column(String(100), nullable=False)
    deficiency_remarks = Column(Text, nullable=False)
    aph_clause_ref = Column(String(100), default="APH 2024-27, clause TBD")
    cure_deadline = Column(DateTime, nullable=False)
    institution_response = Column(Text, nullable=True)
    resubmitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# 4. APH RULES & CLAUSE PROVENANCE
# ============================================================================
class RuleVersion(Base):
    """
    Versioned rulesets parsed or drafted from APH Handbook.
    """
    __tablename__ = "rule_versions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    version = Column(String(50), unique=True, nullable=False) # e.g. APH-2024-27-SAMPLE-V1
    title = Column(String(150), nullable=False)
    is_active = Column(Boolean, default=True)
    approved_by = Column(String(36), ForeignKey("users.id"), nullable=True)
    raw_config_yaml = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    clauses = relationship("APHClause", back_populates="ruleset")


class APHClause(Base):
    """
    Hand-curated or LLM-extracted clauses from the APH Handbook.
    Every rule links to an exact clause and page.
    """
    __tablename__ = "aph_clauses"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ruleset_id = Column(String(36), ForeignKey("rule_versions.id"), nullable=False)
    clause_no = Column(String(50), nullable=False) # e.g. "APH 2024-27, clause TBD"
    title = Column(String(200), nullable=False)
    page_no = Column(Integer, default=0)
    category = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    is_sample = Column(Boolean, default=True) # Labeled sample value pending PDF compilation

    ruleset = relationship("RuleVersion", back_populates="clauses")


# ============================================================================
# 5. EVC (EXPERT VISIT COMMITTEE) SCHEDULING
# ============================================================================
class EVCPanel(Base):
    """
    Inspection panel assigned to an institution.
    """
    __tablename__ = "evc_panels"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), unique=True, nullable=False)
    scheduled_date = Column(Date, nullable=False)
    mode = Column(String(20), default="ON_SITE") # ON_SITE, VIRTUAL
    status = Column(String(50), default="DRAFT_SUGGESTED") # DRAFT_SUGGESTED, CONFIRMED, CONDUCTED, REPORT_SUBMITTED, OVERDUE
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", back_populates="evc_panel")
    assignments = relationship("EVCAssignment", back_populates="panel")
    reports = relationship("EVCReport", back_populates="panel")


class EVCAssignment(Base):
    """
    Committee member assignment with conflict-of-interest declarations.
    """
    __tablename__ = "evc_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    panel_id = Column(String(36), ForeignKey("evc_panels.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    role_in_panel = Column(String(50), default="EXPERT_MEMBER") # CHAIRMAN, CONVENER, EXPERT_MEMBER
    conflict_of_interest_declared = Column(Boolean, default=False)
    conflict_statement = Column(Text, nullable=True)
    attendance_confirmed = Column(Boolean, default=False)

    panel = relationship("EVCPanel", back_populates="assignments")
    user = relationship("User", back_populates="evc_assignments")


class EVCReport(Base):
    """
    Official inspection verdict submitted by the EVC panel.
    """
    __tablename__ = "evc_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    panel_id = Column(String(36), ForeignKey("evc_panels.id"), nullable=False)
    submitted_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    inspection_summary = Column(Text, nullable=False)
    deficiencies_found = Column(Text, nullable=True) # JSON list
    geo_lat = Column(Float, nullable=True)
    geo_lng = Column(Float, nullable=True)
    geo_timestamp = Column(DateTime, nullable=True)
    recommendation = Column(String(50), nullable=False) # RECOMMENDED, NOT_RECOMMENDED, CONDITIONAL
    is_final = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    panel = relationship("EVCPanel", back_populates="reports")


# ============================================================================
# 6. DOCUMENT REGISTRY & TIME-BOUND UNDERTAKINGS
# ============================================================================
class DocumentType(Base):
    """
    Admin-configurable document types with validity rules and alert offsets.
    """
    __tablename__ = "document_types"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(150), nullable=False) # e.g. Registered Land Lease Deed, Fire NOC
    code = Column(String(50), unique=True, nullable=False) # LEASE_DEED, FIRE_NOC, BUILDING_STABILITY
    category = Column(String(50), nullable=False)
    validity_years = Column(Integer, default=5)
    alert_offsets_days = Column(String(50), default="90,60,30,7") # sample value, configurable
    is_mandatory = Column(Boolean, default=True)


class InstitutionalDocument(Base):
    """
    Uploaded regulatory documents with SHA-256 hash tracking and expiry monitoring.
    """
    __tablename__ = "institutional_documents"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=False, index=True)
    doc_type_id = Column(String(36), ForeignKey("document_types.id"), nullable=False)
    document_number = Column(String(100), nullable=False)
    file_url = Column(String(255), nullable=False)
    file_hash_sha256 = Column(String(64), nullable=False, index=True) # SHA-256 for integrity & duplicate detection
    file_size_bytes = Column(Integer, default=102400)
    issue_date = Column(Date, nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    issuing_authority = Column(String(150), nullable=False)
    status = Column(String(30), default="ACTIVE") # ACTIVE, EXPIRING_SOON, EXPIRED, PENDING_VERIFICATION
    
    submitter_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    verifier_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="documents")
    doc_type = relationship("DocumentType")


class TimeBoundUndertaking(Base):
    """
    Conditional approvals with time-bound milestones.
    """
    __tablename__ = "time_bound_undertakings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    institution_id = Column(String(36), ForeignKey("institutions.id"), nullable=False, index=True)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=True)
    aph_clause_ref = Column(String(100), default="APH 2024-27, clause TBD")
    condition_title = Column(String(200), nullable=False)
    condition_details = Column(Text, nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    status = Column(String(30), default="PENDING") # PENDING, SUBMITTED, VERIFIED_CLOSED, DEFAULT_ESCALATED
    evidence_file_url = Column(String(255), nullable=True)
    
    submitter_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    verifier_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    institution = relationship("Institution", back_populates="undertakings")
    application = relationship("Application", back_populates="undertakings")


# ============================================================================
# 7. AI DRAFTS & AUTHORITY-BOUNDARY (STRICT ISOLATION)
# ============================================================================
class LLMDraft(Base):
    """
    Separate drafts table for AI outputs.
    LLM CANNOT write to case state. Only writes here.
    Separation of Duties:
      requester_id != approver_id (Approver must be an authorized human officer differing from requester).
    """
    __tablename__ = "llm_drafts"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    draft_type = Column(String(50), nullable=False) # DEFICIENCY_LETTER, CASE_SUMMARY, NOTICE_MEMO, OCR_EXTRACTION
    related_entity_type = Column(String(50), nullable=False) # APPLICATION, DOCUMENT, UNDERTAKING
    related_entity_id = Column(String(36), nullable=False)
    prompt_hash = Column(String(64), nullable=False)
    model_version = Column(String(50), default="hosted-llm-v1")
    generated_content = Column(Text, nullable=False) # Schema-validated JSON
    confidence_score = Column(Float, default=0.92)
    source_citations = Column(Text, nullable=True) # JSON list of clause references
    
    status = Column(String(30), default="PENDING_HUMAN_REVIEW") # PENDING_HUMAN_REVIEW, ACCEPTED_OFFICIAL, REJECTED
    requester_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    approver_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    human_edits_diff = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthorityBoundaryMatrix(Base):
    """
    Authority-Boundary Matrix: AUTO, SUGGEST-ONLY, or HUMAN-ONLY.
    Configurable and visible in the UI.
    """
    __tablename__ = "authority_boundary_matrix"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    action_key = Column(String(50), unique=True, nullable=False)
    action_name = Column(String(150), nullable=False)
    classification = Column(String(20), nullable=False) # AUTO, SUGGEST_ONLY, HUMAN_ONLY
    description = Column(Text, nullable=False)
    safeguard_notes = Column(Text, nullable=False)


# ============================================================================
# 8. NOTIFICATIONS & ESCALATION LADDER
# ============================================================================
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), nullable=False) # SLA_ALERT, EVC_SCHEDULE, UNDERTAKING_DUE, LEASE_EXPIRY, ESCALATION
    severity = Column(String(20), default="INFO") # INFO, WARNING, CRITICAL
    scheduled_for = Column(DateTime, nullable=False)
    fired_at = Column(DateTime, nullable=True)
    is_read = Column(Boolean, default=False)
    application_id = Column(String(36), nullable=True)
    escalation_level = Column(String(50), nullable=True) # L1_OFFICER, L2_REGIONAL_HEAD, L3_BUREAU_HEAD, L4_MEMBER_SECRETARY
    delivery_channel = Column(String(30), default="IN_APP") # IN_APP, EMAIL_MOCK, SMS_MOCK
    delivery_status = Column(String(20), default="DELIVERED")
    created_at = Column(DateTime, default=datetime.utcnow)


class EscalationLog(Base):
    __tablename__ = "escalation_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    application_id = Column(String(36), ForeignKey("applications.id"), nullable=False)
    trigger_reason = Column(String(50), nullable=False) # SLA_BREACH, UNDERTAKING_OVERDUE, EXPIRED_LEASE
    escalation_level = Column(String(50), nullable=False) # L1_OFFICER, L2_REGIONAL_HEAD, L3_BUREAU_HEAD, L4_MEMBER_SECRETARY
    recipient_role = Column(String(50), nullable=False)
    recipient_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    status = Column(String(30), default="FIRED") # FIRED, ACKNOWLEDGED, RESOLVED
    fired_at = Column(DateTime, default=datetime.utcnow)


# ============================================================================
# 9. IMMUTABLE HASH-CHAINED AUDIT TRAIL & FRAUD ANOMALIES
# ============================================================================
class AuditTrail(Base):
    """
    Append-only SHA-256 hash-chained ledger.
    Every row contains prev_entry_hash and curr_entry_hash.
    Updates and deletes are strictly prohibited.
    """
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_uuid = Column(String(36), unique=True, nullable=False, default=generate_uuid)
    prev_entry_hash = Column(String(64), nullable=False)
    curr_entry_hash = Column(String(64), nullable=False)
    actor_id = Column(String(36), nullable=True)
    actor_role = Column(String(50), nullable=False)
    action_type = Column(String(50), nullable=False) # INTAKE, ADVANCE, REVERT, EVC_SCHEDULE, VERIFY, AI_APPROVED, ESCALATED, SOD_REJECTED
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(String(36), nullable=False)
    metadata_json = Column(Text, nullable=True)
    ip_address = Column(String(45), default="127.0.0.1")
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)


class DocumentAnomaly(Base):
    """
    Flags suspicious document submissions (e.g. duplicate SHA-256 hash across two institutions).
    SUGGEST-ONLY flag for officer investigation. Never auto-rejects.
    """
    __tablename__ = "document_anomalies"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("institutional_documents.id"), nullable=False)
    anomaly_type = Column(String(50), nullable=False) # DUPLICATE_HASH, ALTERED_METADATA, AREA_MISMATCH, PROMPT_INJECTION
    severity = Column(String(20), default="HIGH")
    details = Column(Text, nullable=False)
    is_dismissed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("InstitutionalDocument")


class HolidayCalendar(Base):
    """
    Working days & statutory holidays calendar.
    SLA clocks pause on holidays.
    """
    __tablename__ = "holidays_calendar"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    holiday_date = Column(Date, unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    is_national = Column(Boolean, default=True)
    region_id = Column(String(36), ForeignKey("regions.id"), nullable=True)
