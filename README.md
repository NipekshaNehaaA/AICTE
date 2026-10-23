# Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System
### Smart India Hackathon (SIH) — Problem Statement SIH26262

---

## 1. Executive Summary & Positioning: *"Prevent, Not Just Notify"*
The All India Council for Technical Education (AICTE) processes thousands of applications annually across technical institutions under the **Approval Process Handbook (APH 2024-25 to 2026-27)**.
This platform provides an **end-to-end digital approval workflow, compliance monitoring, and alert management system** built on one non-negotiable core principle:

> **Automation SUPPORTS the process. It NEVER replaces statutory scrutiny, verification, inspections, or decisions of the Competent Authority.**

- **Deterministic Rules Engine:** Every routing decision, SLA calculation, and escalation is deterministic and traceable to exact APH clauses (Table 2.3, Chapter I, Chapter II, Chapter VI, Annexures 1, 3, 7, 16).
- **Isolated AI Layer (SUGGEST-ONLY):** The LLM and ML models have **zero write access** to application state. They write exclusively to a separate `llm_drafts` table. A draft becomes official only after a named human officer approves it.
- **Pairwise Separation of Duties (SoD):** Enforces $Submitter \ne Verifier \ne Approver$ and $AI\_Requester \ne AI\_Approver$ at both the database and service levels. Every violation is blocked and logged.
- **Append-Only Cryptographic Audit Trail:** Non-repudiable SHA-256 hash-chained ledger guaranteeing complete auditability.

---

## 2. System Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND (Next.js 14 + TS)                             │
│       Cherry Blossom Surfaces & Ink Wash Neutrals (100% WCAG AA Contrast Passed)       │
│  ┌──────────────────────┬──────────────────────┬────────────────────────────────────┐  │
│  │ Stakeholder Views    │ Real-Time Dashboards │ Signature Differentiators          │  │
│  │ • Institution Portal │ • SLA & Aging RAG    │ • APH-to-Rules Compiler Diff View  │  │
│  │ • Regional Officer   │ • Bottleneck Heatmap │ • Next-Best-Action Priority Queue  │  │
│  │ • EVC Committee View │ • Workload Balance   │ • What-If Scenario Simulator       │  │
│  │ • Bureau Head / HQ   │ • Live Audit Chain   │ • Time-Travel Simulator (+1/+7/+30)│  │
│  └──────────────────────┴──────────────────────┴────────────────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ REST / SSE
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                BACKEND (FastAPI + Python 3.11)                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                         DETERMINISTIC RULES ENGINE                               │  │
│  │  • Pure deterministic state machine (Table 2.3 pipelines, statutory SLAs)        │  │
│  │  • Working day & holiday-aware calendar calculator (pauses during cure period)   │  │
│  │  • Complete clause provenance: Every rule links to exact APH Handbook clauses    │  │
│  └─────────────────────────────────────────┬────────────────────────────────────────┘  │
│                                            │                                           │
│       ┌────────────────────────────────────┼──────────────────────────────────┐        │
│       ▼                                    ▼                                  ▼        │
│  ┌─────────────────────┐        ┌─────────────────────┐        ┌─────────────────────┐ │
│  │ Ingestion & Adapters│        │ Notification Engine │        │ Hash-Chained Audit  │ │
│  │ • AICTE Portal Mock │        │ • Multi-channel mock│        │ • SHA-256 prev_hash │ │
│  │ • DigiLocker Mock   │        │   (In-App/Email/SMS)│        │ • Non-repudiation   │ │
│  │ • e-Sign Mock       │        │ • L1→L2→L3→L4 Ladder│        │ • Tamper Verifier   │ │
│  └─────────────────────┘        └─────────────────────┘        └─────────────────────┘ │
│                                                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐  │
│  │                  ISOLATED AI / LLM ASSIST LAYER (SUGGEST-ONLY)                   │  │
│  │  • Strict read-only case access; cannot advance stages or set deadlines          │  │
│  │  • Writes strictly to `llm_drafts` table with confidence scores & citations      │  │
│  │  • Human approval gate (Authorised Officer ID + Timestamp) to promote draft      │  │
│  │  • OCR & Document Anomaly detector (SHA-256 hash collisions across institutions) │  │
│  └──────────────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              DATA & PERSISTENCE LAYER                                  │
│  • Production: PostgreSQL 16 with native ENABLE + FORCE ROW LEVEL SECURITY (RLS)       │
│  • Development: Scoped Data Access Layer (DAL) with simulated RLS & default deny       │
│  • Storage Adapter: MinIO (S3-compatible) & Local storage                              │
│  • Append-Only Audit Ledger: Immutable SHA-256 cryptographic chain                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Authority-Boundary Matrix

| Action | Classification | Actor / Engine | Fallback / Safeguard | APH 2024-27 Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Pipeline Routing** | **AUTO** | Deterministic Rules Engine | Configured APH Table 2.3 Matrix | Table 2.3 (Page 30) |
| **SLA Countdown & Pause** | **AUTO** | Rules Engine (Calendar-aware) | Pauses automatically when in "Deficient / Cure" state | Chapter I Clause 1.8(f) |
| **Escalation Notification** | **AUTO** | Alert Scheduler ($L_1 \to L_2 \to L_3 \to L_4$) | Triggered when SLA breached; logged in tamper-evident audit | Chapter I Clause 1.10 |
| **Deficiency Letter Drafting** | **SUGGEST-ONLY** | LLM Engine | Stored in `llm_drafts`; must be reviewed & signed by Officer | Chapter I Clause 1.8(f) |
| **Document Field Extraction (OCR)** | **SUGGEST-ONLY** | OCR + LLM Extractor | Confidence $< 0.85$ forces manual entry; Officer verifies | Chapter VI Clause 6.17 |
| **Next-Best-Action Work Queue Ranking** | **SUGGEST-ONLY** | Heuristic / ML Model | Sorts by breach risk $\times$ student intake; non-binding | Section 8 Differentiator |
| **Document Anomaly Flags** | **SUGGEST-ONLY** | Anomaly Engine | Flags duplicate SHA-256 hashes & altered dates; Officer investigates | Chapter II Clause 2.3.5(b) |
| **Scrutiny Verification Decision** | **HUMAN-ONLY** | Authorized Scrutiny Committee | Mandatory officer digital signature & recorded reason | Chapter I Clause 1.8 |
| **EVC Inspection Verdict** | **HUMAN-ONLY** | Expert Visit Committee (EVC) | On-site/virtual report verification with geotag confirmation | Chapter I Clause 1.9 |
| **Approval / Rejection Order** | **HUMAN-ONLY** | Competent Authority (HQ/Council) | Legally binding decision reserved for designated statutory officers | Chapter I Clause 1.10 |

---

## 4. Design System: Cherry Blossom Surfaces + Ink Wash Text

Adheres strictly to the **Cherry Blossom & Ink Wash** tokens with **100% WCAG AA contrast compliance** (verified via automated tests):
- **Surfaces:** `--blossom-100` (`#F2C7C7`), `--blossom-300` (`#FFB7C5`), `--mint-100` (`#D5F3D8`), `--white` (`#FFFFFF`), `--ivory` (`#FFFFE3`).
- **Text & Neutrals:** `--text` (`#4A4A4A`), `--text-strong` (`#2E2E2E`), `--text-muted` (`#55687C` on white/ivory), `--slate` (`#6D8196`), `--line` (`#CBCBCB`).
- **Status & Actions:** `--blossom-600` (`#C2456B`), `--blossom-700` (`#9E3256`), `--mint-700` (`#26693D`), `--amber-100`/`--amber-700`, `--rose-100`/`--rose-700`.
- **Statutory Banner:** *"AI draft. Decision reserved for the competent authority."* & *"Sample value, configurable pending APH 2024-27 compilation."*

---

## 5. Quick Start & Execution

### Option A: Local Dev Startup (Instant Python + Next.js)
```bash
# 1. Initialize & Seed Database (210 institutions, 7 regions, deliberate demo edge cases)
python backend/app/seed.py

# 2. Run Backend (FastAPI on Port 8000)
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# 3. Run Frontend (Next.js on Port 3000 in a separate terminal)
cd frontend
npm run dev
```

### Option B: One-Command Docker Compose (Production Submission)
```bash
docker-compose up --build
```
*Frontend runs on `http://localhost:3000` | Backend API runs on `http://localhost:8000` | MinIO on `http://localhost:9001`*

---

## 6. Demo Credentials Matrix (Seed Data)

| Role | Regional Scope | Name & Office | Email | Password |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | HQ (Pan-India) | Prof. Rajive Kumar (Member Secretary) | `member.secretary@aicte-india.org` | `DemoPassword@123` |
| **Bureau Officer** | HQ (Pan-India) | Shri Anand Sharma (Director, Approval Bureau) | `approval.bureau@aicte-india.org` | `DemoPassword@123` |
| **Regional Officer** | SWRO (Bengaluru) | Dr. Regional Officer (SWRO - Bengaluru) | `ro.swro@aicte-india.org` | `DemoPassword@123` |
| **Regional Officer** | SRO (Chennai) | Dr. Regional Officer (SRO - Chennai) | `ro.sro@aicte-india.org` | `DemoPassword@123` |
| **Committee Member** | SWRO (Bengaluru) | Prof. EVC Expert (SWRO) | `expert.swro@aicte-india.org` | `DemoPassword@123` |
| **Statutory Auditor**| HQ (Pan-India) | Smt. Priya Balan (Statutory Auditor) | `auditor.compliance@aicte-india.org` | `DemoPassword@123` |
| **Institution User** | SWRO (PID 1-10000001) | Dr. Principal (Apex Institute of Technology) | `principal.110000001@fictional-aicte.edu.in` | `DemoPassword@123` |

*MFA Demo Verification Code:* `123456`

---

## 7. Demo Walkthrough Script (for Evaluators)

1. **Time-Travel Demonstration:**
   - In the top bar, click `+7d` or `+30d`.
   - Watch the virtual date fast-forward live, triggering real-time SLA deadline checks, advancing case aging, and automatically firing Level 2 and Level 3 escalations with desktop notifications.
2. **Deterministic Stage Progression & APH Table 2.3 Routing:**
   - Go to **Applications & Routing**.
   - Select an application. Review its **Visual Stage Pipeline**, SLA countdown clock, and the **"Why did this happen?"** clause provenance panel linking to Chapter I Clause 1.8 / Table 2.3.
   - Click **"Sign-Off & Advance Stage (AUTO)"**. Observe the automatic transition to EVC or Hearing.
3. **Authorized Revert Loop & Paused SLA Clock:**
   - Click **"Revert for Deficiency"**. Select *"Land Lease Period Inadequate"* (Clause 2.1(e)) and set a 15-day cure window.
   - Notice the status updates to `DEFICIENT` and the statutory SLA clock immediately pauses.
   - Click **"Submit Rectification"** to simulate institution resubmission. Observe the clock unpause and route to Re-Scrutiny (Clause 1.8(g)).
4. **Isolated AI Assistant & Human Approval Gate:**
   - Click **"Draft Electronic Docket (AI)"**.
   - Review the generated structured case docket in `llm_drafts` with confidence score and APH citations.
   - Observe the mandatory warning: *"AI draft. Decision reserved for the competent authority."*
   - Click **"Approve as Official Record"**. Observe pairwise Separation of Duties ($Requester \ne Approver$) enforced.
5. **Document Integrity & Fraud Detection (Signature Differentiator 2):**
   - Navigate to **Anomalies & Integrity**.
   - Inspect the detected **Duplicate Hash Anomaly**: The system catches identical SHA-256 PDF hashes uploaded by two distinct institutions.
6. **Next-Best-Action Work Queue (Signature Differentiator 3):**
   - Navigate to **Next-Best-Action Queue**.
   - Review the ranked list sorted by $Breach\_Risk \times Student\_Impact \times Overdue\_Multiplier$ with plain-English rationales.
7. **What-If Simulation Lab (Signature Differentiator 3):**
   - Navigate to **What-If Simulation Lab**.
   - Drag sliders for *"Committee Inspectors Unavailable"* and *"Regional Staffing"*. See live projected SLA breaches and at-risk student quotas.
8. **Cryptographic Audit Chain & Tampering Verifier:**
   - Navigate to **Hash-Chained Audit Trail**.
   - Click **"Verify Chain Integrity"** $\to$ Unbroken SHA-256 continuity verified across all records.
   - Click **"Simulate Tampering"** $\to$ Immediate detection of modified historical data with security breach alert! Click **"Restore Chain"** to return to integrity.

---

## 8. Test Suite Verification (100% Passing)

Run all tests via:
```bash
# Full Backend Test Suite (21/21 passing)
python -m pytest backend/tests/ -v

# Automated WCAG AA Contrast Test
npm run test:contrast --prefix frontend
```

### Verified Test Categories:
- **WCAG AA Contrast Ratios:** All 13 text/background pairs pass $\ge 4.5:1$ (normal) and $\ge 3.0:1$ (large/UI).
- **Default Deny:** Empty context returns zero rows.
- **Cross-Region Read Blocked:** Regional officers can only access institutions within their regional office.
- **Cross-Institution Isolation:** Institutions can only access their own records.
- **Committee Member Scoping:** Experts only see applications where they hold an explicit EVC panel assignment.
- **Auditor Read-Only Enforcement:** Auditor mutations throw `SecurityScopeError`.
- **Pairwise Separation of Duties:** Submitter cannot verify; Verifier cannot approve; AI Requester cannot approve. All rejections logged to `audit_trail`.
- **Working-Day SLA Calculation:** Weekends and holidays properly omitted.
- **SLA Pausing:** Clock freezes during deficiency cure.
- **Cryptographic Hash Continuity:** Unbroken SHA-256 hash chaining verified.

---

## 9. DPDP Act 2023 Alignment & Infrastructure Roadmap

- **Data Protection and Digital Privacy (DPDP) Act 2023:**
  - Role-based data minimization: Public tracking lookup by Application ID + OTP shows stage and status only—**zero confidential documents or personal data are exposed**.
  - Separation of duties and strict audit logging of every document view and inspection verdict.
  - Personal data redaction before any external or LLM processing.
- **Government Cloud Hosting Readiness:**
  - Architecture is designed for deployment on **MeitY-empanelled cloud service providers (CSPs)** or **National Informatics Centre (NIC)** government infrastructure.
  - S3-compatible document storage (MinIO adapter) is ready for direct migration to government object storage.

---

## 10. Honest Limitations & Human Oversight

1. **Competent Authority Reservation:** Automated alerts, recommendations, and pipeline routing support the approval workflow but **never replace statutory scrutiny, verification, inspections, or decisions** reserved for authorized AICTE officials and committees.
2. **Simulated External Integrations:** External connectors for the AICTE NSWS Portal, DigiLocker, and Aadhaar e-Sign are implemented as **integration-ready mock adapters** with documented REST payloads.
3. **Synthetic Seed Data:** All 210 institutions, document numbers, and committee member profiles are deterministic synthetic records designed specifically for demonstration and evaluation purposes.
