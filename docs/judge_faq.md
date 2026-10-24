# AICTE Approval & Compliance Automation Platform
## Evaluator & Judge FAQ: Defending Architectural Decisions

This document addresses the most critical questions regarding architecture, security, regulatory compliance, and AI governance for the AICTE Approval & Compliance Automation Platform (PS SIH26262).

---

### Q1: Why not use a pure LLM for the entire workflow?
**Answer: Because regulatory approvals are governed by statutory law, not probabilistic prompts.**
1. **Legal Enforceability & Determinism:** The AICTE Approval Process Handbook (APH 2024–27), specifically Table 2.3, defines 21 strict institutional pipelines, mandatory document prerequisites, and statutory SLA clocks. A pure LLM is non-deterministic: given the same institution dossier twice, temperature variation or prompt drift could lead to two different approval pathways.
2. **Statutory Non-Delegation:** AI cannot lawfully sign an approval or issue an Extension of Approval (EoA). AICTE Act of 1987 and Council regulations reserve approval authority exclusively to the Regional Officer, Bureau Head, and Council Executive Committee.
3. **Auditability:** Courts and appellate tribunals (SAC/SHC) require demonstrable proof of which clause was applied. Our Rules Engine maps every condition directly to its exact chapter, clause, and handbook page number (e.g., Clause 1.8(g), Table 2.3).

---

### Q2: How do you guarantee zero LLM hallucinations?
**Answer: The LLM suggests; the deterministic Rules Engine decides; a named Human Approver commits.**
1. **Hard Rules Engine Boundary:** Eligibility, stage progression, SLA deadlines, and penalty calculations are executed strictly in deterministic Python code using mathematical formulas and codified Table 2.3 logic.
2. **Drafts-Only Isolation:** All generative AI outputs (deficiency memos, scrutiny summaries, hearing briefs) are written exclusively to the `llm_drafts` table marked with `status="DRAFT"` and `classification="SUGGEST_ONLY"`.
3. **Human-in-the-Loop Gate:** An AI draft cannot advance an application or modify case state. An authorized officer must review, edit, and sign their cryptographic identity to the draft.
4. **Separation of Duties (SoD):** The officer who triggered the AI draft is prohibited from being the final approver, preventing rubber-stamping.

---

### Q3: What stops a corrupt officer or bad actor inside AICTE from altering records?
**Answer: Multi-layered defence: Hash-Chained Audit Ledger, Pairwise Separation of Duties, and Row-Level Security.**
1. **Immutable Cryptographic Ledger:** Every action (document upload, verification, stage advancement, alert dispatch, login, escalation) is recorded in a SHA-256 hash-chained audit ledger (`AuditTrail`). Each entry contains `curr_entry_hash = SHA256(prev_entry_hash + actor_id + action + entity_id + timestamp + metadata)`. Any direct database row tampering breaks the chain immediately.
2. **Pairwise Separation of Duties:**
   - Submitter $\neq$ Verifier: An officer cannot verify an application or document they submitted.
   - Verifier $\neq$ Approver: The scrutiny officer who verified compliance cannot be the final approver.
   - Submitter $\neq$ Approver: The applicant institution or initial dealing officer cannot grant approval.
3. **Row-Level Security (RLS) & ScopedDAL:**
   - Regional officers are strictly confined to their assigned geographic jurisdiction (e.g., SWRO officers cannot access or query NRO applications).
   - Institution users can only view their own institution's docket.
   - Cross-jurisdiction requests are rejected with 403 Forbidden or 404 Not Found.
4. **File Tamper Detection on Read:** Every document's SHA-256 hash is computed on upload. When any stakeholder downloads the file, the server recomputes the hash from the storage backend (disk/MinIO). If a single byte was altered, download is blocked with HTTP 409 Conflict and an emergency security anomaly is logged.

---

### Q4: What is Real vs What is Simulated?

| Subsystem | Real Implementation | Simulated / Evaluator Sandbox |
|---|---|---|
| **Authentication & RBAC** | Real PBKDF2-SHA256 password hashing, real RS256/HS256 JWT tokens, refresh token rotation, brute-force lockout. | 1-Click Persona switching buttons (only enabled when `EVALUATOR_MODE=True`). |
| **Email Delivery** | Real SMTP client sending actual RFC-5322 emails over port 1025 to Mailpit inbox. | Mailpit local dev mail server (no spam sent to real college principals). |
| **WhatsApp / SMS** | Real HTTP adapter formatted for Twilio WhatsApp Sandbox REST API. | Twilio Sandbox fallback when live API credentials are not provided in environment. |
| **File Storage** | Real binary storage (local disk / MinIO S3-compatible), real `%PDF-1.4` magic byte validation, real SHA-256 hashing. | Seeded initial demo documents have synthesized valid PDF headers. |
| **Audit Ledger** | Real SHA-256 hash chaining with automated verification endpoint (`/api/v1/audit/verify-chain`). | None (100% Real). |
| **SLA Clocks & Timers** | Real working-days calendar calculation excluding national gazetted holidays and weekends; real APScheduler. | Virtual Time-Travel bar (+7, +30 days) to simulate SLA progression without waiting weeks. |
| **Rules Engine** | 100% Real deterministic Python rules engine with Table 2.3 routes, Clause 2.1(e) lease logic, and penalty formulas. | None (100% Real). |
| **EVC Inspection Hub** | Real pairwise conflict-of-interest validation, expert empanelment, and geotagged report storage. | Geotagged coordinates represent verified sample engineering campuses across India. |

---

### Q5: How does the system handle institutional disputes and appeals?
**Answer: Statutory compliance with Chapter I, Clause 1.10 & 1.11 of APH 2024–27.**
- **Standing Hearing Committee (SHC):** If deficiencies are not cured within the statutory window, the application is referred to SHC (Clause 1.10).
- **Standing Appellate Committee (SAC):** If an institution receives a Letter of Rejection (LoR), they have a statutory right to appeal within 7 calendar days to the SAC headed by a retired High Court Justice (Clause 1.11(a)).
- **Clock Freezing:** Under Clause 1.8(g), when an application is reverted for deficiency cure, the statutory SLA clock is frozen (`is_paused=True`). The clock resumes only after the institution uploads verified rectified documents.

---

### Q6: How does the Workload Forecasting Engine differ from simple deadlines?
**Answer: It uses queuing theory and per-case parameters rather than static dates.**
- Static deadlines tell an officer when a case is due; our **Workload Forecasting Engine** calculates **projected completion probability bands (P10, P50, P90)**.
- It considers:
  1. Current stage and remaining stages in the pipeline.
  2. Regional queue depth and officer case load.
  3. Indian working calendar (excluding Saturday/Sunday and Central Gazetted Holidays).
  4. Historical stage velocity and deficiency pause probabilities.
- Different cases with different stages, pipelines, and submission dates receive distinct, mathematically rigorous projected completion dates.

---

### Q7: How is public transparency maintained without violating data privacy (DPDP Act 2023)?
**Answer: The Public Tracking Portal exposes status milestones while strictly redacting PII.**
- Available at `/api/v1/public/track/{tracking_id}` without authentication.
- Rate-limited to 30 requests per minute per IP to prevent scraping.
- Returns only public interest fields: Application Number, Academic Cycle, Application Type, Current Stage, Status, Statutory Due Date, Next Required Action, and Progress Timeline.
- Personal data (officer contact, institution email, phone numbers, internal committee deliberations, unreleased deficiency memos) are strictly filtered and omitted.
