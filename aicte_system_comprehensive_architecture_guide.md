# AICTE Approval & Compliance Automation System
## Complete System Architecture, Operational Manual & Technical Specification

---

### Executive Overview

The **AICTE Approval & Compliance Automation System** is an enterprise-grade statutory governance portal engineered in alignment with the **All India Council for Technical Education (AICTE) Approval Process Handbook (APH 2024–27)** and the **Digital Personal Data Protection (DPDP) Act 2023**. 

The system transitions AICTE’s technical institution approvals from fragmented, manual inspection queues into a **data-driven, transparent, and auditable digital workflow**, featuring explainable AI (XAI), automated panel dispatch, cryptographic audit ledgers, and strict statutory separation of duties (SoD).

---

## 1. System Topology & Technology Stack

The platform is designed around a decoupled, service-oriented architecture:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 14 App Router)                │
│  • React 18 + TypeScript + Tailwind CSS                                │
│  • Cherry Blossom Statutory Theme (HSL Curated, Contrast Ratio > 4.5:1) │
│  • Lucide React Icons + Chart.js + HTML5 Canvas                       │
│  • Role-Aware Scoped State (AppContext)                                │
│  • Public Outsider Verifier at /verify (Zero PII Disclosure)           │
│  • Port: http://localhost:3000                                         │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API / JSON (Bearer JWT Authorization;
                                    │ custom x-user-* headers stripped & ignored)
┌───────────────────────────────────▼────────────────────────────────────┐
│                       BACKEND (FastAPI / Python 3.11+)                  │
│  • RESTful API Endpoints with Pydantic Schema Validation               │
│  • ScopedDAL: Row-Level Security (RLS) & Default-Deny Scoping          │
│    (AST static analysis test guarantees 0 queries outside ScopedDAL)   │
│  • APH Rules Engine: Table 2.3 Dynamic Router (Conditional SAC/SHC)   │
│  • APH Compiler: Quote-verified rule drafting with BM25 Copilot search │
│  • Deterministic Workload Forecast Engine (Queueing + Holiday + MC)    │
│  • Real SMTP Email Notification Channel with Mailpit & Quiet Hours     │
│  • EVC Panel Conflict-of-Interest Exclusion & RFC 5545 .ics Export     │
│  • Multilingual Statutory Alerts (English, Hindi, Tamil)               │
│  • SHA-256 Hash Chained Audit Ledger & Daily Merkle Roots              │
│  • Uvicorn ASGI Server on http://127.0.0.1:8000                        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLAlchemy ORM via ScopedDAL
┌───────────────────────────────────▼────────────────────────────────────┐
│                             DATA STORE                                 │
│  • SQLite (Development / Demo): aicte_dev.db via ScopedDAL             │
│  • PostgreSQL (Production Specification): schema_rls_postgres.sql      │
│  • Seed Data: 210 Institutions, 7 Regional Offices, Table 2.3 Routes   │
│  • Mailpit SMTP Service: Port 1025 (SMTP) / 8025 (Web UI)              │
│  • MinIO Storage Adapter: S3-Compatible Object Store (Port 9000/9001)  │
└────────────────────────────────────────────────────────────────────────┘
```

### Core Technologies
- **Frontend**: Next.js 14 (App Router), TypeScript, Vanilla CSS + Tailwind CSS utilities, Lucide React icons.
- **Backend**: FastAPI, Python 3.11+, SQLAlchemy 2.0 ORM, Pydantic v2 schemas.
- **Security & Crypto**: PBKDF2-HMAC-SHA256 password hashing, PyJWT tokens (pinned HS256, rejecting `alg=none`, secret loaded from `JWT_SECRET`, session expiration timestamps, server-side verified MFA, DEMO_MODE isolation), SHA-256 cryptographic hash chaining and daily Merkle root sealing for outsider-verifiable audit proofs.
- **Workload Modeling**: Deterministic queueing model with holiday calendar, backlog delay projection, and Monte-Carlo simulation (P10/P50/P90 probability bands) using fixed seeds for guaranteed reproducibility.
- **EVC Panel Optimization**: Statutory conflict exclusion rules (Annexure-16: home state, 24-month cooling period, double-booking guard) with load-balanced panel recommendation and RFC 5545 iCalendar (`.ics`) export.
- **Multilingual Messaging**: Static, verified statutory notification catalog in English, Hindi, and Tamil with exact clause citations (Clause 1.8(f), Clause 1.4.1(e), Annexure-4) and strict fallback to English.
- **Analytics & Explainability**: Weighted risk score with per-factor contributions for triage recommendations.
- **APH Clause Verification**: Automated AST compiler & APH PDF verbatim text proximity verification engine verifying seeded rules against authentic APH 2024-27 text.

---

## 2. End-to-End User Flow & Screen Architecture

```mermaid
graph TD
    Boot[1. Progressive Loading & Boot Screen] -->|Self-Diagnostics Pass / Skip| Login[2. Authorized SSO Login Portal]
    Login -->|Standard Credentials / 1-Click Persona| MFA[3. TOTP Two-Factor Authentication]
    MFA -->|Verification Success| Shell[4. Authenticated Application Shell]
    Shell --> TopBar[Top Navigation & Role Switcher]
    Shell --> Sidebar[Dynamic Role-Scoped Sidebar]
    Shell --> Workspace[Active Work Area]
    Workspace --> Dash[Executive National Command Console]
    Workspace --> AppRouting[Applications & Workflow Engine]
    Workspace --> EVCHub[EVC Inspections Hub]
    Workspace --> Compliance[Undertakings & Leases]
    Workspace --> Differentiators[6 Signature Differentiator Suites]
    Workspace --> Audit[Cryptographic Audit Ledger]
```

### 2.1 Screen 1: System Boot & Diagnostic Loading Screen
- **Visual Design**: Clean white background (`#FFFFFF`) with a central console highlighted in subtle cherry blossom tones (`#FFF0F5` to `#E84370`).
- **Functionality**:
  - Automatically simulates 5 progressive system health checks:
    1. Core Engine Handshake (`/api/v1/health`)
    2. APH 2024–27 Rules Registry compilation
    3. Regional Office network synchronization (SWRO, SRO, WRO, NRO, ERO, CRO, NWRO, HQ)
    4. Cryptographic SHA-256 ledger integrity verification
    5. Role-Based Access Control (RBAC) security matrix initialization
  - Includes progressive percentage meter (0% to 100%).
  - Fast-path **"Skip to Login"** button allows immediate transition without waiting.
  - A persistent execution guard (`completedRef`) ensures that timer cancellations or component re-renders never result in a blank white page.

### 2.2 Screen 2: Authorized SSO Login Screen
- **Tab Order (Strictly Configured)**:
  1. **Standard Credentials (Default / Primary)**: Official AICTE login form with government email, masked password, quick-fill presets, and 5-attempt brute-force lockout protection.
  2. **1-Click Demo Personas (Secondary - Demo Only)**: Grid of 6 interactive stakeholder persona cards designed for evaluators to switch roles instantly with a single click. **Strictly disabled unless `DEMO_MODE=true`**.
- **Cryptographic Authentication & Token Issuance Architecture**:
  - **Server-Side MFA Verification**: Credentials verification alone cannot issue a full session token. A two-factor challenge (TOTP) is required; only upon server-side MFA verification is a signed JWT issued.
  - **Pinned Cryptographic Algorithm**: JWT tokens are signed using a server-side secret loaded from `JWT_SECRET` with pinned `HS256` algorithm. Requests using `alg=none` or tampered signatures are rejected with `HTTP 401 Unauthorized`.
  - **Token Expiry Enforced**: Session tokens enforce session expiration timestamps (`exp`); expired tokens are rejected with `HTTP 401 Unauthorized`.
  - **Strict Header Stripping & JWT Derivation**: Incoming `x-user-role`, `x-user-id`, or client-forged headers are completely stripped and ignored. Role and user jurisdiction are derived solely from cryptographically verified JWT claims.
  - **Role Switcher & Demo Shortcuts**:
    - The top-bar role switcher and 1-click personas are active only when `DEMO_MODE=true`. `DEMO_MODE` defaults to `false`.
    - When switched, the client obtains a new signed JWT from the demo-only endpoint `/api/v1/auth/demo-switch-token/{role}` (with alias `/api/v1/auth/demo-token/{role}`). This endpoint returns `HTTP 403 Forbidden` if `DEMO_MODE` is disabled.
    - TOTP shortcut (`123456`) and the public status-lookup OTP (`123456`) are active only when `DEMO_MODE=true` (and return `HTTP 403 Forbidden` when `DEMO_MODE=false`).
    - Backend startup fails fast with a `RuntimeError` if `JWT_SECRET` is unset in non-demo mode.

---

## 3. The 6 Stakeholder Roles, Data Scoping & Decision Rights

The portal implements strict **Row-Level Security (RLS)**, **Default-Deny Scoping**, and **Pairwise Separation of Duties (SoD)**.
- **Architectural Scoping Barrier**: In development (SQLite), all entity access is strictly mediated by `ScopedDAL`, which injects role and regional boundaries into every query. In production, PostgreSQL enforces native `ENABLE + FORCE ROW LEVEL SECURITY` as defined in `backend/app/schema_rls_postgres.sql`.
- **AST Static Analysis Enforcement**: An automated test (`test_no_router_queries_outside_scoped_dal`) parses the abstract syntax tree of all FastAPI router modules to assert that zero database queries bypass `ScopedDAL`.

```mermaid
graph LR
    User[Stakeholder Request] --> DAL{ScopedDAL Gatekeeper}
    DAL -->|Role Check| RBAC[Module Visibility Check]
    DAL -->|Region Check| RLS[Row-Level Filter]
    DAL -->|Action Check| SoD[Pairwise SoD Validation]
    SoD -->|Pass| DB[(Database / Ledger)]
    SoD -->|Violation| Reject[Append SOD_REJECTED to Ledger]
```

### Detailed Authority Matrix

| Role | Persona & Email | Visible Navigation Items | Data Jurisdiction (Row-Level Security) | Operational Decision Power | Strict Prohibitions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Institution User (Applicant)** | Dr. Ramesh Kumar<br>`principal.110000001@fictional-aicte.edu.in` | • Executive Dashboard<br>• Applications & Routing<br>• Undertakings & Leases | **Own Institution Only**<br>(PID: `1-109283741`) | • Submit new applications<br>• Upload regulatory documents (Leases, Fire NOC)<br>• Submit deficiency cure packages | ❌ Cannot view other institutions<br>❌ Cannot advance AICTE stages<br>❌ Cannot view EVC hub or audit ledger |
| **2. Regional Officer (SWRO)** | Dr. K. S. Venkatesh<br>`ro.swro@aicte-india.org` | • Executive Dashboard<br>• Applications & Routing<br>• EVC Inspections Hub<br>• Undertakings & Leases<br>• Next-Best-Action Queue<br>• What-If Simulation<br>• Audit Trail<br>• Anomalies & Integrity | **Own Region Cases**<br>(South-Western Region / Bengaluru jurisdiction) | • Scrutinize applications<br>• Sign-off & advance Scrutiny / EVC stages<br>• Issue deficiency reverts (pauses SLA clock)<br>• Auto-dispatch EVC inspection panels | ❌ Cannot grant final Council EoA<br>❌ Cannot compile national rules<br>❌ Cannot view cases from other regions |
| **3. Bureau Officer (HQ)** | Shri Anand Sharma<br>`approval.bureau@aicte-india.org` | • Executive Dashboard<br>• Applications & Routing<br>• EVC Inspections Hub<br>• Undertakings & Leases<br>• Next-Best-Action Queue<br>• APH-to-Rules Compiler<br>• What-If Simulation<br>• Audit Trail<br>• Anomalies & Integrity | **Pan-India Policy & Bureau Scope** | • Review regional recommendations<br>• Compile APH clauses into rules<br>• Refer cases to Standing Appellate Committees (SAC) | ❌ Cannot act as both Verifier and Approver on the same application (Pairwise SoD) |
| **4. EVC Committee Expert** | Prof. Meenakshi Sundaram<br>`expert.visit@aicte-india.org` | • Executive Dashboard<br>• EVC Inspections Hub | **Assigned Cases Only**<br>(Zero-conflict panels where assigned) | • Sign conflict-of-interest declarations<br>• Conduct virtual / physical inspections<br>• Submit geo-stamped deficiency reports | ❌ Cannot view general applications<br>❌ Cannot self-assign panels<br>❌ Cannot alter official application stages |
| **5. Member Secretary / Council Administration** | Dr. Arvind Ramanathan<br>`member.secretary@aicte-india.org` | • All Navigation Modules & National Command Console | **Pan-India Council Jurisdiction** | • Council communications & execution of Council decisions<br>• Level 4 council escalation handling<br>• APH compiler management<br>*(Executive Committee decides, Council ratifies; Member Secretary is not the final approving authority)* | ❌ Cannot verify scrutiny on an application they personally sign/ratify (SoD enforced) |
| **6. Statutory Compliance Auditor** | Smt. Priya Balan<br>`auditor.compliance@aicte-india.org` | • Executive Dashboard<br>• Applications & Routing<br>• Undertakings & Leases<br>• APH-to-Rules Compiler<br>• Hash-Chained Audit Trail<br>• Anomalies & Integrity | **Pan-India Read-Only Oversight** | • Verify cryptographic hash chains<br>• Inspect chronological case histories<br>• Audit SoD rejection logs | ❌ **STRICTLY READ-ONLY:** All mutation, stage advance, and document upload buttons are disabled |

---

## 4. Statutory Approval Pipelines & Dynamic SLA Engine

### 4.1 Table-Driven Pipelines & Stage Routing (Table 2.3 vs. Chapter I)

Every submitted application is dynamically routed using the statutory configurations from the APH:

1. **Table 2.3 Routing for Existing Institutions (Chapter II)**:
   - Applies exclusively to **Existing Institutions** under Chapter II, containing exactly **21 seeded application types**.
   - The 21 types map to 3 statutory routes:
     - **Self-Disclosure only**: e.g., `EOA_SELF_DISCLOSURE` (Extension of Approval based on online self-disclosure of facilities).
     - **Scrutiny only**: e.g., `CHANGE_NAME_INSTITUTION`, `CLOSURE_PROGRAMME`, `CHANGE_BANK_DETAILS`, `CONVERSION_WOMEN_COED`.
     - **Scrutiny + EVC + SAC/SHC (as applicable)**: e.g., `EOA_AFTER_BREAK` (Extension of Approval after a break in approval), `INCREASE_INTAKE`, `NEW_PROGRAMME`.
2. **Chapter I Routing for New Technical Institutions**:
   - `NEW_INSTITUTION` applications do **not** fall under Table 2.3. They are governed by Chapter I norms.
   - Sequential statutory lifecycle: `Scrutiny` → `Re-Scrutiny` (if deficiencies noted) → `EVC` (Expert Visit Committee) → `Executive Committee` (decision) → `Council` (ratification).
3. **Conditional SAC / SHC Dynamic Stage Path (`build_route_stage_path`)**:
   - **Standing Appellate Committee (`SAC_HEARING`)**: Pursuant to **Chapter I Clause 1.11(a)** and **Chapter II Clause 2.24(a)**, any institution aggrieved by the decision of the Executive Committee has the right to appeal once to the Council within **7 days**. The SAC hearing stage is dynamically inserted **only** when an active appeal is lodged. It is never shown for standard applications.
   - **Standing Hearing Committee (`SHC_HEARING`)**: Pursuant to **Chapter II Clause 2.23.3** (*Process for Verification of Compliance through Standing Hearing Committee*), SHC is convened for compliance verification of shortcomings. The SHC stage is inserted dynamically **only** when compliance verification applies.
4. **Re-Scrutiny Scope Restriction (Chapter I Clause 1.8(g))**:
   - When an application is reverted for deficiency, Re-Scrutiny is legally restricted to verifying **only** the specific deficiencies pointed out by the Scrutiny Committee as per norms, preventing unbounded re-audits.

### 4.2 Dynamic SLA Escalation Matrix & Pause/Cure Mechanics

The system continuously tracks countdowns against stage deadlines:
- **ON_TRACK (Green)**: > 30% of stage SLA remaining.
- **WARNING (Yellow)**: < 30% of SLA remaining. Automated reminder sent to assigned officer.
- **CRITICAL (Orange)**: < 10% of SLA remaining. Automated high-priority alert to Regional Director.
- **BREACHED (Red)**: Deadline exceeded. Triggers escalation cascade:
  - **Level 1**: Regional Officer
  - **Level 2**: Regional Director
  - **Level 3**: Bureau Head (HQ)
  - **Level 4**: Member Secretary / Council Adjudication

#### The Deficiency Pause & Cure Mechanism (Design Choice, Configurable)
When an application is reverted for deficiency (e.g. inadequate lease tenure or missing NOC), the processing clock is paused (`is_paused = True`) and a 15-day cure window opens for the applicant institution.
> **Note on Governance**: Clause 1.8(f) governs the issuance of deficiency memos, but does **not** define an SLA clock freeze or a statutory 15-day cure window. The timer pause and 15-day cure duration are **system design choices (configurable)** implemented to ensure operational fairness so that institutional rectification delays do not penalize regional office processing metrics. When the applicant submits rectification documents, the clock unpauses and resumes from the exact recorded second.

### 4.3 Land Lease Rules & Proactive Early Warning Engine

The system enforces land lease rules with exact APH text provenance:
- **Chapter II Clause 2.1(e) (EoA Live Lease Cutoff Rule)**:
  Verbatim APH text:
  > *"In case of Institutions having Lease agreement for Land, the Council shall not issue EoA from the Year in which the Live Lease is equal to the number of years of the Course having the maximum duration. However, if such Institutions submit the Lease extended for a further 30  years, application shall be considered for EoA."*
  
  In own words: The Council withholds Extension of Approval (EoA) starting from the year in which the remaining live lease duration equals the duration of the longest course offered by the institution (e.g., 4 years for B.Tech). EoA is considered only if the institution submits a lease extended **for a further 30 years** (an additional 30 years, not merely "extended to 30 years").
- **Chapter VI Clause 6.17 (Registered Lease Deed Norm)**:
  Land required for the technical institution must be on a long-term registered lease for a **minimum period of 30 years**.
- **Mega/Metro Cities Lease Rule**:
  Any legacy references to "20 years for Mega/Metro cities" are explicitly labeled in code, UI, and documentation as `"unsourced assumption, configurable"` (as Clause 6.17 specifies 30 years).
- **Proactive Early Warning Alert**:
  - The engine continuously computes `years_remaining` against `threshold_course_duration_years`.
  - Triggers an `ALERT_EXPIRING_SOON` early warning 1 year prior to the block date.
  - Computes and surfaces the exact **EoA block date** to prompt proactive lease extension.

---

## 5. The 6 Signature Differentiators

The system contains 6 advanced differentiator engines designed to solve operational bottlenecks in technical education governance:

### Differentiator 1: Next-Best-Action Queue & Weighted Risk Score with Per-Factor Contributions
- **Location**: `NextBestActionQueueView.tsx` & `/api/v1/differentiators/next-best-action`
- **Mechanism**: Instead of basic First-In-First-Out (FIFO) processing, a multi-factor triage model calculates an urgency-risk priority score (0–100) based on:
  - SLA time remaining (40% weight)
  - Institutional compliance health score (25% weight)
  - Historical deficiency velocity (20% weight)
  - Student intake seat volume at risk (15% weight)
- **Explainability**: Integrated feature-attribution waterfall charts visualize factor contributions to explain exactly *why* a particular case was prioritized over others, eliminating black-box bias.

### Differentiator 2: APH-to-Rules Compiler with Provenance Graph & Verbatim Verification
- **Location**: `APHCompilerView.tsx` & `/api/v1/differentiators/aph-compiler`
- **Mechanism**: Parses regulatory prose from the AICTE Approval Process Handbook (APH) and compiles it into executable AST validation rules.
- **Traceability**: Every validation check, deficiency flag, and automated routing decision displays its exact regulatory provenance:
  > *Example: Chapter II Clause 2.1(e): EoA cutoff when live lease equals longest course duration; Chapter VI Clause 6.17: 30-year registered lease deed.*
- **Automated Verbatim Proximity Verification**:
  - Every seeded rule in `APH_CLAUSE_CATALOG` stores a verbatim text snippet from the official APH 2024–27 document.
  - The verification test suite (`test_aph_clause_verification.py`) reads the authentic 231-page `Approval process handbook.pdf` and verifies that each snippet occurs in close textual proximity to the cited clause number.
  - Includes negative tests confirming that invalid citations (e.g. citing the land lease rule under Clause 1.12 Security Deposit) fail CI.

### Differentiator 3: What-If Simulation Sandbox
- **Location**: `WhatIfSimulatorView.tsx` & `/api/v1/differentiators/what-if`
- **Mechanism**: Interactive Monte Carlo simulation laboratory allowing council leadership to stress-test policy changes before gazetting them:
  - *Sliders*: SLA deadlines (+/- days), scrutinizer staff capacity, projected application surge (% increase), deficiency rate tolerance.
  - *Outputs*: Live projected SLA breach probability, regional officer queue congestion curves, and estimated processing cost impacts.

### Differentiator 4: Hash-Chained Tamper-Evident Audit Ledger
- **Location**: `AuditLedgerView.tsx` & `/api/v1/audit/ledger`
- **Mechanism**: Implements a blockchain-inspired, append-only SHA-256 hash ledger:
  ```
  Block[n].curr_hash = SHA256(Block[n-1].curr_hash + actor_id + action + entity_id + timestamp + payload)
  ```
- **Integrity**: Any attempt by a database administrator or malicious actor to edit or delete a past decision breaks the mathematical hash chain. The ledger features a live **"Verify Chain Integrity"** button that computes mathematical proofs across all blocks.

### Differentiator 5: Security & Anti-Fraud Anomaly Detection
- **Location**: `SecurityAnomaliesView.tsx` & `/api/v1/differentiators/security-anomalies`
- **Detection Engines**:
  1. **Duplicate File Hash Fraud**: Flags across institutions sharing identical PDF hashes for distinct NOCs.
  2. **Impossible Inspection Travel**: Detects committee experts recorded at two distant campuses within hours.
  3. **Velocity Abuse**: Flags bulk approvals processed faster than human reading speed.
  4. **Pairwise SoD Rejection Ledger**: Audits and preserves all attempted SoD bypasses.

### Differentiator 6: Obligation Dependency, Intake Impact Graph & Lease Early Warning
- **Location**: `ComplianceView.tsx` & `/api/v1/compliance/obligation-dependencies/{id}`
- **Mechanism**: Maps statutory dependencies to prevent unauthorized institutional expansion:
  - *Live Case Study*: **Pinnacle Polytechnic College [Bengaluru Campus]** (PID: `1-10000003`).
  - *Cascade Trigger*: Expired 30-year Land Lease Deed (`LEASE-REG-1994-KAR-0921`).
  - *Automated Impact*: Extension of Approval (EoA) issuance is frozen, placing **360 student intake seats at risk** until registered lease renewal is submitted and verified.
  - *Early Warning Telemetry*: Displays remaining lease tenure, course duration threshold, and calculated EoA block date.

---

## 6. EVC Inspections Hub & Conflict-Free Panel Dispatch

- **Location**: `EVCView.tsx` & `/api/v1/evc/*`
- **Zero-Conflict Algorithm**:
  - Automatically filters an empanelled pool of verified academic experts (e.g. IIT, NIT professors).
  - Enforces three strict exclusion filters:
    1. **Regional Conflict**: Expert cannot inspect an institution located in their home state or current university zone.
    2. **Institutional History**: Expert cannot have served as faculty, consultant, or governing board member in the institution.
    3. **Reciprocal Conflict**: Prevents two institutions from cross-inspecting each other.
- **Inspection Dossier**: Enables digital upload of geo-tagged, timestamped site photos, architectural stability certificates, and verified faculty appointment registers and cadre qualifications as per APH norms.

---

## 7. AI Copilot & Natural Language Assistant

- **Location**: Global Floating Copilot widget in bottom right corner.
- **Capabilities**:
  - **Statutory Queries**: Instant semantic lookup across APH 2024–27 clauses.
  - **Docket Generation**: Generates formal executive inspection summaries and deficiency intimations with one click.
  - **Suggested Prompt Chips**: Context-aware prompts tailored to the user's active page and role.
  - **Human-in-the-Loop Guardrail**: All AI-generated text is labeled as draft advisory and requires formal officer sign-off before entering legal records.

---

## 8. Database Architecture & Schema Specifications

The database schema encapsulates 14 relational tables:

```
┌──────────────────┐       1:N       ┌──────────────────┐
│   Institutions   ├─────────────────┤   Applications   │
│  (PID, Category) │                 │  (Pipeline, SLA) │
└────────┬─────────┘                 └────────┬─────────┘
         │                                    │
         ├──────────────┐                     ├──────────────┐
         │ 1:N          │ 1:N                 │ 1:N          │ 1:N
┌────────▼─────────┐ ┌──▼───────────────┐ ┌───▼─────────┐ ┌──▼─────────┐
│ Institutional    │ │ Time-Bound       │ │ Application │ │ Case Events │
│ Documents (NOCs) │ │ Undertakings     │ │ Stages      │ │ (Immutable) │
└──────────────────┘ └──────────────────┘ └─────────────┘ └─────────────┘
                                                      
┌───────────────────────────────────────────────────────────────┐
│                   Append-Only Audit Ledger                    │
│   (prev_hash, curr_hash, actor, action, timestamp, metadata)  │
└───────────────────────────────────────────────────────────────┘
```

1. **`institutions`**: Permanent ID (PID), name, address, category, compliance health score, region foreign key.
2. **`regions`**: 7 Regional offices (SWRO, SRO, WRO, NRO, ERO, CRO, NWRO) + HQ.
3. **`applications`**: Application number, institution ID, pipeline type, current stage, submitter, verifier, approver, SLA deadline, status.
4. **`application_stages`**: Stage sequence order, stage name, status (PENDING, ACTIVE, PASSED, DEFICIENT), SLA days allotted.
5. **`case_events`**: Immutable event stream of all status changes, reverts, and cures with APH clause references.
6. **`document_types`**: Configurable registry of statutory documents (Land Lease, Fire NOC, Building Stability, Affiliation).
7. **`institutional_documents`**: Registered document number, SHA-256 binary hash, issue date, expiry date, RAG status.
8. **`time_bound_undertakings`**: Conditions requiring time-bound fulfillment (e.g. faculty cadre recruitment within 180 days).
9. **`evc_panels` & `evc_assignments`**: Empanelled expert committees, conflict declarations, inspection dates, status.
10. **`audit_trail`**: Genesis-linked SHA-256 hash chain recording every read, write, advance, and SoD rejection.

---

## 9. Verification & Operational Health Check

Both development runtimes are configured and operational:

| Service | Address | Daemon Process | Health Check Route |
| :--- | :--- | :--- | :--- |
| **FastAPI Backend** | `http://127.0.0.1:8000` | Uvicorn with `--reload` | `GET /api/v1/health` (HTTP 200 OK) |
| **Next.js Frontend** | `http://localhost:3000` | Node.js Next Dev Server | Active HTTP 200 Shell |
| **Public Outsider Verifier** | `http://localhost:3000/verify` | Next.js Public Route | Unauthenticated Hash Verification (HTTP 200 OK) |
| **Mailpit SMTP Testing** | `http://localhost:8025` | Mailpit Container | Web UI & HTTP API (Port 1025 SMTP) |
| **MinIO Storage Adapter** | `http://localhost:9001` | MinIO Container | Web Console (Port 9000 S3 API) |
| **Automated Test Suite** | Backend CLI | Pytest Suite | `112 passed, 5 skipped (117 tests across 19 modules) in ~17s` |

### Comprehensive Test Suite Breakdown (117 Automated Tests across 19 Modules — 112 Passed, 5 Skipped)

1. **APH Clause Verification (`test_aph_clause_verification.py` - 13 tests passed)**:
   - Validates authenticity of 231-page `Approval process handbook.pdf`.
   - Seeded rules verbatim proximity check ensuring each snippet is found in textual proximity to cited clause.
   - Negative test: Asserts citing land lease under Clause 1.12 fails CI, while Chapter II Clause 2.1(e) passes.
   - Enforces Chapter II Clause 2.1(e) (EoA considered if lease extended "for a further 30 years") & Chapter VI Clause 6.17 (30-year registered lease deed).
   - Validates configurable early-warning offsets (default 12/6/3 months before EoA block date) and lease-expiry alerts.
   - Validates dynamic Table 2.3 stage path (filtering SAC only for appeals, SHC only for compliance verification).
   - Verifies Clause 1.8(g) Re-Scrutiny scope restriction.
   - Verifies Clause 2.23.3 SHC compliance verification & Clause 1.11(a) / 2.24(a) SAC 7-day appeal window against Executive Committee decisions.
   - Verifies Clause 2.25(f) Security Deposit penalties & Clause 2.25(j) academic calendar cutoff.
   - Decision flow authority matrix: Committees recommend -> Executive Committee decides -> Council ratifies (Member Secretary is not final approver).
   - Validates all 21 Chapter II application types in Table 2.3, separation of Chapter I for New Institutions, and split of EoA into `EOA_SELF_DISCLOSURE` and `EOA_AFTER_BREAK`.
2. **APH Compiler Lifecycle, Quoting & Copilot (`test_aph_compiler_and_claims.py` - 5 tests passed)**:
   - APH compiler 5-step lifecycle: upload -> LLM draft -> diff view -> human approval -> versioned activation.
   - Automatic quote verifier against page-aware PDF text extracted via `pypdf`.
   - Verifies that any candidate rule with wrong citations or tampered quotes is marked `UNVERIFIED` and rejected at approval gate (`HTTP 400 Bad Request`).
   - Verifies fallback to `"OFFLINE DETERMINISTIC EXTRACTOR"` when no API key is set.
   - Validates Copilot BM25 probabilistic retrieval and weak-evidence guard returning `"not found in APH"` with 0 citations.
3. **Outsider-Verifiable Audit & Daily Merkle Roots (`test_audit_verification.py` - 5 tests passed)**:
   - Binary SHA-256 Merkle root computation (`seal_daily_merkle_root`).
   - Exported report hash and audit chain head registration in `exported_reports_registry`.
   - Public outsider verification endpoint (`/public-verify`) proving authentic provenance with **zero confidential applicant PII**.
   - Negative tamper tests proving forged chain heads and altered document hashes are rejected.
4. **Code Cleanup, Fictional Personas & Scope (`test_cleanup_and_scoping.py` - 3 tests passed)**:
   - Asserts fictional names only in seeded users and personas (no real council officials).
   - HQ treated as Bureau Scope (`region_id = None`), not a geographic region.
   - Asserts zero local absolute paths in documentation.
5. **Compliance Registry, Lease OCR & Adapters (`test_compliance_and_adapters.py` - 7 tests passed)**:
   - Document-Type registry CRUD with configurable alert offsets.
   - Land lease OCR extraction labeled as "simulated extraction on synthetic text" with field-level confidence scores.
   - Low-quality scan test case: Dropping confidence below 0.75 threshold withholds extraction and forces manual entry plus officer verification.
   - Human officer verification gate enforcing Separation of Duties ($Submitter \ne Verifier$).
   - DigiLocker and e-Sign labeled as "simulated connectors" (no Aadhaar claims; PKCS#7 envelope generation).
   - Legacy ERP / State portal application import adapter.
6. **Design System & WCAG AA Contrast (`test_contrast.py` - 1 test passed)**:
   - Automated mathematical verification that all 13 text/background token combinations satisfy WCAG AA contrast standards ($\ge 4.5:1$ normal, $\ge 3.0:1$ large/UI).
7. **Weighted Risk Score & Explainability (`test_copilot_and_risk_scorer.py` - 5 tests passed)**:
   - Grounded clause citations and context-specific Copilot query assistance.
   - `test_risk_score_factor_contributions_waterfall`: Feature-attribution waterfall chart contributions for prioritization.
   - `test_next_best_action_embedded_risk_factors`: Next-Best-Action queue factor breakdowns.
8. **Scripted Scenario & Time Travel (`test_demo_scenario.py` - 3 tests passed)**:
   - Time Travel virtual clock control, drift calculation, and reset.
   - Individual step verification for all 8 regulatory lifecycle stages.
   - One-click full scripted scenario end-to-end execution.
9. **Real SMTP Email Notification Channel (`test_email_smtp_channel.py` - 5 tests passed)**:
   - Real SMTP email transmission via Mailpit test server.
   - Exponential backoff retries and failure state tracking.
   - Quiet hours deferral (22:00 to 06:00).
   - Per-recipient delivery receipt logging in the SHA-256 audit ledger.
   - Explicit labeling of simulated SMS and WhatsApp mock channels.
10. **EVC Panel Conflict-of-Interest & Load Balancing (`test_evc_panel_conflicts.py` - 5 tests passed)**:
    - Exclusion Rule 1: Same home state conflict (Annexure-16 Clause 16.5).
    - Exclusion Rule 2: Prior review cooling period (default 24 months).
    - Exclusion Rule 3: Double-booking guard in `confirm_evc_schedule` raising `HTTP 400 Bad Request`.
    - Expert load balancing across active inspection assignments.
    - RFC 5545 iCalendar (`.ics`) schedule export.
11. **JWT Security, Expiry, MFA & Demo Gating (`test_jwt_and_demo_mode.py` - 9 tests passed)**:
    - Loads secret key from `JWT_SECRET` environment variable.
    - Pinned `HS256` algorithm strictly rejecting `alg=none` and untrusted algorithms.
    - Session expiration timestamps (`exp`) enforced; expired tokens rejected with 401.
    - Signature tampering detection and rejection.
    - Server-side MFA verification enforced before any access token is issued.
    - `DEMO_MODE` gating: TOTP `123456`, `/personas`, and `/demo-token/{role}` (alias `/demo-switch-token/{role}`) return 403 in production mode.
    - `DEMO_MODE` defaults to `false`.
    - Fast-fail startup check: Raises `RuntimeError` if `JWT_SECRET` is unset in non-demo mode.
    - Public status-lookup OTP `123456` gated behind `DEMO_MODE` (returns 403 when false).
12. **Multilingual Institution Alerts (`test_multilingual_alerts.py` - 5 tests passed)**:
    - Static reviewed template catalog across English, Hindi, and Tamil with exact clause citations and due dates.
    - Rendering deficiency notices with variable interpolation across all three languages.
    - Fallback to English on unsupported or untranslated languages.
    - Updating institution language preference (`PUT /institutions/{id}/language`).
    - Localized alert dispatch using institution preference.
13. **PostgreSQL Native RLS Testbed (`test_postgres_rls.py` - 1 passed, 5 skipped)**:
    - Evaluates native row-level security policies against PostgreSQL when an active server is provided.
    - Reporting status: **RLS enforced by ScopedDAL in dev; Postgres policies specified in schema_rls_postgres.sql** (1 passed, 5 skipped when local PostgreSQL instance is inactive).
14. **Reports Export & Impact Metrics (`test_reports_export.py` - 6 tests passed)**:
    - Default-deny on unauthenticated export calls.
    - Binary PDF-1.4 report generation with tamper-evident audit ledger stamping.
    - Genuine Excel (.xlsx) OpenXML workbook generation verified via openpyxl and PK zip headers.
    - Operational impact metrics calculation: reminders sent automatically, escalations fired on time, follow-ups avoided, and officer-hours saved with explicit assumptions shown.
15. **Row-Level Security, AST Scoping & SoD (`test_rls_and_sod.py` - 20 tests passed)**:
    - Real HTTP requests via `TestClient` + JWT bearer tokens; client-forged headers stripped and ignored.
    - Default-deny scoping (empty context returns zero rows).
    - Cross-region read blocks and cross-institution write blocks.
    - Committee member scoping (experts see only assigned EVC panels).
    - Auditor read-only enforcement (mutations raise `SecurityScopeError`).
    - Pairwise Separation of Duties ($Submitter \ne Verifier \ne Approver$ and $Requester \ne Approver$).
    - Cryptographic SHA-256 hash chain continuity.
    - AST static analysis: Asserts zero router queries execute outside `ScopedDAL`.
16. **Roles, Tracking & Notifications (`test_roles_and_tracking.py` - 3 tests passed)**:
    - Role-based JWT scoping and dynamic sidebar navigation.
    - Multi-channel notification delivery logs (In-App, Email, SMS).
    - Public status lookup and Table 2.3 timeline visualization.
17. **SLA Escalation Engine (`test_sla_escalation.py` - 4 tests passed)**:
    - Working-day calendar calculation (omits weekends and public holidays).
    - SLA RAG status classification (ON_TRACK, WARNING, CRITICAL, BREACHED).
    - Hierarchical escalation ladder ($L_1 \to L_2 \to L_3 \to L_4$).
    - Time-travel simulator (+1d, +7d, +30d).
18. **Workflow Intake & State Machine (`test_workflow_intake.py` - 3 tests passed)**:
    - Table 2.3 pipeline determination and stage validation.
    - Deficiency revert and paused SLA clock (design choice, configurable).
    - Isolated AI draft in `llm_drafts` and mandatory human approval gate.
19. **Deterministic Breach Forecasting (`test_workload_forecasting.py` - 6 tests passed)**:
    - Mathematical queueing model with holiday calendar projection and backlog delay.
    - Dynamic holiday shifting of projected completion dates.
    - Staffing shocks simulation (reduced inspectors increases delay).
    - Deterministic Monte-Carlo simulation with fixed seed producing P10/P50/P90 probability bands.
    - Application forecast API and What-If simulation workload integration.

### Key Developer Commands
```powershell
# 1. Run Automated Backend Pytest Suite (117 tests across 19 modules: 112 passed, 5 skipped)
python -m pytest backend/tests/ -v

# 2. Run Automated WCAG AA Contrast Test
python -m pytest backend/tests/test_contrast.py -v

# 3. Start Production Services via Docker Compose
docker-compose up --build

# 4. Start Local Development Services
# Terminal 1: Backend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
# Terminal 2: Frontend
cd frontend
npm run dev
```

---

*Authored for AICTE National Technical Education Portal • Designed in accordance with APH 2024–27 & DPDP principles.*

