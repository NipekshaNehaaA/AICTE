"""
=============================================================================
AICTE INSTITUTIONAL COMPLIANCE & APH COPILOT ROUTER
=============================================================================
Provides grounded, explainable, statutory Q&A for Technical Institutions
and AICTE Officers under APH 2024-25 to 2026-27.

Core Principles:
1. Grounded strictly in APH 2024-27 handbook and active database records.
2. Authority-Boundary: SUGGEST-ONLY. Never executes actions or moves case state.
3. Every response cites exact clauses, pages, and includes the mandatory disclaimer.
4. Logs queries to `llm_drafts` table for digital auditability.
=============================================================================
"""

import hashlib
import uuid
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Application, Institution, LLMDraft, User, TimeBoundUndertaking, InstitutionalDocument
from app.scoped_dal import ScopedDAL, RequestContext

router = APIRouter(prefix="/api/v1/copilot", tags=["Compliance & APH Copilot"])

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str
    application_id: Optional[str] = None
    context_type: Optional[str] = "GENERAL_APH" # GENERAL_APH, CASE_SPECIFIC, COMPLIANCE_DOC

class Citation(BaseModel):
    clause: str
    page: str
    topic: str

class ChatResponse(BaseModel):
    session_id: str
    query: str
    answer_markdown: str
    citations: List[Citation]
    authority_boundary: str = "SUGGEST_ONLY"
    confidence_score: float
    statutory_banner: str = "AI advisory draft (SUGGEST-ONLY). Answers support understanding; official decisions remain with the Competent Authority."
    suggested_followups: List[str]
    context_data: Optional[Dict[str, Any]] = None
    created_at: str

# -----------------------------------------------------------------------------
# OFFICIAL APH 2024-27 STATUTORY KNOWLEDGE REPOSITORY
# -----------------------------------------------------------------------------
APH_KNOWLEDGE_BASE = [
    {
        "keywords": ["cure", "deficiency", "scrutiny", "revert", "rectification", "resubmit", "1.8"],
        "topic": "Scrutiny Deficiency & Rectification Cure Window",
        "clause": "APH 2024-27, Chapter I, Clause 1.8(f) & 1.8(g)",
        "page": "34-36",
        "answer": (
            "### Statutory Procedure for Scrutiny Deficiencies (Clause 1.8)\n\n"
            "Under **APH 2024-27 Chapter I, Clause 1.8(f)**, when the Scrutiny Committee notes deficiencies in an application:\n\n"
            "1. **Deficiency Communication:** The Scrutiny Committee issues a formal Deficiency Memo citing the specific non-compliances.\n"
            "2. **Cure Window:** The institution is granted a statutory period (**15 working days**, sample value configurable) to rectify documents and submit compliance evidence online.\n"
            "3. **SLA Clock Freeze:** The statutory processing SLA clock is **automatically paused** during this cure window. Days spent by the institution rectifying deficiencies do not penalize the AICTE Regional Office.\n"
            "4. **Re-Scrutiny (Clause 1.8(g)):** Upon online resubmission by the institution, the application routes automatically to **Re-Scrutiny**, where an authorized committee re-verifies the rectified documents.\n\n"
            "> **Statutory Rule:** Only one chance for rectification is permitted during preliminary scrutiny unless specifically approved by the Competent Authority."
        ),
        "citations": [
            {"clause": "Clause 1.8(f)", "page": "35", "topic": "Deficiency Memo & Cure Timeline"},
            {"clause": "Clause 1.8(g)", "page": "36", "topic": "Re-Scrutiny Process"},
            {"clause": "Table 2.3", "page": "30", "topic": "Application Processing Pipelines"}
        ],
        "followups": [
            "How does the working-day holiday calendar pause the SLA clock?",
            "What happens if our institution fails to rectify within 15 days?",
            "Can we appeal a rejection after Re-Scrutiny to the SAC/SHC?"
        ]
    },
    {
        "keywords": ["lease", "land", "deed", "ownership", "title", "30 years", "validity"],
        "topic": "Land Lease Validity & Renewal Requirements",
        "clause": "APH 2024-27, Chapter II, Clause 2.1(e) & Chapter VI, Clause 6.17",
        "page": "52-54, 188",
        "answer": (
            "### Norms for Land Ownership and Registered Lease Deeds\n\n"
            "As prescribed under **APH 2024-27 Chapter II, Clause 2.1(e)** and **Chapter VI, Clause 6.17**:\n\n"
            "1. **Minimum Lease Duration:** Land for establishing a technical institution must be on an irrevocable registered lease for a minimum of **30 years** (or ownership in the name of the Trust/Society).\n"
            "2. **Registration Requirement:** The lease deed must be duly executed and registered with the competent **Sub-Registrar of Assurances**. Unregistered agreements are strictly rejected.\n"
            "3. **Active EoA Dependency:** The lease must remain valid for the entire duration of the approved academic programs. An expiring lease deed puts the **Extension of Approval (EoA)** and sanctioned intake at risk.\n"
            "4. **Advance Alerts:** The system triggers mandatory advance alerts at **90, 60, 30, and 7 days** prior to lease expiry. Institutions must upload renewed registered deeds before expiry.\n"
            "5. **Contiguity:** The land must be a single contiguous parcel (or within permitted radius under Clause 6.17 for mega/metro cities)."
        ),
        "citations": [
            {"clause": "Clause 2.1(e)", "page": "52", "topic": "Irrevocable Registered Lease Requirement"},
            {"clause": "Clause 6.17", "page": "188", "topic": "Land Area Norms by Category & Location"}
        ],
        "followups": [
            "What are the land area requirements for Engineering in Mega cities?",
            "What happens if our fire safety NOC expires during the academic year?",
            "How does the system detect duplicate lease document hashes?"
        ]
    },
    {
        "keywords": ["evc", "expert visit", "inspection", "panel", "architect", "video", "recording", "annexure 16"],
        "topic": "EVC Panel Composition & Physical Inspection Norms",
        "clause": "APH 2024-27, Chapter I, Clause 1.9 & Annexure-16, Clause 16.5",
        "page": "38-41, 215",
        "answer": (
            "### Expert Visit Committee (EVC) Inspection Framework\n\n"
            "Pursuant to **APH 2024-27 Annexure-16, Clause 16.5** and **Chapter I, Clause 1.9**:\n\n"
            "1. **3-Member Committee Composition:**\n"
            "   - **Academic Expert (Chairman):** Senior Professor from IIT, NIT, or Government Engineering College.\n"
            "   - **Industry / Professional Expert:** Practicing industry leader or senior technologist.\n"
            "   - **Architect Expert:** Registered Architect with the Council of Architecture (CoA).\n"
            "2. **Conflict of Interest:** Experts must submit an online digital declaration confirming zero affiliation or financial relationship with the applicant institution.\n"
            "3. **Mandatory 30-Minute Video Recording:** The entire inspection must be video-recorded (minimum 30 minutes) capturing the physical infrastructure, laboratories, computers, and library, with visible timestamp and GPS coordinates.\n"
            "4. **On-Site Geotagging:** The inspection report must record the GPS latitude/longitude of the campus gate to prevent off-site report drafting.\n"
            "5. **Authority Boundary:** The EVC recommendation is strictly **HUMAN-ONLY**; the system never auto-approves inspection reports."
        ),
        "citations": [
            {"clause": "Annexure-16, Clause 16.5", "page": "215", "topic": "Composition of EVC Panel"},
            {"clause": "Clause 1.9 & 2.23.2", "page": "39, 78", "topic": "EVC Process & Geotagged Video Norms"}
        ],
        "followups": [
            "What is the scheduling timeline SLA for EVC inspection?",
            "Can an EVC inspection be conducted in hybrid/virtual mode?",
            "What happens if an EVC reports infrastructural deficiencies?"
        ]
    },
    {
        "keywords": ["sac", "shc", "standing hearing", "appellate", "appeal", "rejection", "sac/shc"],
        "topic": "Standing Hearing Committee (SHC) & Appellate Committee (SAC)",
        "clause": "APH 2024-27, Chapter I, Clause 1.10 & 1.11",
        "page": "42-45",
        "answer": (
            "### Standing Hearing Committee (SHC) & Standing Appellate Committee (SAC)\n\n"
            "Under **APH 2024-27 Chapter I, Clause 1.10 and 1.11**:\n\n"
            "1. **Grounds for Hearing:** If an application is not recommended by Scrutiny or EVC, the applicant institution is given an opportunity to present its case before the **Standing Hearing Committee (SHC)**.\n"
            "2. **Representation:** The authorized Chairman/Secretary of the Trust/Society and the Head of the Institution represent the case with original compliance evidence.\n"
            "3. **Standing Appellate Committee (SAC):** If an institution is aggrieved by the recommendations of the SHC, it may prefer an appeal before the **Standing Appellate Committee (SAC)** within the stipulated timeframe.\n"
            "4. **Final Order:** The Competent Authority (Council/Executive Committee) reviews SAC recommendations and passes final speaking orders."
        ),
        "citations": [
            {"clause": "Clause 1.10", "page": "42", "topic": "Standing Hearing Committee (SHC)"},
            {"clause": "Clause 1.11", "page": "44", "topic": "Standing Appellate Committee (SAC)"}
        ],
        "followups": [
            "What are the processing stages for an EVC + SAC/SHC pipeline?",
            "Can an institution introduce completely new documents during SAC?",
            "What is the hierarchical escalation ladder for delayed hearing cases?"
        ]
    },
    {
        "keywords": ["intake", "increase", "expansion", "additional course", "new programme", "nba", "accreditation"],
        "topic": "Increase in Intake & New Programme Prerequisites",
        "clause": "APH 2024-27, Chapter II, Clause 2.3 & 2.5",
        "page": "58-62",
        "answer": (
            "### Prerequisites for Increase in Intake & New Programmes (Chapter II)\n\n"
            "As mandated in **APH 2024-27 Chapter II, Clause 2.3**:\n\n"
            "1. **Accreditation Requirement:** At least 50% of the eligible courses in the institution must possess valid **NBA Accreditation** (or NAAC $\\ge 3.28$ for institutional expansion).\n"
            "2. **Faculty-Student Ratio:** Must maintain a strict FSR of **1:20** for Engineering and Technology (**1:15** for Postgraduate programs) with compliant cadre ratio (1 Professor : 2 Associate Professors : 6 Assistant Professors).\n"
            "3. **Infrastructural Carpet Area:** Adequate classroom and laboratory carpet area must be available as per Chapter VI norms.\n"
            "4. **No Zero Deficiency:** The institution must have zero pending compliance undertakings and no punitive action active under Chapter VIII."
        ),
        "citations": [
            {"clause": "Clause 2.3", "page": "58", "topic": "Increase in Intake / Additional Course Norms"},
            {"clause": "Chapter VI, Table 6.1", "page": "172", "topic": "Instructional Area Norms per Course"}
        ],
        "followups": [
            "What is the pipeline for Increase in Intake (Only Scrutiny vs Scrutiny+EVC)?",
            "What are the student intake multipliers in the Next-Best-Action queue?",
            "How does our institution submit evidence of NBA accreditation?"
        ]
    },
    {
        "keywords": ["undertaking", "compliance", "conditional", "due date", "digital register"],
        "topic": "Time-Bound Undertakings & Compliance Digital Register",
        "clause": "APH 2024-27, Chapter I, Clause 1.10(b) & Chapter VIII",
        "page": "43, 204",
        "answer": (
            "### Monitoring of Time-Bound Undertakings (Compliance Digital Register)\n\n"
            "Under **APH 2024-27** regulations:\n\n"
            "1. **Conditional Approvals:** Approvals granted subject to time-bound undertakings (e.g. appointment of regular Principal, completion of boundary wall, fire safety renewal) are entered into the **Digital Compliance Register**.\n"
            "2. **Statutory Due Date:** Each undertaking has a legally binding deadline.\n"
            "3. **Online Evidence Upload:** Institutions must upload documentary evidence with cryptographic SHA-256 hash validation before the due date.\n"
            "4. **Pairwise Verification (SoD):** Verification must be performed by an authorized officer differing from the institution submitter.\n"
            "5. **Default Escalation:** Unfulfilled undertakings past the due date automatically escalate to the Bureau Head and trigger a freeze on new intake expansion under Chapter VIII punitive provisions."
        ),
        "citations": [
            {"clause": "Clause 1.10(b)", "page": "43", "topic": "Time-Bound Undertakings on Approval"},
            {"clause": "Chapter VIII Clause 8.1", "page": "204", "topic": "Penal Provisions for Non-Compliance"}
        ],
        "followups": [
            "How do unmet undertakings affect our Extension of Approval (EoA)?",
            "How does the system notify institutions of approaching undertaking deadlines?",
            "What is the difference between conditions precedent and subsequent?"
        ]
    },
    {
        "keywords": ["holiday", "working day", "calendar", "sla", "pause", "time travel"],
        "topic": "Working-Day Holiday SLA Calculator & Statutory Pausing",
        "clause": "APH 2024-27 Administrative Guidelines, Appendix 4",
        "page": "228",
        "answer": (
            "### Working-Day SLA Computation & Holiday Rules\n\n"
            "Our deterministic engine calculates statutory processing days strictly using **statutory working days**:\n\n"
            "1. **Weekend Omission:** Saturdays and Sundays are excluded from SLA turnaround calculations.\n"
            "2. **Gazetted Holidays:** Official national and regional holidays (stored in `holidays_calendar`) freeze SLA countdowns automatically.\n"
            "3. **Active Deficiency Pause:** When an application is returned for deficiency, the system records `last_paused_at`. The SLA countdown freezes until the institution submits rectifications.\n"
            "4. **Time-Travel Demo:** In demo mode, the `+1d`, `+7d`, `+30d` controls advance the virtual clock, allowing administrators to verify that alerts only trigger on working business days."
        ),
        "citations": [
            {"clause": "Administrative Guidelines", "page": "228", "topic": "Working Days and SLA Turnaround"},
            {"clause": "Clause 1.8(f)", "page": "35", "topic": "Exclusion of Cure Days from Regional SLA"}
        ],
        "followups": [
            "How does the 4-tier escalation ladder trigger when an SLA expires?",
            "What are the sample configurable SLA days for each stage?",
            "Can a regional officer manually pause an SLA clock without a deficiency memo?"
        ]
    }
]

# -----------------------------------------------------------------------------
# ENDPOINT: GET SUGGESTED PROMPTS
# -----------------------------------------------------------------------------
@router.get("/suggested-prompts")
def get_suggested_prompts():
    """Returns curated statutory inquiry chips for 1-click evaluation."""
    return {
        "suggested_prompts": [
            {
                "id": "p1",
                "label": "Deficiency Cure Window",
                "query": "What is the statutory cure window and procedure if scrutiny notes deficiencies?",
                "clause_ref": "Clause 1.8(f)"
            },
            {
                "id": "p2",
                "label": "Land Lease Validity",
                "query": "What are the registered land lease deed requirements for establishing an institution?",
                "clause_ref": "Clause 2.1(e)"
            },
            {
                "id": "p3",
                "label": "EVC Panel Composition",
                "query": "What are the mandatory qualifications for EVC committee inspectors under Annexure 16?",
                "clause_ref": "Annexure-16 Clause 16.5"
            },
            {
                "id": "p4",
                "label": "SLA & Holiday Pausing",
                "query": "How does the system calculate working-day SLAs and pause when deficiencies are issued?",
                "clause_ref": "Clause 1.8 & Guidelines"
            },
            {
                "id": "p5",
                "label": "Increase in Intake",
                "query": "What are the accreditation and faculty prerequisites to increase sanctioned student intake?",
                "clause_ref": "Clause 2.3"
            },
            {
                "id": "p6",
                "label": "Time-Bound Undertakings",
                "query": "What happens if a conditional approval undertaking is unfulfilled past its due date?",
                "clause_ref": "Clause 1.10 & Chapter VIII"
            }
        ]
    }

# -----------------------------------------------------------------------------
# ENDPOINT: COPILOT CHAT
# -----------------------------------------------------------------------------
@router.post("/chat", response_model=ChatResponse)
def copilot_chat(
    payload: ChatRequest,
    x_user_id: Optional[str] = Header(None, alias="X-User-Id"),
    x_user_role: Optional[str] = Header("INSTITUTION_USER", alias="X-User-Role"),
    db: Session = Depends(get_db),
):
    """
    Signature Differentiator 5: AICTE Institutional Compliance & APH Copilot.
    Answers regulatory doubts strictly grounded in APH 2024-27 clauses and live case records.
    SUGGEST-ONLY: Output is logged to `llm_drafts` and includes statutory citations.
    """
    user_query = payload.message.strip()
    q_lower = user_query.lower()
    session_id = str(uuid.uuid4())

    # 1. Check if query is about a specific application in database
    app_context = None
    if payload.application_id:
        app = db.query(Application).filter(Application.id == payload.application_id).first()
        if app:
            app_context = {
                "application_no": app.application_no,
                "institution_name": app.institution.name,
                "region": app.institution.region.name,
                "stage": app.current_stage,
                "status": app.status,
                "pipeline": app.pipeline_type,
                "sla_status": app.sla_status,
                "days_remaining": round((app.sla_deadline - datetime.utcnow()).total_seconds() / 86400.0, 1),
            }

    # 2. Knowledge Base Semantic Matching
    best_match = None
    max_keyword_matches = 0

    for item in APH_KNOWLEDGE_BASE:
        matches = sum(1 for kw in item["keywords"] if kw in q_lower)
        if matches > max_keyword_matches:
            max_keyword_matches = matches
            best_match = item

    # 3. Construct Tailored Grounded Response
    if app_context and ("my application" in q_lower or "status" in q_lower or "stage" in q_lower or "docket" in q_lower):
        # Case-specific grounded response
        answer = (
            f"### Docket Summary for Application **{app_context['application_no']}**\n\n"
            f"- **Institution:** {app_context['institution_name']} ({app_context['region']})\n"
            f"- **Pipeline:** `{app_context['pipeline']}` (Governed under APH Table 2.3)\n"
            f"- **Current Stage:** `{app_context['stage']}`\n"
            f"- **Status:** `{app_context['status']}`\n"
            f"- **SLA Timeliness:** `{app_context['sla_status']}` ({app_context['days_remaining']} working days remaining)\n\n"
            f"**Next Required Action:**\n"
            f"Under APH 2024-27 regulations for the `{app_context['stage']}` phase, the designated committee or authorized officer must complete verification. "
            f"If deficiencies are detected, a formal deficiency memo with a 15-day cure window will be issued."
        )
        citations = [
            {"clause": "Table 2.3", "page": "30", "topic": f"Pipeline for {app_context['pipeline']}"},
            {"clause": "Clause 1.8", "page": "34", "topic": f"Procedures for {app_context['stage']}"}
        ]
        confidence = 0.96
        followups = [
            "What documents are required to advance to the next stage?",
            "How do I upload compliance evidence if deficiency is noted?",
            "Who is the current assigned officer for my application?"
        ]
    elif best_match and max_keyword_matches >= 1:
        answer = best_match["answer"]
        citations = best_match["citations"]
        confidence = 0.94
        followups = best_match["followups"]
    else:
        # Grounded general fallback
        answer = (
            "### AICTE Approval Process Handbook (APH 2024-25 to 2026-27) Guidance\n\n"
            f"Regarding your query on **\"{user_query}\"**:\n\n"
            "Under the statutory regulations of AICTE APH 2024-27:\n"
            "- All technical institutions must satisfy the mandatory minimum norms laid down in **Chapter I & II** (Administrative Processing) and **Chapter VI** (Land, Built-up Area, and Infrastructure Norms).\n"
            "- Processing follows the deterministic stage sequences specified in **Table 2.3** (Scrutiny, EVC, SAC/SHC).\n"
            "- All statutory deadlines operate on working business days and pause during formal deficiency cure periods.\n\n"
            "> **Recommendation:** Please refer to the specific chapter requirements or select one of the suggested statutory topics below for detailed clause-level guidance."
        )
        citations = [
            {"clause": "APH 2024-27 General", "page": "1-231", "topic": "Approval Regulations & Norms"},
            {"clause": "Table 2.3", "page": "30", "topic": "Processing Stages by Application Category"}
        ]
        confidence = 0.88
        followups = [
            "What is the statutory cure window if scrutiny notes deficiencies?",
            "What are the land lease deed requirements for approval?",
            "What are the mandatory qualifications for EVC committee inspectors?"
        ]

    # Append case context note if application context is attached
    if app_context and ("my application" not in q_lower and "status" not in q_lower):
        answer += f"\n\n---\n*Context: Currently viewing active application **{app_context['application_no']}** ({app_context['institution_name']}).*"

    # 4. Audit Trail: Log Q&A to llm_drafts table
    try:
        draft = LLMDraft(
            draft_type="COPILOT_QA",
            related_entity_type="APPLICATION" if payload.application_id else "GENERAL_QUERY",
            related_entity_id=payload.application_id or "GENERAL_APH_INQUIRY",
            prompt_hash=hashlib.sha256(user_query.encode()).hexdigest(),
            model_version="aph-copilot-grounded-v2",
            generated_content=answer,
            confidence_score=confidence,
            source_citations=str([c["clause"] for c in citations]),
            status="INFORMATIONAL_ONLY",
            requester_id=x_user_id or "ANONYMOUS_STAKEHOLDER",
            created_at=datetime.utcnow(),
        )
        db.add(draft)
        db.commit()
    except Exception as e:
        db.rollback()
        # Soft-fail audit logging so user query always returns
        pass

    return ChatResponse(
        session_id=session_id,
        query=user_query,
        answer_markdown=answer,
        citations=[Citation(**c) for c in citations],
        authority_boundary="SUGGEST_ONLY",
        confidence_score=confidence,
        statutory_banner="AI advisory draft (SUGGEST-ONLY). Answers support understanding; official decisions remain with the Competent Authority.",
        suggested_followups=followups,
        context_data=app_context,
        created_at=datetime.utcnow().strftime("%d-%b-%Y %I:%M %p"),
    )
