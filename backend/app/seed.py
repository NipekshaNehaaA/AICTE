"""
Deterministic Synthetic Data Seeder for AICTE Approval & Compliance System.
Seeds 200+ fictional institutions across 7 regional offices, users for all roles,
mixed application pipelines, document types, undertakings, and the 7 deliberate demo edge cases.
All data is explicitly synthetic.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import random
import hashlib
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from app.database import SessionLocal, init_db
from app.auth import hash_password
from app.models import (
    Region,
    Institution,
    User,
    Application,
    ApplicationStage,
    CaseEvent,
    StageRevert,
    RuleVersion,
    APHClause,
    EVCPanel,
    EVCAssignment,
    EVCReport,
    DocumentType,
    InstitutionalDocument,
    TimeBoundUndertaking,
    Notification,
    EscalationLog,
    LLMDraft,
    AuthorityBoundaryMatrix,
    HolidayCalendar,
    AuditTrail,
    DocumentAnomaly,
    AcademicCalendar,
)

# Set deterministic random seed for repeatable demos
random.seed(42)

SAMPLE_REGIONS_CONFIG = [
    {"code": "SWRO", "name": "South-Western Regional Office", "city": "Bengaluru", "states": ["Karnataka", "Kerala", "Lakshadweep"]},
    {"code": "SRO", "name": "Southern Regional Office", "city": "Chennai", "states": ["Tamil Nadu", "Puducherry", "Andaman & Nicobar"]},
    {"code": "WRO", "name": "Western Regional Office", "city": "Mumbai", "states": ["Maharashtra", "Goa", "Gujarat", "DNH & DD"]},
    {"code": "NRO", "name": "Northern Regional Office", "city": "Kanpur", "states": ["Uttar Pradesh", "Uttarakhand"]},
    {"code": "ERO", "name": "Eastern Regional Office", "city": "Kolkata", "states": ["West Bengal", "Bihar", "Odisha", "Jharkhand", "Assam"]},
    {"code": "CRO", "name": "Central Regional Office", "city": "Bhopal", "states": ["Madhya Pradesh", "Chhattisgarh"]},
    {"code": "NWRO", "name": "North-Western Regional Office", "city": "Chandigarh", "states": ["Punjab", "Haryana", "Himachal Pradesh", "Jammu & Kashmir", "Delhi"]},
]

INSTITUTION_PREFIXES = [
    "Apex", "Horizon", "Pinnacle", "Vanguard", "Zenith", "Quantum", "Beacon",
    "Nexus", "Starlight", "Crestview", "Silverline", "Trident", "Summit",
    "Evergreen", "Frontier", "Olympus", "Astral", "Catalyst", "Nova",
    "Paramount", "Titan", "Valiance", "Solaris", "Radiant", "Vortex",
    "Spectrum", "Equinox", "Meridian", "Ascent", "Centennial"
]

INSTITUTION_TYPES = [
    ("Institute of Technology", "Engineering & Tech"),
    ("Engineering Academy", "Engineering & Tech"),
    ("Polytechnic College", "Applied Engineering"),
    ("School of Advanced Computing", "Computer Applications"),
    ("Institute of Management & Research", "Management"),
    ("College of Pharmaceutical Sciences", "Pharmacy"),
    ("School of Architecture & Planning", "Architecture"),
]

DOCUMENT_TYPES_CONFIG = [
    {"name": "Registered Land Lease Deed (30+ Years)", "code": "LEASE_DEED", "category": "LAND_BUILDING", "years": 30, "offsets": "90,60,30,7"},
    {"name": "Fire and Life Safety Certificate (NOC)", "code": "FIRE_NOC", "category": "SAFETY", "years": 1, "offsets": "60,30,15,7"},
    {"name": "Building Stability & Structural Soundness Certificate", "code": "BUILDING_STABILITY", "category": "SAFETY", "years": 5, "offsets": "90,60,30"},
    {"name": "Affiliating University Approval Order", "code": "UNIVERSITY_AFFILIATION", "category": "ACADEMIC", "years": 1, "offsets": "60,30,15"},
    {"name": "Pollution Control Board Consent Certificate", "code": "POLLUTION_NOC", "category": "ENVIRONMENT", "years": 3, "offsets": "90,45,15"},
]

def seed_database():
    init_db()
    db: Session = SessionLocal()

    # Clear and sync schema for clean demo seed
    try:
        from app.database import Base
        Base.metadata.drop_all(bind=db.get_bind())
        Base.metadata.create_all(bind=db.get_bind())
    except Exception as e:
        print("Schema sync warning:", e)

    print("--- 1. Seeding Configurable Regions (Sample List) ---")
    regions_map = {}
    for r_data in SAMPLE_REGIONS_CONFIG:
        reg = Region(
            code=r_data["code"],
            name=r_data["name"],
            city=r_data["city"],
            jurisdiction_states=str(r_data["states"]),
        )
        db.add(reg)
        db.flush()
        regions_map[r_data["code"]] = reg

    print("--- 2. Seeding Document Types Registry ---")
    doc_types_map = {}
    for dt in DOCUMENT_TYPES_CONFIG:
        doc_type = DocumentType(
            name=dt["name"],
            code=dt["code"],
            category=dt["category"],
            validity_years=dt["years"],
            alert_offsets_days=dt["offsets"],
            is_mandatory=True,
        )
        db.add(doc_type)
        db.flush()
        doc_types_map[dt["code"]] = doc_type

    print("--- 3. Seeding Authority-Boundary Matrix ---")
    boundary_items = [
        ("ROUTE_PIPELINE", "Determine Application Stage Pipeline", "AUTO", "Deterministic rules engine matches application type to APH route.", "Full APH clause provenance linked in UI."),
        ("SLA_CALCULATE", "Working-Day SLA Countdown & Pause", "AUTO", "Calculates elapsed time excluding holidays. Pauses during deficiency cure.", "No LLM modification allowed."),
        ("ESCALATE_ALERT", "Multi-Tier Escalation Notification", "AUTO", "Fires automated alerts to designated hierarchy when threshold reached.", "Tamper-evident audit log appended."),
        ("DRAFT_DEFICIENCY_MEMO", "Draft Formal Deficiency Notice", "SUGGEST_ONLY", "LLM drafts notice with clause citations.", "Human Officer approval required before dispatch."),
        ("OCR_EXTRACT_DOC", "Extract Expiry & Metadata from Document", "SUGGEST_ONLY", "Confidence score displayed. Low confidence forces manual entry.", "Human verifier confirms dates."),
        ("NEXT_BEST_ACTION", "Work Queue Risk Ranking", "SUGGEST_ONLY", "Ranks cases by breach risk x student intake impact.", "Advisory priority, does not bind officer."),
        ("VERIFY_SCRUTINY", "Scrutiny Eligibility Sign-Off", "HUMAN_ONLY", "Statutory decision reserved for authorized committee.", "Digital signature and recorded findings required."),
        ("EVC_INSPECTION_VERDICT", "Inspection Assessment & Recommendation", "HUMAN_ONLY", "EVC experts conduct on-site/virtual review.", "Geotagged checklist and unanimous sign-off."),
        ("GRANT_APPROVAL", "Final Approval / Rejection Order", "HUMAN_ONLY", "Reserved strictly for Competent Authority (Council/HQ).", "Legally binding statutory outcome."),
    ]
    for act_key, act_name, cls, desc, notes in boundary_items:
        db.add(AuthorityBoundaryMatrix(
            action_key=act_key, action_name=act_name, classification=cls, description=desc, safeguard_notes=notes
        ))

    print("--- 4. Seeding Sample APH Rules & Clauses (Placeholders) ---")
    rule_ver = RuleVersion(
        version="APH-2024-27-SAMPLE-V1",
        title="AICTE Approval Process Handbook (Sample Configurable Ruleset)",
        is_active=True,
        raw_config_yaml="cycle: 2024-2027\nsample_slas:\n  scrutiny_days: 7\n  evc_schedule_days: 15\n  undertaking_cure_days: 30",
    )
    db.add(rule_ver)
    db.flush()

    clauses_seed = [
        ("Clause TBD-2.4", "Grant of Approval for Extension of Approval (EoA)", 18, "Approval Process", "APH 2024-27, clause TBD [Sample value, configurable]"),
        ("Clause TBD-1.3", "Requirements for Setting Up New Technical Institution", 34, "New Institutions", "APH 2024-27, clause TBD [Sample value, configurable]"),
        ("Clause TBD-3.1", "Constitution and Mandate of Expert Visit Committee (EVC)", 52, "Inspections", "APH 2024-27, clause TBD [Sample value, configurable]"),
        ("Clause TBD-4.2", "Time-Bound Undertakings and Post-Approval Compliance", 76, "Compliance", "APH 2024-27, clause TBD [Sample value, configurable]"),
        ("Clause TBD-5.5", "Land Ownership, Lease Period and Building Stability Norms", 91, "Infrastructure", "APH 2024-27, clause TBD [Sample value, configurable]"),
    ]
    for c_no, c_title, p_no, cat, desc in clauses_seed:
        db.add(APHClause(
            ruleset_id=rule_ver.id,
            clause_no=c_no,
            title=c_title,
            page_no=p_no,
            category=cat,
            description=desc,
            is_sample=True,
        ))

    print("--- 5. Seeding Core Users (Officers, Admins, Auditors, Committee Members) ---")
    default_pw_hash = hash_password("DemoPassword@123")

    # Super Admin / Senior Authority (HQ)
    admin_user = User(
        email="member.secretary@aicte-india.org",
        password_hash=default_pw_hash,
        full_name="Dr. Arvind Ramanathan (Member Secretary)",
        role="SUPER_ADMIN",
        region_id=None,
        mfa_enabled=True,
    )
    db.add(admin_user)

    # Bureau Head (HQ - Assumed Escalation Level L3)
    bureau_head_user = User(
        email="bureau.head@aicte-india.org",
        password_hash=default_pw_hash,
        full_name="Dr. M. S. Jayaprakash (Bureau Head, Assumed Escalation)",
        role="BUREAU_HEAD",
        region_id=None,
        mfa_enabled=True,
    )
    db.add(bureau_head_user)

    # Bureau Officer (HQ)
    bureau_user = User(
        email="approval.bureau@aicte-india.org",
        password_hash=default_pw_hash,
        full_name="Shri Anand K. Sharma (Approval Bureau Officer)",
        role="BUREAU_OFFICER",
        region_id=None,
        mfa_enabled=True,
    )
    db.add(bureau_user)

    # SAC / SHC Appellate Committee Member (Pan-India)
    sac_user = User(
        email="sac.appellate@aicte-india.org",
        password_hash=default_pw_hash,
        full_name="Justice (Retd.) K. V. Narayanan (SAC Member)",
        role="SAC_SHC_MEMBER",
        region_id=None,
        mfa_enabled=False,
    )
    db.add(sac_user)

    # Statutory Auditor (HQ - Read Only)
    auditor_user = User(
        email="auditor.compliance@aicte-india.org",
        password_hash=default_pw_hash,
        full_name="Smt. Priya Balan (Statutory Auditor)",
        role="AUDITOR",
        region_id=None,
        mfa_enabled=False,
    )
    db.add(auditor_user)
    db.flush()

    # Regional Officers & Committee Members for each of the 7 regions
    ro_users_map = {}
    rd_users_map = {}
    committee_users_map = {}
    for code, reg in regions_map.items():
        ro_user = User(
            email=f"ro.{code.lower()}@aicte-india.org",
            password_hash=default_pw_hash,
            full_name=f"Dr. Regional Officer ({code} - {reg.city})",
            role="REGIONAL_OFFICER",
            region_id=reg.id,
            mfa_enabled=True,
        )
        db.add(ro_user)
        db.flush()
        ro_users_map[code] = ro_user

        rd_user = User(
            email=f"rd.{code.lower()}@aicte-india.org",
            password_hash=default_pw_hash,
            full_name=f"Dr. Regional Director ({code} - Assumed Escalation)",
            role="REGIONAL_DIRECTOR",
            region_id=reg.id,
            mfa_enabled=True,
        )
        db.add(rd_user)
        db.flush()
        rd_users_map[code] = rd_user

        cm_user = User(
            email=f"expert.{code.lower()}@aicte-india.org",
            password_hash=default_pw_hash,
            full_name=f"Prof. EVC Expert ({code})",
            role="COMMITTEE_MEMBER",
            region_id=reg.id,
            mfa_enabled=False,
        )
        db.add(cm_user)
        db.flush()
        committee_users_map[code] = cm_user

        # Scrutiny Committee Member
        scrutiny_user = User(
            email=f"scrutiny.{code.lower()}@aicte-india.org",
            password_hash=default_pw_hash,
            full_name=f"Prof. Scrutiny Member ({code})",
            role="SCRUTINY_MEMBER",
            region_id=reg.id,
            mfa_enabled=False,
        )
        db.add(scrutiny_user)
        db.flush()

    print("--- 6. Seeding 210 Synthetic Technical Institutions (30 per Region) ---")
    institutions_list = []
    inst_idx = 1
    region_codes = list(regions_map.keys())

    for reg_code in region_codes:
        reg = regions_map[reg_code]
        for i in range(30):
            prefix = INSTITUTION_PREFIXES[i % len(INSTITUTION_PREFIXES)]
            suffix, category = INSTITUTION_TYPES[i % len(INSTITUTION_TYPES)]
            inst_name = f"{prefix} {suffix} [{reg.city} Campus]"
            pid = f"1-{10000000 + inst_idx}"
            health_score = round(random.uniform(78.0, 99.5), 1)

            inst = Institution(
                permanent_id=pid,
                name=inst_name,
                address=f"Plot {10 + i}, Tech Knowledge Park, Sector {i % 12 + 1}",
                state=random.choice(eval(reg.jurisdiction_states)),
                region_id=reg.id,
                category=category,
                status="ACTIVE",
                compliance_health_score=health_score,
                is_synthetic=True,
            )
            db.add(inst)
            db.flush()
            institutions_list.append(inst)

            # Create institution admin user for every 5th institute
            if i % 5 == 0:
                inst_user = User(
                    email=f"principal.{inst.permanent_id.replace('-', '')}@fictional-aicte.edu.in",
                    password_hash=default_pw_hash,
                    full_name=f"Dr. Principal ({prefix})",
                    role="INSTITUTION_USER",
                    region_id=reg.id,
                    institution_id=inst.id,
                )
                db.add(inst_user)

            inst_idx += 1

    db.commit()
    print(f"Successfully seeded {len(institutions_list)} synthetic institutions across all 7 regions.")

    print("--- 7. Seeding Applications & Pipelines ---")
    now = datetime.utcnow()
    app_types = ["EXTENSION_OF_APPROVAL", "INCREASE_INTAKE", "NEW_PROGRAMME", "NEW_INSTITUTION"]
    pipeline_types = ["ONLY_SCRUTINY", "SCRUTINY_EVC", "ONLY_SCRUTINY", "EVC_SAC_SHC"]

    # Seed ~80 applications across various institutions
    for i in range(80):
        inst = institutions_list[i]
        reg_code = [k for k, v in regions_map.items() if v.id == inst.region_id][0]
        ro_user = ro_users_map[reg_code]
        
        # Submitter user: Institution admin or system submitter
        inst_user = db.query(User).filter(User.institution_id == inst.id).first()
        if not inst_user:
            inst_user = User(
                email=f"registrar.{inst.permanent_id.replace('-', '')}@fictional-aicte.edu.in",
                password_hash=default_pw_hash,
                full_name=f"Registrar ({inst.name[:15]})",
                role="INSTITUTION_USER",
                region_id=inst.region_id,
                institution_id=inst.id,
            )
            db.add(inst_user)
            db.flush()

        app_type = app_types[i % len(app_types)]
        pipe_type = pipeline_types[i % len(pipeline_types)]
        app_no = f"AICTE/2026-27/{inst.permanent_id}"

        # SLA calculation (realistic baseline: statutory 25-50 days per APH 2024-27)
        sla_deadline = now + timedelta(days=random.randint(25, 50))
        sla_status = "ON_TRACK"

        app = Application(
            application_no=app_no,
            institution_id=inst.id,
            region_id=inst.region_id,
            application_type=app_type,
            academic_year="2026-2027",
            pipeline_type=pipe_type,
            current_stage="SCRUTINY",
            status="IN_PROGRESS",
            submitter_id=inst_user.id,
            assigned_officer_id=ro_user.id,
            verifier_id=None,
            approver_id=None,
            sla_deadline=sla_deadline,
            sla_status=sla_status,
            submitted_at=now - timedelta(days=random.randint(1, 8)),
        )
        db.add(app)
        db.flush()

        # Add initial stage
        stage = ApplicationStage(
            application_id=app.id,
            stage_name="SCRUTINY",
            sequence_order=1,
            status="ACTIVE",
            started_at=app.submitted_at,
            due_at=sla_deadline,
            sla_days_allotted=21, # realistic statutory scrutiny timeline
        )
        db.add(stage)

        # Initial Case Event
        db.add(CaseEvent(
            application_id=app.id,
            event_type="INTAKE",
            actor_id=inst_user.id,
            actor_role="INSTITUTION_USER",
            description=f"Application submitted for {app_type} by {inst.name}.",
            aph_clause_ref="APH 2024-27, clause TBD",
        ))

    db.commit()

    print("--- 8. Seeding Deliberate Demo Edge Cases ---")

    # EDGE CASE 1: Approaching SLA (Due in 2 days)
    edge_inst_1 = institutions_list[0]
    app_edge_1 = db.query(Application).filter(Application.institution_id == edge_inst_1.id).first()
    if app_edge_1:
        app_edge_1.sla_deadline = now + timedelta(days=2)
        app_edge_1.sla_status = "AT_RISK"
        db.add(Notification(
            user_id=ro_users_map["SWRO"].id,
            title="SLA Alert: Approaching Deadline (2 Days Left)",
            message=f"Application {app_edge_1.application_no} at {edge_inst_1.name} has 2 days remaining before scrutiny deadline.",
            category="SLA_ALERT",
            severity="WARNING",
            scheduled_for=now,
            fired_at=now,
            is_read=False,
            application_id=app_edge_1.id,
        ))

    # EDGE CASE 2: Overdue SLA (Overdue by 4 days, Escalated to L2)
    edge_inst_2 = institutions_list[1]
    app_edge_2 = db.query(Application).filter(Application.institution_id == edge_inst_2.id).first()
    if app_edge_2:
        app_edge_2.sla_deadline = now - timedelta(days=4)
        app_edge_2.sla_status = "OVERDUE"
        app_edge_2.status = "ESCALATED"
        db.add(EscalationLog(
            application_id=app_edge_2.id,
            trigger_reason="SLA_BREACH",
            escalation_level="L2_REGIONAL_HEAD",
            recipient_role="REGIONAL_OFFICER",
            recipient_id=ro_users_map["SWRO"].id,
            status="FIRED",
            fired_at=now - timedelta(days=1),
        ))
        # Multi-Channel notification delivery logs (In-App, Email Mock, SMS Mock, WhatsApp Mock)
        channels = [
            ("IN_APP", "Direct Portal Session"),
            ("EMAIL_MOCK", "ro.swro@aicte-india.org"),
            ("SMS_MOCK", "+91-9876543210"),
            ("WHATSAPP_MOCK", "+91-9876543210"),
        ]
        for ch, contact in channels:
            db.add(Notification(
                user_id=ro_users_map["SWRO"].id,
                title="SLA Breach Escalation (Level 2)",
                message=f"Application {app_edge_2.application_no} exceeded statutory timeline by 4 days. Escalated to Regional Director.",
                category="ESCALATION",
                severity="CRITICAL",
                scheduled_for=now,
                fired_at=now,
                is_read=False,
                application_id=app_edge_2.id,
                escalation_level="L2_REGIONAL_HEAD",
                delivery_channel=ch,
                delivery_status="DELIVERED",
                recipient_contact=contact,
            ))

    # EDGE CASE 3: Expired Lease Deed (Expired 12 days ago)
    edge_inst_3 = institutions_list[2]
    inst_user_3 = db.query(User).filter(User.institution_id == edge_inst_3.id).first()
    lease_doc = InstitutionalDocument(
        institution_id=edge_inst_3.id,
        doc_type_id=doc_types_map["LEASE_DEED"].id,
        document_number="LEASE-REG-1994-KAR-0921",
        file_url="/storage/synthetic_docs/lease_expired_sample.pdf",
        file_hash_sha256="4a5b6c7d8e9f0123456789abcdef0123456789abcdef0123456789abcdef0123",
        issue_date=date(1994, 10, 10),
        expiry_date=date.today() - timedelta(days=12),
        issuing_authority="Sub-Registrar Bengaluru South",
        status="EXPIRED",
        submitter_id=inst_user_3.id if inst_user_3 else admin_user.id,
    )
    db.add(lease_doc)
    edge_inst_3.compliance_health_score = 64.0
    edge_inst_3.status = "DEFICIENT"

    # EDGE CASE 4: Overdue Time-Bound Undertaking (Overdue 5 days)
    edge_inst_4 = institutions_list[3]
    inst_user_4 = db.query(User).filter(User.institution_id == edge_inst_4.id).first()
    undertaking_edge = TimeBoundUndertaking(
        institution_id=edge_inst_4.id,
        condition_title="Recruitment of Qualified Principal (PhD in Engineering)",
        condition_details="Appointment of a regular Professor & Principal as prescribed under APH norms.",
        due_date=date.today() - timedelta(days=5),
        status="DEFAULT_ESCALATED",
        aph_clause_ref="APH 2024-27, clause TBD [Sample value, configurable]",
        submitter_id=inst_user_4.id if inst_user_4 else admin_user.id,
    )
    db.add(undertaking_edge)

    # EDGE CASE 5: Duplicate File Hash across two institutions (Fraud Anomaly Demo)
    # The exact same PDF hash uploaded by Institution 5 and Institution 6
    edge_inst_5 = institutions_list[4]
    edge_inst_6 = institutions_list[5]
    inst_user_5 = db.query(User).filter(User.institution_id == edge_inst_5.id).first()
    inst_user_6 = db.query(User).filter(User.institution_id == edge_inst_6.id).first()

    shared_fraud_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    doc_fraud_1 = InstitutionalDocument(
        institution_id=edge_inst_5.id,
        doc_type_id=doc_types_map["FIRE_NOC"].id,
        document_number="FIRE-NOC-KAR-2026-001",
        file_url="/storage/synthetic_docs/fire_noc_5.pdf",
        file_hash_sha256=shared_fraud_hash,
        issue_date=date(2026, 1, 15),
        expiry_date=date(2027, 1, 14),
        issuing_authority="Karnataka Fire & Emergency Services",
        status="PENDING_VERIFICATION",
        submitter_id=inst_user_5.id if inst_user_5 else admin_user.id,
    )
    doc_fraud_2 = InstitutionalDocument(
        institution_id=edge_inst_6.id,
        doc_type_id=doc_types_map["FIRE_NOC"].id,
        document_number="FIRE-NOC-KAR-2026-001",
        file_url="/storage/synthetic_docs/fire_noc_6.pdf",
        file_hash_sha256=shared_fraud_hash,
        issue_date=date(2026, 1, 15),
        expiry_date=date(2027, 1, 14),
        issuing_authority="Karnataka Fire & Emergency Services",
        status="PENDING_VERIFICATION",
        submitter_id=inst_user_6.id if inst_user_6 else admin_user.id,
    )
    db.add(doc_fraud_1)
    db.add(doc_fraud_2)
    db.flush()

    db.add(DocumentAnomaly(
        document_id=doc_fraud_2.id,
        anomaly_type="DUPLICATE_HASH",
        severity="CRITICAL",
        details=f"Identical SHA-256 file hash ({shared_fraud_hash}) detected across two distinct institutions: {edge_inst_5.name} and {edge_inst_6.name}. Officer inspection flagged.",
    ))

    # EDGE CASE 6: Level-3 Escalation (Overdue by 9 days, Escalated to Member Secretary HQ)
    edge_inst_7 = institutions_list[6]
    app_edge_7 = db.query(Application).filter(Application.institution_id == edge_inst_7.id).first()
    if app_edge_7:
        app_edge_7.sla_deadline = now - timedelta(days=9)
        app_edge_7.sla_status = "OVERDUE"
        app_edge_7.status = "ESCALATED"
        db.add(EscalationLog(
            application_id=app_edge_7.id,
            trigger_reason="SLA_BREACH",
            escalation_level="L3_BUREAU_HEAD",
            recipient_role="BUREAU_OFFICER",
            recipient_id=bureau_user.id,
            status="FIRED",
            fired_at=now - timedelta(days=2),
        ))
        db.add(Notification(
            user_id=bureau_user.id,
            title="CRITICAL Escalation (Level 3): EVC Delay Exceeds 8 Days",
            message=f"Application {app_edge_7.application_no} has exceeded regional response window by 9 days. Escalated to Headquarters Bureau.",
            category="ESCALATION",
            severity="CRITICAL",
            scheduled_for=now,
            fired_at=now,
            is_read=False,
            application_id=app_edge_7.id,
            escalation_level="L3_BUREAU_HEAD",
        ))

    # EDGE CASE 7: Case Returned for Deficiency (Paused SLA Clock)
    edge_inst_8 = institutions_list[7]
    app_edge_8 = db.query(Application).filter(Application.institution_id == edge_inst_8.id).first()
    if app_edge_8:
        app_edge_8.status = "DEFICIENT"
        app_edge_8.current_stage = "DEFICIENCY_REVERTED"
        app_edge_8.last_paused_at = now - timedelta(days=3)
        app_edge_8.paused_accumulated_hours = 72.0
        
        revert = StageRevert(
            application_id=app_edge_8.id,
            stage_id=app_edge_8.stages[0].id if app_edge_8.stages else "stg-01",
            reverted_by=ro_users_map["SWRO"].id,
            reason_category="Missing Fire Safety NOC",
            deficiency_remarks="Submitted Fire Safety Certificate expired on 30 Sept 2026. Submit renewed NOC from Competent Authority.",
            aph_clause_ref="APH 2024-27, clause TBD [Sample value, configurable]",
            cure_deadline=now + timedelta(days=12),
        )
        db.add(revert)

    # Add EVC Inspection Panels
    for i in range(12):
        inst = institutions_list[i + 8]
        app_evc = db.query(Application).filter(Application.institution_id == inst.id).first()
        if app_evc:
            app_evc.pipeline_type = "SCRUTINY_EVC"
            app_evc.current_stage = "EVC_SCHEDULED"
            panel = EVCPanel(
                application_id=app_evc.id,
                scheduled_date=date.today() + timedelta(days=random.randint(3, 14)),
                mode="ON_SITE",
                status="CONFIRMED",
            )
            db.add(panel)
            db.flush()

            # Assign Committee Member
            db.add(EVCAssignment(
                panel_id=panel.id,
                user_id=committee_users_map["SWRO"].id,
                role_in_panel="CONVENER",
                conflict_of_interest_declared=True,
                conflict_statement="I hereby declare no past employment or consultancy with the institution in the last 5 years.",
                attendance_confirmed=True,
            ))

    # Seed an isolated AI Draft (SUGGEST-ONLY) with Human Gate
    ai_draft = LLMDraft(
        draft_type="DEFICIENCY_LETTER",
        related_entity_type="APPLICATION",
        related_entity_id=app_edge_8.id if app_edge_8 else "app-01",
        prompt_hash="f5a8b7c6d4e3a2b10987654321abcdef0123456789abcdef0123456789abcdef",
        model_version="hosted-llm-v1",
        generated_content="{'subject': 'Deficiency Notice: Submission of Valid Fire NOC', 'body': 'Pursuant to Chapter II of the Approval Process Handbook, technical institutions are required to maintain active fire safety certification. Please rectify within 15 days.'}",
        confidence_score=0.94,
        source_citations="['APH 2024-27, clause TBD']",
        status="PENDING_HUMAN_REVIEW",
        requester_id=ro_users_map["SWRO"].id,
    )
    db.add(ai_draft)

    # Initial Root Hash for Audit Trail
    init_audit = AuditTrail(
        prev_entry_hash="0" * 64,
        curr_entry_hash=hashlib.sha256(b"AICTE_GENESIS_SIH26262_AUDIT_ROOT").hexdigest(),
        actor_id=admin_user.id,
        actor_role="SUPER_ADMIN",
        action_type="SYSTEM_GENESIS",
        entity_type="SYSTEM",
        entity_id="ROOT",
        metadata_json='{"event": "System initialized with deterministic synthetic seed"}',
        ip_address="127.0.0.1",
    )
    db.add(init_audit)

    # Seed Admin-Entered Public Notice & Academic Calendar (Clause 1.8 & 2.25)
    academic_cal = AcademicCalendar(
        academic_year="2026-2027",
        public_notice_date=date(2026, 1, 15),
        portal_open_date=date(2026, 2, 1),
        portal_close_date=date(2026, 3, 15),
        scrutiny_cutoff_date=date(2026, 4, 15),
        evc_cutoff_date=date(2026, 5, 10),
        sac_appeal_cutoff_date=date(2026, 5, 25),
        eoa_final_cutoff_date=date(2026, 6, 10), # Clause 2.25(j): No EoA granted after this cutoff
        council_ratification_date=date(2026, 6, 30),
        is_active=True,
    )
    db.add(academic_cal)

    db.commit()
    db.close()
    print("Database seeding completed successfully!")

if __name__ == "__main__":
    seed_database()
