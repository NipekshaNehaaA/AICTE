# AICTE Approval & Compliance Platform: Real-Clock 7-Step Demonstration Script

This script provides an evaluative, production-grade walkthrough of the AICTE statutory approval workflow executed under **real-clock conditions** with **Evaluator Mode OFF** (`EVALUATOR_MODE=false`, `DEMO_MODE=false`).

---

## 1. Persona Matrix & Statutory Credentials

| Step | Stakeholder Role | Representative User | Email Address | Password / MFA | Scope & Statutory Mandate |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1, 3** | **INSTITUTION_USER** | Dr. Principal | `principal.110000001@fictional-aicte.edu.in` | `DemoPassword@123` | Apex Institute of Technology (PID: 1-10000001) |
| **2, 4** | **REGIONAL_OFFICER** | Dr. K. S. Venkatesh | `ro.swro@aicte-india.org` | `DemoPassword@123` + TOTP | South Western Regional Office (SWRO) |
| **5** | **COMMITTEE_MEMBER** | Prof. R. Soundarajan | `exp-prof-01` (IIT Madras) | Pre-Empanelled Cross-State | Empanelled Expert Visit Committee (EVC) |
| **6** | **REGIONAL_DIRECTOR** | Dr. Regional Director | `rd.swro@aicte-india.org` | `DemoPassword@123` + TOTP | SWRO Regional Bureau Oversight |
| **7** | **SUPER_ADMIN** | Dr. Arvind Ramanathan | `member.secretary@aicte-india.org` | `DemoPassword@123` + TOTP | Member Secretary, AICTE Council (HQ) |
| **Audit** | **AUDITOR** | Smt. Priya Balan | `auditor.compliance@aicte-india.org` | `DemoPassword@123` + TOTP | Pan-India Read-Only Audit & Verification |

---

## 2. Step-by-Step Statutory Storyline

### Step 1: Technical Institution Submits Application & Initial Lease Deed
- **Actor:** `INSTITUTION_USER` (`Dr. Principal`, Apex Institute of Technology)
- **APH Mandate:** Chapter I, Clause 1.3 & Table 2.3 (Establishment of New Technical Campus).
- **Actions:**
  1. Log in via Portal Sign In using `principal.110000001@fictional-aicte.edu.in` and `DemoPassword@123`.
  2. The portal routes directly to the **Institution Tracker** with dynamic institution header:
     - `Apex Institute of Technology`
     - `PID: 1-10000001`
  3. Submit an application for establishment of new technical campus:
     - **API:** `POST /api/v1/applications/submit`
     - **Payload:**
       ```json
       {
         "institution_id": "inst-10000001",
         "application_type": "NEW_INSTITUTION",
         "academic_year": "2026-2027",
         "course_name": "Artificial Intelligence & Data Science",
         "intake_proposed": 60
       }
       ```
     - **Response:** Application assigned `current_stage="SCRUTINY"`, `status="IN_PROGRESS"`, and initial statutory SLA deadline.
  4. Upload initial Registered Land Lease Deed (Doc v1):
     - **API:** `POST /api/v1/compliance/documents/upload-file` (Multipart)
     - **Document Validity:** Only 3 years (e.g. 2024-01-01 to 2027-01-01).
     - **Result:** `version=1`, `status="PENDING_VERIFICATION"`, `is_latest_version=True`.

---

### Step 2: Regional Scrutiny Officer Identifies Deficiency & Reverts
- **Actor:** `REGIONAL_OFFICER` (`Dr. K. S. Venkatesh`, SWRO)
- **APH Mandate:** Chapter II Clause 2.1(e) & Chapter VI Clause 6.17 (Minimum 30-Year Registered Lease Requirement).
- **Actions:**
  1. Officer logs in to the SWRO regional worklist at `/queue`.
  2. Reviews Table 2.3 intake compliance and examines the 3-year land lease deed.
  3. Under Clause 2.1(e), live lease period cannot be shorter than the course duration and must be a minimum 30-year registered lease.
  4. Flags deficiency and returns application:
     - **API:** `POST /api/v1/workflow/{application_id}/revert`
     - **Payload:**
       ```json
       {
         "reason_category": "Land Lease Near Expiration",
         "deficiency_remarks": "Live lease period is only 3 years. AICTE Chapter II Clause 2.1(e) & Chapter VI Clause 6.17 mandates minimum 30 years registered lease.",
         "aph_clause_ref": "Chapter II Clause 2.1(e) & Chapter VI Clause 6.17 (Page 28)",
         "cure_days": 15
       }
       ```
     - **Enforced Outcome:**
       - Application transitions to `status="DEFICIENT"`, `current_stage="DEFICIENCY_REVERTED"`.
       - **Statutory SLA Clock is Paused (`last_paused_at` set).**
       - Formal deficiency notification dispatched to institution with a 15-day cure deadline.

---

### Step 3: Institution Uploads 30-Year Lease Extension & Cures Deficiency
- **Actor:** `INSTITUTION_USER` (`Dr. Principal`)
- **APH Mandate:** Chapter I, Clause 1.8(g) (Opportunity for Deficiency Rectification).
- **Actions:**
  1. Institution views deficiency notice in the Institution Tracker.
  2. Obtains and uploads registered 30-year lease extension deed (Doc v2):
     - **API:** `POST /api/v1/compliance/documents/upload-file`
     - **Payload:** `replaces_document_id={doc_v1_id}`, `expiry_date="2056-01-01"`.
     - **Truthful UI Versioning Result:**
       - **Doc v1 is marked `status="SUPERSEDED"`, `is_latest_version=False` (retained in audit history and downloadable).**
       - **Doc v2 is marked `version=2`, `is_latest_version=True`, `status="PENDING_VERIFICATION"`.**
  3. Submits formal cure response:
     - **API:** `POST /api/v1/workflow/{application_id}/cure-submit`
     - **Payload:**
       ```json
       {
         "institution_response": "Registered 30-year extension lease deed uploaded with Sub-Registrar endorsement.",
         "rectified_document_urls": ["/api/v1/compliance/documents/.../download"]
       }
       ```
     - **Enforced Outcome:**
       - Application transitions to `current_stage="RE_SCRUTINY"`, `status="IN_PROGRESS"`.
       - **Statutory SLA Clock Unpauses:** `last_paused_at=None`, deadline pushed forward by the exact paused duration (~48 hours).

---

### Step 4: Regional Officer Re-Scrutiny Verification & EVC Panel Allocation
- **Actor:** `REGIONAL_OFFICER` (`Dr. K. S. Venkatesh`)
- **APH Mandate:** Chapter I Clause 1.8(g) (Strict Re-Scrutiny Scope) & Annexure-16 Clause 16.5 (Conflict-Free EVC Panel).
- **Actions:**
  1. Officer executes Re-Scrutiny verification strictly against the preliminary deficiency:
     - **API:** `POST /api/v1/workflow/{application_id}/re-scrutiny-verify`
     - **Payload:**
       ```json
       {
         "items_to_verify": ["Land Lease Near Expiration"],
         "is_satisfactory": true,
         "committee_remarks": "30-year registered lease deed verified compliant with Chapter II Clause 2.1(e)."
       }
       ```
     - **Guarded Rule:** Attempting to verify or add out-of-scope items triggers HTTP 422 under Clause 1.8(g).
     - **Outcome:** Stage advances to `"EVC"`. `app.verifier_id = "ro-officer-swro"`.
  2. Smart Panel Suggestion with Cross-State Conflict Prevention:
     - **API:** `POST /api/v1/evc/suggest-panel`
     - **Rules Enforced:**
       - **Rule 1 (Home State):** Experts from Karnataka are strictly excluded.
       - **Rule 2 (Cooling Window):** Experts who reviewed this institution within 24 months are excluded.
       - **Rule 3 (Double Booking):** Experts already scheduled on the inspection date are excluded.
     - **Result:** Selects cross-state panel (e.g., Prof. from Tamil Nadu, Architect from Delhi, Industry Expert from Maharashtra).
  3. Confirm EVC Panel & Export Calendar:
     - **API:** `POST /api/v1/evc/{application_id}/confirm`
     - **API:** `GET /api/v1/evc/schedule/{panel_id}/ics` (RFC 5545 iCalendar download).
     - **Outcome:** Stage advances to `"EVC_SCHEDULED"`.

---

### Step 5: Empanelled Committee Member Conflict Declaration & Geotagged Report
- **Actor:** `COMMITTEE_MEMBER` (`Prof. R. Soundarajan`, IIT Madras)
- **APH Mandate:** Chapter I Clause 1.9 & Annexure-16 Clause 16.5 (30-min Video Recording & Geotag Verification).
- **Actions:**
  1. Empanelled expert officially submits conflict of interest declaration:
     - **API:** `POST /api/v1/evc/{panel_id}/declare-conflict`
     - **Payload:**
       ```json
       {
         "has_conflict": false,
         "statement": "I declare zero financial, familial, or consulting affiliation with this institution under Annexure-16 Clause 16.5."
       }
       ```
  2. Expert conducts on-site / virtual verification and submits final inspection report:
     - **API:** `POST /api/v1/evc/reports/{panel_id}/submit`
     - **Payload:**
       ```json
       {
         "recommendation": "RECOMMENDED",
         "inspection_summary": "Comprehensive 30-minute physical inspection completed. Infrastructure, laboratories, barrier-free access, and fire safety fully compliant.",
         "deficiencies": [],
         "geo_lat": 12.9716,
         "geo_lng": 77.5946
       }
       ```
     - **Outcome:** Stage advances to `"EXECUTIVE_COMMITTEE"`.

---

### Step 6: Regional Director Reviews Docket & Recommends Ratification
- **Actor:** `REGIONAL_DIRECTOR` (`Dr. Regional Director`, SWRO)
- **APH Mandate:** Chapter I Clause 1.10 (Regional Bureau Oversight & EC Submission).
- **Actions:**
  1. Regional Director reviews the complete electronic case docket:
     - Application intake & Table 2.3 routing
     - Re-scrutiny compliance certificate
     - EVC Geotagged inspection report & video verification hash
  2. Advances case docket to Council Ratification:
     - **API:** `POST /api/v1/workflow/{application_id}/advance`
     - **Pairwise SoD Guard:** Regional Director differs from Submitter.
     - **Outcome:** Stage transitions to `"COUNCIL_RATIFIED"`.

---

### Step 7: Member Secretary Final Approval & Cryptographic Audit Proof
- **Actor:** `SUPER_ADMIN` (`Dr. Arvind Ramanathan`, Member Secretary, AICTE Council HQ)
- **APH Mandate:** Chapter I Clause 1.10 (Council Approval & Non-Repudiation).
- **Actions:**
  1. **Strict Pairwise SoD Enforcement:**
     $$\text{Submitter (Dr. Principal)} \ne \text{Verifier (Dr. Venkatesh)} \ne \text{Approver (Dr. Ramanathan)}$$
     Any attempt by the Submitter or Verifier to approve the application is rejected with HTTP 403.
  2. Member Secretary signs and issues the official Approval Order:
     - **API:** `POST /api/v1/workflow/{application_id}/advance`
     - **Outcome:** Application status updated to `"APPROVED"`.
  3. **Cryptographic SHA-256 Audit Chain Verification:**
     - **API:** `POST /api/v1/audit/verify-chain`
     - **Verification Check:**
       ```json
       {
         "status": "VERIFIED_INTEGRITY",
         "is_valid": true,
         "total_entries_verified": 18,
         "violations": []
       }
       ```
  4. **Daily Merkle Root Sealing & Public Verification:**
     - **API:** `POST /api/v1/audit/merkle-roots/seal` $\to$ yields `merkle_root_hash`.
     - **API:** `GET /api/v1/audit/public-verify?hash={chain_head_hash}` $\to$ confirms authentic audit entry with **ZERO confidential applicant PII returned**.

---

## 3. Automated Test Verification

Execute the end-to-end real-clock story automated tests:

### Backend Pytest Suite:
```powershell
python -m pytest tests/test_real_clock_7step_story.py -v
```
*Expected: 1 passed in ~0.7s.*

### Frontend Playwright E2E Suite:
```powershell
npx playwright test e2e/real-clock-7step-story.spec.ts
```
*Expected: 1 passed in ~2.0s.*
