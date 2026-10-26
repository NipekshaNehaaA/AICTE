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
- **Append-Only Cryptographic Audit Trail:** Non-repudiable SHA-256 hash-chained ledger guaranteeing complete auditability with daily Merkle roots.
- **Real Storage & Identity Infrastructure:** S3-compatible MinIO and local filesystem storage with magic-byte (`%PDF-1.4`) verification, SHA-256 on-read tamper detection, real self-service accounts with SMTP email verification, and unauthenticated public tracking with safe non-PII fields.

> For deep-dive technical evaluations and answers to common hackathon panel queries (e.g., *"Why not pure LLM?"*, *"How do you prevent hallucinations?"*, *"What stops a rogue regional officer?"*), see the dedicated [Judge FAQ Document](docs/judge_faq.md).

---

## 2. System Architecture & Signature Differentiators

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FRONTEND (Next.js 14 + TS)                             │
│       Cherry Blossom Surfaces & Ink Wash Neutrals (100% WCAG AA Contrast Passed)       │
│  ┌──────────────────────┬──────────────────────┬────────────────────────────────────┐  │
│  │ Stakeholder Views    │ Real-Time Dashboards │ 5 Signature Differentiators        │  │
│  │ • Institution Portal │ • SLA & Aging RAG    │ #1 APH-to-Rules Compiler Diff View │  │
│  │ • Single Case Docket │ • Bottleneck Heatmap │ #2 Next-Best-Action Priority Queue │  │
│  │ • Regional Officer   │ • Workload Balance   │ #3 What-If Scenario Simulator      │  │
│  │ • EVC Committee View │ • Live Audit Chain   │ #4 Time-Travel Clock (+1/+7/+30d)  │  │
│  │ • Bureau Head / HQ   │ • Public Tracking    │ #5 Outsider-Verifiable Audit Chain │  │
│  └──────────────────────┴──────────────────────┴────────────────────────────────────┘  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │ REST / SSE
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                BACKEND (FastAPI + Python 3.11/3.12)                    │
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
│  │ Ingestion & Storage │        │ Notification Engine │        │ Hash-Chained Audit  │ │
│  │ • MinIO / Local S3  │        │ • APScheduler Clock │        │ • SHA-256 prev_hash │ │
│  │ • Magic-Byte %PDF   │        │ • Real Mailpit SMTP │        │ • Daily Merkle Roots│ │
│  │ • Tamper Rechecking │        │ • Twilio WhatsApp   │        │ • Non-repudiation   │ │
│  │ • Version Retain    │        │ • Multilingual Alert│        │ • Public Verifier   │ │
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
│  • Development: Scoped Data Access Layer (DAL) with default deny & AST query enforcement│
│  • Storage Adapter: Swappable MinIO S3 & Local with SHA-256 re-verification on-read   │
│  • Append-Only Audit Ledger: Immutable SHA-256 cryptographic chain                     │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### The 5 Signature Differentiators
1. **Differentiator #1: APH-to-Rules Compiler Diff View** — Upload the 231-page APH PDF; deterministic chunking and LLM verifier extract statutory rules with mandatory verbatim proximity proof against source pages. Any discrepancy is tagged `UNVERIFIED` and blocked from activation.
2. **Differentiator #2: Next-Best-Action Work Queue Priority with Risk Factor Attribution** — Dynamically sorts pending applications by composite breach probability $\times$ sanctioned intake volume. Surfaces feature-attribution waterfall breakdowns (e.g., Land Title ambiguity $+32\%$, High Intake $+18\%$) so officers address highest-risk bottlenecks first.
3. **Differentiator #3: Realistic What-If Scenario Simulator** — Simulates policy shifts (e.g. $+30\%$ application surge, $-20\%$ regional officer staff capacity, or 10-day scrutiny deadline compression) with baseline comparison and deterministic Monte Carlo P10/P50/P90 probability bands.
4. **Differentiator #4: Virtual Time-Travel Clock Simulator** — Fast-forwards system time by $+1$, $+7$, $+15$, or $+30$ days to demonstrate working-day calendar calculations, cure period SLA pauses, and automatic multi-tier statutory escalations ($L_1 \to L_2 \to L_3$).
5. **Differentiator #5: Outsider-Verifiable Cryptographic Audit Ledger with Merkle Roots** — Binary SHA-256 hash chain sealed into daily Merkle roots. Public third parties can verify document authenticity and chain continuity at `/verify` with **zero disclosure of confidential institution PII**.

---

## 3. Authority-Boundary Matrix

| Action | Classification | Actor / Engine | Fallback / Safeguard | APH 2024-27 Reference |
| :--- | :--- | :--- | :--- | :--- |
| **Pipeline Routing** | **AUTO** | Deterministic Rules Engine | Configured APH Table 2.3 Matrix (21 Types) & Chapter I | Table 2.3 & Chapter I |
| **SLA Countdown & Pause** | **AUTO** | Rules Engine (Calendar-aware) | Pauses automatically in "Deficient / Cure" state | Design Choice, Configurable |
| **Escalation Notification** | **AUTO** | APScheduler ($L_1 \to L_2 \to L_3 \to L_4$) | Triggered when SLA breached; logged in tamper-evident audit | Chapter I Clause 1.10 |
| **Deficiency Letter Drafting** | **SUGGEST-ONLY** | LLM Engine | Stored in `llm_drafts`; must be reviewed & signed by Officer | Chapter I Clause 1.8 |
| **Document Field Extraction (OCR)** | **SUGGEST-ONLY** | OCR + LLM Extractor | Confidence $< 0.75$ forces manual entry; Officer verifies | Chapter VI Clause 6.17 |
| **Next-Best-Action Work Queue Ranking** | **SUGGEST-ONLY** | Heuristic Risk Model | Sorts by breach risk $\times$ student intake; non-binding | Section 8 Differentiator |
| **Document Anomaly Flags** | **SUGGEST-ONLY** | Anomaly Engine | Flags duplicate SHA-256 hashes & altered dates; Officer investigates | Chapter II Clause 2.3.5(b) |
| **Scrutiny Verification Decision** | **HUMAN-ONLY** | Authorized Scrutiny Committee | Mandatory officer digital signature & recorded reason | Chapter I Clause 1.8 |
| **EVC Inspection Verdict** | **HUMAN-ONLY** | Expert Visit Committee (EVC) | On-site/virtual report verification with geotag confirmation | Chapter I Clause 1.9 |
| **Approval / Rejection Order** | **HUMAN-ONLY** | Competent Authority (HQ/Council) | Legally binding decision reserved for designated statutory officers | Chapter I Clause 1.10 |

---

## 4. Design System: Cherry Blossom Surfaces + Ink Wash Text

Adheres strictly to the **Cherry Blossom & Ink Wash** tokens with **100% WCAG AA contrast compliance** (verified mathematically via automated tests):
- **Surfaces:** `--blossom-100` (`#F2C7C7`), `--blossom-300` (`#FFB7C5`), `--mint-100` (`#D5F3D8`), `--white` (`#FFFFFF`), `--ivory` (`#FFFFE3`).
- **Text & Neutrals:** `--text` (`#4A4A4A`), `--text-strong` (`#2E2E2E`), `--text-muted` (`#55687C` on white/ivory), `--slate` (`#6D8196`), `--line` (`#CBCBCB`).
- **Status & Actions:** `--blossom-600` (`#C2456B`), `--blossom-700` (`#9E3256`), `--mint-700` (`#26693D`), `--amber-100`/`--amber-700`, `--rose-100`/`--rose-700`.
- **Statutory Banners:** *"AI draft. Decision reserved for the competent authority."* & *"Sample value, configurable pending APH 2024-27 compilation."*

---

## 5. Quick Start & Execution

### Option A: One-Command Docker Compose (Recommended for Evaluators)
```bash
docker-compose up --build
```
*Spins up all container services seamlessly:*
- **Frontend Governance Portal & Single Case Docket:** `http://localhost:3000`
- **Backend FastAPI API & OpenAPI Swagger Docs:** `http://localhost:8000/docs`
- **Public Outsider Verifier (Zero PII):** `http://localhost:3000/verify`
- **Mailpit Real SMTP Testing Web UI:** `http://localhost:8025` (SMTP on port `1025`)
- **MinIO S3 Object Storage Console:** `http://localhost:9001` (S3 API on port `9000`)
- **Redis Cache & Coordination:** Port `6379`

### Option B: Local Dual-Process Dev Startup (Python + Next.js)
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

### Environment Configuration Reference

| Environment Variable | Default (Dev) | Production Recommended | Description |
| :--- | :--- | :--- | :--- |
| `JWT_SECRET` | Required | 64+ char random string | Secret key for HMAC-SHA256 tokens. Server fails fast if missing/weak. |
| `DEMO_MODE` | `false` | `false` | When `true`, enables demo OTP `123456` and `/api/v1/auth/demo-token/*`. Strictly forbidden in production. |
| `EVALUATOR_MODE` | `false` | `false` | Runtime toggle gating 1-click persona switchers, time travel clock, and sample data badges. |
| `STORAGE_BACKEND` | `local` | `minio` | Swappable file storage backend (`local` or `minio`). |
| `LOCAL_STORAGE_DIR` | `./storage/documents` | N/A | Storage directory for local filesystem storage adapter. |
| `MINIO_ENDPOINT` | `127.0.0.1:9000` | S3 / MinIO cluster host | Host endpoint for S3-compatible object storage. |
| `MINIO_ACCESS_KEY` | `minioadmin` | Encrypted secret | Object storage root access key. |
| `MINIO_SECRET_KEY` | `minioadmin` | Encrypted secret | Object storage root secret key. |
| `MINIO_BUCKET_NAME`| `aicte-documents` | `aicte-documents` | Destination S3 bucket name. |
| `SMTP_HOST` | `127.0.0.1` | Corporate SMTP Gateway | SMTP relay host for transactional emails. |
| `SMTP_PORT` | `1025` (Mailpit) | `587` / `465` | SMTP port. |
| `TWILIO_ACCOUNT_SID`| Optional | Live Twilio SID | Twilio account SID for WhatsApp notices (falls back to sandbox log). |
| `TWILIO_AUTH_TOKEN` | Optional | Live Twilio Auth | Twilio authorization token. |

---

## 6. Real Accounts & Demo Credentials Matrix

### Real Self-Service Accounts
The platform features genuine account creation and authentication workflows:
- **Institution Self-Signup:** Any institution can sign up at `/signup`. A verification token is generated and dispatched via SMTP (viewable in Mailpit). The account remains inactive until confirmed.
- **Admin Officer Provisioning:** Super Admin accounts can provision Regional and Bureau Officers with specific jurisdictional scopes (`region_id` or pan-India Council scope).
- **Password Reset Flow:** Full self-service password reset via email reset token at `/forgot-password`.
- **Brute-Force Protection:** Automatically locks accounts for 15 minutes after 5 consecutive failed login attempts.
- **JWT Refresh Rotation:** Issuance of short-lived access tokens and single-use rotating refresh tokens.

### Pre-Seeded Evaluation Personas
When `DEMO_MODE=true` or in sandbox environments, pre-seeded personas can be used for instant evaluation:

| Role | Jurisdiction / Scope | Name & Role Office | Email | Password |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | Council Authority (Pan-India) | Dr. Arvind Ramanathan (Member Secretary) | `member.secretary@aicte-india.org` | `DemoPassword@123` |
| **Bureau Head** | Bureau Scope (Pan-India) | Dr. M. S. Jayaprakash (Bureau Head) | `bureau.head@aicte-india.org` | `DemoPassword@123` |
| **Bureau Officer** | Bureau Scope (Pan-India) | Shri Anand K. Sharma (Approval Bureau Officer) | `approval.bureau@aicte-india.org` | `DemoPassword@123` |
| **Regional Director** | SWRO (Regional Director) | Dr. K. S. Sitaram (Regional Director - SWRO) | `rd.swro@aicte-india.org` | `DemoPassword@123` |
| **Regional Officer** | SWRO (Bengaluru) | Dr. Regional Officer (SWRO - Bengaluru) | `ro.swro@aicte-india.org` | `DemoPassword@123` |
| **Scrutiny Member** | SWRO (Bengaluru) | Prof. N. Meenakshi (Scrutiny Committee Member) | `scrutiny.member@aicte-india.org` | `DemoPassword@123` |
| **Committee Member** | SWRO (Bengaluru) | Prof. EVC Expert (SWRO Inspection Panel) | `expert.swro@aicte-india.org` | `DemoPassword@123` |
| **SAC/SHC Member** | Standing Appellate (Pan-India) | Justice (Retd.) K. V. Narayanan (SAC Member) | `sac.appellate@aicte-india.org` | `DemoPassword@123` |
| **Statutory Auditor**| Council Scope (Read-Only) | Smt. Priya Balan (Statutory Compliance Auditor)| `auditor.compliance@aicte-india.org` | `DemoPassword@123` |
| **Institution User** | SWRO (PID 1-10000001) | Dr. Principal (Apex Institute of Technology) | `principal.110000001@fictional-aicte.edu.in` | `DemoPassword@123` |

*MFA Demo Verification Code:* `123456` (active only when `DEMO_MODE=true`).

---

## 7. Demonstration Scripts & Real-Clock Walkthroughs

The platform provides two complementary walkthrough methodologies:

1. **Production Real-Clock 7-Step Walkthrough (`EVALUATOR_MODE=false`):**
   - Detailed in [docs/demo_script_real_clock.md](docs/demo_script_real_clock.md).
   - Demonstrates the end-to-end statutory lifecycle under live production conditions:
     1. Technical institution submits application & 3-year lease deed (Doc v1).
     2. Regional Scrutiny Officer identifies Table 2.3 deficiency and reverts; **statutory SLA clock pauses**.
     3. Institution cures deficiency by uploading 30-year lease extension (Doc v2); **Doc v1 marked SUPERSEDED**, clock unpauses.
     4. Regional Officer verifies Re-Scrutiny scope (Clause 1.8(g)) and confirms conflict-free EVC panel with `.ics` export.
     5. Empanelled Cross-State Committee Member declares absence of conflict (Annexure-16 Clause 16.5) and submits geotagged report.
     6. Regional Director reviews docket and recommends for Council Ratification.
     7. Member Secretary issues final Approval Order with **Pairwise Separation of Duties ($Submitter \ne Verifier \ne Approver$)** and validates cryptographic SHA-256 hash continuity.

2. **Evaluator Mode Walkthrough (`EVALUATOR_MODE=true`):**
   - Enables the 1-Click Personas switcher, Virtual Time-Travel Clock (`+1d`, `+7d`, `+15d`, `+30d`), and scripted scenario demo engine.
   - For complete answers to technical evaluation panel queries, see the [Judge FAQ Document](docs/judge_faq.md).
   - For live Twilio WhatsApp and SMTP verification instructions, see [docs/channels_verification.md](docs/channels_verification.md).

---

## 8. Test Suite Verification (100% Passing)

The entire platform is backed by **162 backend automated tests across 26 test modules** (**157 passed, 5 skipped** for native Postgres RLS in SQLite dev mode, **0 failures**), **15 Playwright E2E tests (100% passed)**, and **13/13 WCAG AA contrast tokens passed**.

```bash
# 1. Run full backend pytest suite (157 passed, 5 skipped)
python -m pytest backend/tests/ -v

# 2. Run real-clock 7-step story integration test
python -m pytest backend/tests/test_real_clock_7step_story.py -v

# 3. Run automated WCAG AA contrast ratio verification (13/13 passed)
python -m pytest backend/tests/test_contrast.py -v

# 4. Run full Playwright E2E test suite (15 passed)
cd frontend
npx playwright test
### Verified Test Categories (162 Automated Tests across 26 Modules):
1. **Real-Clock 7-Step Story (`test_real_clock_7step_story.py` - 1 test):** End-to-end statutory proof under `EVALUATOR_MODE=false`: Submitter intake $\to$ Scrutiny revert & paused SLA clock $\to$ 30-year lease cure & superseded versioning $\to$ Re-scrutiny verification $\to$ Conflict-free EVC panel & RFC 5545 `.ics` export $\to$ Conflict declaration & geotagged report $\to$ Regional Director ratification $\to$ Member Secretary final approval & unbroken SHA-256 audit continuity.
2. **Zero Demo Leaks under Production (`test_no_demo_leaks_when_evaluator_off.py` - 7 tests):** Asserts zero mentions of "Demo", "123456", or "Evaluator Mode" in login, error, and OTP responses when `EVALUATOR_MODE=false`. Asserts real SHA-256 email OTP for public tracking.
3. **Officer TOTP Enrollment & Production Auth (`test_totp_enrollment_and_non_demo_auth.py` - 9 tests):** Validates officer TOTP setup, encrypted Fernet storage, single-use emergency recovery codes, replay window protection, and audited admin MFA resets.
4. **Document Versioning & Superseded Documents (`test_superseded_documents.py` - 4 tests):** Validates that renewed documents mark previous versions as `SUPERSEDED`, retain downloadability, and are excluded from scheduler expiry scans.
5. **APH PDF Verbatim Proximity Verification (`test_aph_clause_verification.py` - 13 tests):** Validates authenticity of 231-page `Approval process handbook.pdf`. Seeded rules verbatim proximity check ensures each snippet is found in textual proximity to cited clause. Negative test proves wrong citation fails CI. Enforces Chapter II Clause 2.1(e) and Chapter VI Clause 6.17 (30-year registered lease deed) with early-warning offsets.
6. **APH Compiler Lifecycle & Quoting (`test_aph_compiler_and_claims.py` - 8 tests):** Tests the 5-step compiler lifecycle: upload $\to$ LLM draft $\to$ diff view $\to$ human approval $\to$ versioned activation. Validates quote verifier, confirms fallback to `"OFFLINE DETERMINISTIC EXTRACTOR"` when no API key is configured, and validates Copilot BM25 weak-evidence guards.
7. **Outsider-Verifiable Audit & Merkle Roots (`test_audit_verification.py` - 5 tests):** Tests binary SHA-256 daily Merkle root computation (`seal_daily_merkle_root`), report registration, public outsider verification (`/public-verify`) with zero PII disclosure, and negative tamper detection against forged chain heads.
8. **Single Case Docket & Public Status Portal (`test_case_page_and_public_tracking.py` - 3 tests):** Validates single case docket completeness (owner, stage timeline, SLA clock with pause indicator, documents with download/versions, undertakings, 30-year lease expiry, alerts sent with delivery status, EVC details, workload forecast P10/P50/P90, filtered audit ledger); validates unauthenticated rate-limited public tracking portal (`/public/track/{tracking_id}`) with safe non-PII fields.
9. **Code Cleanup, Fictional Personas & Scope (`test_cleanup_and_scoping.py` - 4 tests):** Asserts fictional names only in seeded users and personas. Asserts HQ is treated as Bureau Scope (`region_id = None`), not a geographic region. Asserts zero local absolute paths in documentation. Asserts tests run on isolated temporary databases.
10. **Compliance Registry, Lease OCR & Adapters (`test_compliance_and_adapters.py` - 7 tests):** Tests Document-Type registry CRUD, lease deed OCR extraction with field-level confidence scores, low-quality degraded scan fallback (< 0.75 forces manual entry), officer verification gate with SoD, and DigiLocker/e-Sign simulated connectors.
11. **WCAG AA Contrast Ratios (`test_contrast.py` - 1 test):** Automated mathematical verification that all 13 text/background token combinations in the Cherry Blossom design system satisfy WCAG AA contrast standards ($\ge 4.5:1$ normal, $\ge 3.0:1$ large/UI).
12. **Copilot Grounding & Risk Scorer (`test_copilot_and_risk_scorer.py` - 5 tests):** Grounded clause citations and context-specific Copilot query assistance. Tests feature-attribution waterfall chart contributions and Next-Best-Action queue factor breakdowns.
13. **Scripted Scenario & Time Travel (`test_demo_scenario.py` - 3 tests):** Validates virtual clock warp (`+1d`, `+7d`, `+15d`, `+30d`, reset), individual execution of all regulatory steps, and 1-click full scripted scenario run.
14. **Real SMTP Email Notification Channel (`test_email_smtp_channel.py` - 5 tests):** Validates real SMTP transmission via Mailpit, exponential backoff retries on transmission failure, quiet hours deferral (22:00–06:00), per-recipient delivery receipt logging in the SHA-256 audit ledger, and explicit labeling of simulated SMS/WhatsApp mock channels.
15. **EVC Panel Conflict-of-Interest & Load Balancing (`test_evc_panel_conflicts.py` - 5 tests):** Validates statutory exclusion rules (same home state, 24-month cooling period, double-booking guard in `confirm_evc_schedule`), expert load-balancing, and RFC 5545 `.ics` calendar export.
16. **Real Storage & Authenticated Downloads (`test_file_storage_and_downloads.py` - 8 tests):** Tests swappable local and MinIO storage adapters, path traversal sanitization, magic-byte (`%PDF-1.4`) validation, SHA-256 calculation, document versioning on renewal, authenticated download with on-read SHA-256 tamper rechecking (rejects bitflips with HTTP 409), and cross-region download authorization.
17. **JWT Cryptographic Hardening & Demo Mode (`test_jwt_and_demo_mode.py` - 10 tests):** Rejects `alg=none`, enforces token expiry, secret from env (`JWT_SECRET`), and enforces server-side MFA verification before token issuance. `DEMO_MODE` defaults to `false`. Startup fails fast with `RuntimeError` without `JWT_SECRET` in non-demo mode.
18. **Multilingual Institution Alerts (`test_multilingual_alerts.py` - 5 tests):** Validates static template catalogs across English, Hindi, and Tamil with exact statutory clause citations and deadlines. Validates fallback to English on unsupported languages, institution language preference updates, and dispatching localized notices.
19. **Full Persona E2E Lifecycles (`test_persona_e2e_suite.py` - 4 tests):** Validates full Persona E2E journeys: Institution user submit/cure/resubmit, Regional Officer scrutiny & deficiency issuance, Auditor read-only & hash chain verification, Super Admin officer provisioning and evaluator mode toggling.
20. **PostgreSQL Native RLS Testbed (`test_postgres_rls.py` - 6 tests: 1 passed, 5 skipped):** Evaluates native database-level RLS policies against PostgreSQL. In dev environments, the testbed explicitly reports: **"RLS enforced by ScopedDAL in dev; Postgres policies specified"**.
21. **Real Accounts, Email Verification & Evaluator Mode (`test_real_auth_and_evaluator_mode.py` - 5 tests):** Validates self-service institution signup with SMTP verification token, password reset flow with secure token, JWT refresh token rotation, Super Admin officer provisioning, and runtime Evaluator Mode toggling.
22. **Reports Export & Impact Metrics (`test_reports_export.py` - 6 tests):** Tests binary `%PDF-1.4` headers, genuine Excel (.xlsx) OpenXML workbook generation verified via openpyxl and PK zip headers, SLA breach audits, tamper-evident audit ledger stamping, and operational impact metrics.
23. **HTTP Client & ScopedDAL Enforcement (`test_rls_and_sod.py` - 21 tests):** Real HTTP requests with `TestClient` + JWT bearer tokens assert that forged `x-user-*` headers are stripped; role/user are derived strictly from JWT claims. AST static analysis test verifies zero database queries execute outside `ScopedDAL`. Default deny, cross-region read blocks, cross-institution write blocks, committee scoping, auditor read-only enforcement, and pairwise SoD are strictly verified.
24. **Roles, Tracking & Notifications (`test_roles_and_tracking.py` - 3 tests):** Role-based JWT scoping and dynamic sidebar navigation. Multi-channel notification delivery logs (In-App, Email, SMS).
25. **Scheduler Engine & Real Channels (`test_scheduler_and_real_channels.py` - 7 tests):** Validates APScheduler real clock catch-up, T-90/60/30/7/overdue statutory triggers, real SMTP Mailpit delivery, Twilio WhatsApp sandbox adapter, multilingual templates, and idempotent alert dispatch.
27. **Security Regressions & Defect Attacks (`test_security_regressions.py` - 8 tests):**
    - `test_regression_defect_1_production_evaluator_mode_toggle_rejected`: Proves evaluator mode cannot be toggled at runtime in production; anonymous and normal user toggle attempts return HTTP 404; demo tokens and MFA 123456 bypass remain strictly rejected; `/system/mode` returns only `{"evaluator_mode": false}`.
    - `test_regression_defect_6_boot_refusal_when_production_and_demo_flag`: Proves process startup unconditionally aborts (`RuntimeError`) if `ENV=production` while `DEMO_MODE` or `EVALUATOR_MODE` is enabled.
    - `test_regression_defect_2_password_reset_security`: Proves `/auth/forgot-password` returns identical 200 responses for real and non-existent accounts; never leaks reset tokens over HTTP; delivers tokens strictly via outbound email outbox; verifies token is single-use and hashed with SHA-256; proves expired tokens fail; proves password reset increments `token_version` to immediately revoke existing sessions; asserts immutable audit logging.
    - `test_regression_defect_3_signup_email_verification_security`: Proves `/auth/signup` never exposes `verification_token` in HTTP response; duplicate email returns identical success message without revealing account existence; unverified accounts cannot log in (HTTP 403); verification link works exactly once.
    - `test_regression_defect_7_brute_force_rate_limiting`: Proves brute-force attempts against password reset and signup trigger HTTP 429 Too Many Requests and are logged to the audit ledger.
    - `test_regression_defect_4_production_demo_users_disabled_and_rejected`: Proves that when booting in production, existing seeded demo users are automatically disabled (`is_active=False`); logging in with default password `DemoPassword@123` fails for all accounts; startup self-check aborts boot if any active account matches a known default password hash.
    - `test_regression_defect_5_admin_first_login_password_change_enforced`: Proves administrative first-login issues a restricted token permitting ONLY `POST /auth/change-password` (all other APIs return HTTP 403); weak (<12 chars), breached, identical-to-email, or unchanged passwords are rejected; valid password change revokes old session and unlocks full administrative access.
    - `test_regression_defect_8_e2e_json_response_leak_scan`: E2E probe scanner scanning all JSON responses across production endpoints asserting 0 occurrences of `"reset_token"`, `"verification_token"`, `"123456"`, or `"DemoPassword"`.
28. **Playwright Production Login Integrity (`frontend/e2e/production-login-integrity.spec.ts` - 1 test):** Browser E2E proof verifying that in production mode, the public login page renders 0 evaluator toggles, 0 banner buttons, 0 demo persona quick-fills, and clicking around cannot enable demo capabilities.

---

## 9. Mock vs. Real Architecture Matrix

| Architectural Subsystem | Implementation in Workspace (Dev / Demo) | Production Specification | Architectural Classification |
| :--- | :--- | :--- | :--- |
| **Document Storage & Uploads** | **Real Swappable Storage (Local & MinIO S3)** with magic-byte (`%PDF-1.4`) verification, SHA-256 calculation, document versioning, and on-read tamper rechecking | **Production S3 / MinIO Object Storage** with server-side KMS encryption and object versioning | **Real Production Code** |
| **User Accounts & Authentication** | **Real Self-Service Signup, Email Verification via SMTP, Password Reset, Brute-Force Lockout, JWT Refresh Rotation, and Officer Provisioning** | **Production OpenID Connect / SAML / National Jan Parichay SSO Gateway** | **Real Production Code** |
| **Alert Scheduler & Background Jobs**| **Real APScheduler Real-Clock Worker** with catch-up, T-90/60/30/7 triggers, quiet hours deferral (22:00–06:00), and idempotent delivery | **Production Celery / Redis Worker Cluster** with distributed beat scheduler | **Real Production Code** |
| **Email Notification Channel** | **Real SMTP Client** with exponential backoff retries, quiet hours deferral, delivery receipts, and Mailpit integration | **Production SMTP / SES / SendGrid Gateway** | **Real Production Code** |
| **WhatsApp Notification Channel** | **Real Twilio WhatsApp Adapter** with sandbox fallback and multi-channel delivery tracking | **Production CDAC / NIC WhatsApp Business API** | **Real Production Code (Twilio Adapter with Sandbox Fallback)** |
| **Single Case Docket & Public Tracking**| **Real Single Case Docket** with owner, stage timeline, SLA clock, documents, undertakings, lease expiry, alerts, and workload forecast; **Real Rate-Limited Safe Public Portal** | **Enterprise Case Management System & National Public Portal** | **Real Production Code** |
| **Database Isolation & Scoping** | **Real ScopedDAL Engine** in SQLite dev environment with default-deny & AST static query verification (zero DB queries outside ScopedDAL) | **Native PostgreSQL Engine RLS** (`schema_rls_postgres.sql`) with session variables (`SET LOCAL app.current_user_id`) | **RLS enforced by ScopedDAL in dev; Postgres policies specified** |
| **APH Rules Engine** | **Real AST Compiler & RuleVersion Activation** verifying verbatim APH proximity and Table 2.3 routing | **Real AST Compiler & RuleVersion Activation** | **Real Production Code** |
| **Working-Day SLA & Escalation** | **Real Calendar Engine** omitting weekends & holidays; real L1->L2->L3 multi-tier escalation hierarchy | **Real Background Worker** with automated cron | **Real Production Code** |
| **Audit Ledger & Public Proofs** | **Real Cryptographic SHA-256 Hash Chain & Daily Merkle Roots** with real tamper detection and public zero-PII verifier (`/verify`) | **Real Append-Only Ledger / HSM / Immutable Cloud Table** | **Real Production Code** |
| **Workload & Breach Forecasting** | **Real Deterministic Queueing Model** with working-day calendar, gazetted holidays, and Monte-Carlo P10/P50/P90 simulation | **Distributed ML & Queue Analytics Pipeline** | **Real Production Code (Labeled 'forecast from workload model')** |
| **EVC Panel Allocation** | **Real Conflict-of-Interest Exclusion Engine** (home state, 24m cooling, double-booking guard) + load balancing + RFC 5545 `.ics` export | **Council-Wide Inspection Scheduling Engine** | **Real Production Code** |
| **Multilingual Notification Engine**| **Real Static Template Catalog** across English, Hindi, and Tamil with exact clause citations and fallback logic | **Government Multilingual Notification Gateway** | **Real Production Code** |
| **Document OCR** | **Simulated extraction on synthetic text** with confidence metrics and low-quality scan fallback (< 75% forces manual entry) | **Production Tesseract / PaddleOCR Engine** with Sub-Registrar deed layout parsing | **Simulated extraction on synthetic text** |
| **DigiLocker Integration** | **Simulated Connector** returning synthetic certificates, URIs, and SHA-256 hashes | **Production National DigiLocker API Gateway** (MeitY India Stack) | **Simulated Connector** |
| **Digital e-Sign** | **Simulated Connector** generating synthetic PKCS#7 envelope tokens (no Aadhaar data stored) | **Production CCA-Licensed e-Sign Gateway** (CAdES / PKCS#7 envelope) | **Simulated Connector** |
| **SMS Messaging** | **Simulated Mock Channel** logging transmission payloads | **Production CDAC / NIC SMS Gateway** | **Simulated Mock** |
| **State Portal / ERP Ingestion** | **Simulated Connector** normalizing external applications into Table 2.3 pipelines | **Production State CET / DTE API Adapters** | **Simulated Connector** |
| **Report Generation** | **Real OpenXML (.xlsx) & PDF-1.4 Stream Generation** with cryptographic stamp and audit ledger registration | **Production Cloud Document Renderer** | **Real Production Code** |
| **Institutions & Applications** | **210 Deterministic Synthetic Records** across 7 Regional Corridors | **Production AICTE Portal / NSWS Enterprise Registry** | **Synthetic Data** |

---

## 10. Security Model & Verified Defect Fixes

Every security claim in this repository is provably verified by automated attack tests:

| Security Claim / Protection | Implementation Mechanism | Verified By Test / Artifact |
| :--- | :--- | :--- |
| **Runtime Mode Immutability** | `EVALUATOR_MODE` and `DEMO_MODE` are determined strictly from process environment at boot. No runtime endpoint assigns these variables. Toggle endpoint returns HTTP 404 in production. | `test_regression_defect_1_production_evaluator_mode_toggle_rejected`, `test_evaluator_mode_toggle_and_gating` |
| **Production Boot Demarcation** | Startup aborts with `RuntimeError` if `ENV=production` while any demo flag is active. | `test_regression_defect_6_boot_refusal_when_production_and_demo_flag` |
| **Zero Token Disclosure Over HTTP** | `verification_token` and `reset_token` are NEVER included in JSON HTTP responses under any mode. Delivered strictly via outbox/SMTP. | `test_regression_defect_2_password_reset_security`, `test_regression_defect_3_signup_email_verification_security`, `test_regression_defect_8_e2e_json_response_leak_scan` |
| **Constant-Time Account Enumeration Defense** | `/auth/forgot-password` and `/auth/signup` return identical status codes, bodies, and simulated constant timing for existing vs non-existent accounts. | `test_regression_defect_2_password_reset_security`, `test_regression_defect_3_signup_email_verification_security` |
| **Cryptographic Token Lifecycle** | Tokens stored strictly as SHA-256 hashes; single-use (cleared on use); 30m expiry (reset) / 24h expiry (verification); session revocation on reset. | `test_regression_defect_2_password_reset_security`, `test_regression_defect_3_signup_email_verification_security` |
| **Demo Account Production Hygiene** | Seeding demo institutions occurs ONLY when `EVALUATOR_MODE=true`. Booting on a DB with demo users logs a loud alert and disables them (`is_active=False`). Active accounts with default passwords abort boot. | `test_regression_defect_4_production_demo_users_disabled_and_rejected` |
| **Mandatory Admin First-Login Password Change** | Admin created from `ADMIN_INITIAL_PASSWORD` receives a restricted token on first login (`type="password_change_required"`) permitting ONLY `/auth/change-password`. All other APIs return 403 until password is changed. | `test_regression_defect_5_admin_first_login_password_change_enforced` |
| **Statutory Password Policy** | Enforces minimum 12 characters, breach-list check against top common passwords, disallowance of email matches, and disallowance of reusing current password. | `test_regression_defect_5_admin_first_login_password_change_enforced` |
| **Brute-Force & Rate Limiting** | Sliding-window limits per IP and per identifier on login, password reset, and registration endpoints with audit logging. | `test_regression_defect_7_brute_force_rate_limiting` |
| **Repository Hygiene & Packaging Filter** | `.env`, `*.db*`, and `storage_data` contents are strictly excluded from git tracking (`scripts/check_clean_repo.py`) and from distribution archives (`scripts/package.py`, `Ai.zip`). | `scripts/check_clean_repo.py`, `scripts/package.py` |

> [!CAUTION]
> **CRITICAL SECURITY ADVISORY (KEY ROTATION REQUIRED):**
> If any previous build or archive of this repository containing a `backend/.env` file was ever shared, distributed, or deployed, you **MUST immediately rotate** all secrets:
> 1. Rotate `JWT_SECRET` using: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
> 2. Rotate `MFA_ENCRYPTION_KEY` using: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
> 3. Rotate `ADMIN_INITIAL_PASSWORD` and enforce immediate password reset on boot.
> Ship only `.env.example` with placeholders.

---

## 11. DPDP Act 2023 Alignment & Infrastructure Roadmap

- **Data Protection and Digital Privacy (DPDP) Act 2023 Compliance:**
  - **Role-Based Data Minimization:** Public status tracking lookup by Application ID shows stage, status, and masked institution names—**zero confidential documents, financial data, or applicant PII are exposed**.
  - **Outsider-Verifiable Public Audit (`/verify`):** Proves document and ledger authenticity using SHA-256 hashes and daily Merkle roots without revealing applicant identity, student names, or financial records.
  - **Pairwise Separation of Duties:** Strict enforcement of $Submitter \ne Verifier \ne Approver$ and $AI\_Requester \ne AI\_Approver$, with every document view, upload, and verification verdict committed to an append-only cryptographic ledger.
  - **Tamper Detection on Retrieval:** Real-time SHA-256 validation prevents unauthorized bitflips or document replacements on underlying storage.
- **Government Cloud Hosting Readiness:**
  - Architecture is containerized and ready for deployment on **MeitY-empanelled cloud service providers (CSPs)** or **National Informatics Centre (NIC)** government infrastructure.
  - S3-compatible document storage (MinIO adapter) is ready for direct migration to government object storage (e.g. MeghRaj cloud storage).

---

## 12. Known Limitations and Honest Engineering Disclosures

1. **In-Memory Rate Limiting:** The sliding-window rate limiter and brute-force lockout mechanisms are currently held in memory. In a multi-worker production cluster, these should be backed by a centralized distributed cache (e.g. Redis or Memcached).
2. **Single-Node Lockout:** Account lockout thresholds are tracked within the process runtime; enterprise multi-node deployments require distributed session management.
3. **SQLite Development Database:** In development and demonstration environments, the system utilizes SQLite for zero-setup execution. Native PostgreSQL Row-Level Security (RLS) is fully specified in `schema_rls_postgres.sql` and verified via `test_postgres_rls.py` when PostgreSQL is active.
4. **Outbound Email Test Hooks:** To prevent token leaks over HTTP while allowing automated regression testing, an in-memory test outbox is used. This hook is active **ONLY** when `PYTEST_CURRENT_TEST` or `TESTING=true` is set. Calling test outbox methods in a non-testing production environment unconditionally raises `RuntimeError`.
5. **Competent Authority Reservation:** Automated alerts, recommendations, and pipeline routing support the approval workflow but **never replace statutory scrutiny, verification, inspections, or decisions** reserved for authorized AICTE officials and committees. The Council ratifies decisions; the Executive Committee decides; the Member Secretary communicates and executes Council decisions.
6. **Simulated Connectors:** External adapters for DigiLocker, digital e-Sign, and legacy State Portals are implemented as **simulated connectors** with authentic REST schemas and cryptographic verification hashes. No Aadhaar data is processed, demanded, or stored. SMS alerts are marked as **simulated mocks**.
7. **Document OCR Labeling:** Land lease extraction operates as a **simulated extraction on synthetic text**. When scan quality is normal, field-level confidence scores are reported; in degraded or low-quality scan cases, confidence falls below 75%, automatic field extraction is withheld, and the system strictly requires manual officer entry and verification under APH Chapter II Clause 2.1(e).
8. **Synthetic Seed Data:** All 210 institutions, document numbers, and committee member profiles are deterministic synthetic records. Operational metrics reflect automated reminder and escalation cycles.

