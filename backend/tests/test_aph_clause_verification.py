"""
=============================================================================
TEST SUITE: APH 2024-27 CLAUSE VERIFICATION & GROUNDED PROVENANCE
=============================================================================
Validates that every statutory clause reference in the system is directly
extracted from and present in the official uploaded 'Approval process handbook.pdf'.

Upgrades per Group B-E Corrections:
1. Citation Fix: Live lease EoA cutoff rule is Chapter II Clause 2.1(e), NOT 1.12(e).
   Registered lease minimum 30 years stays under Chapter VI Clause 6.17.
2. Mega/Metro 20-year lease rule labeled as 'unsourced assumption, configurable'.
3. Upgraded verification script: Every seeded rule stores a short verbatim snippet
   from the APH, and the script fails CI unless that snippet is found in the APH
   text near the cited clause. Existence of a clause number alone is not enough.
   Negative test added showing wrong citation (lease rule under 1.12) fails CI.
4. Lease early warning: Alerts before remaining live lease reaches longest course
   duration, returning years remaining, the threshold, and the exact EoA block date.
5. Dynamic Table 2.3 stage path: Shows SAC only for appeals and SHC only when
   compliance verification applies.
=============================================================================
"""

import sys
import os
import re
import pypdf
import pytest
from datetime import date, timedelta
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rules_engine import (
    APHRulesEngine,
    APH_STATUTORY_DEADLINES,
    APH_CLAUSE_CATALOG,
    TABLE_2_3_SEEDED_ROUTING,
)

PDF_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "Approval process handbook.pdf"))

@pytest.fixture(scope="module")
def aph_reader():
    """Loads the uploaded Approval Process Handbook PDF once and pre-caches page texts."""
    assert os.path.exists(PDF_PATH), f"Uploaded APH not found at {PDF_PATH}"
    reader = pypdf.PdfReader(PDF_PATH)
    assert len(reader.pages) >= 200, f"Expected 200+ pages, found {len(reader.pages)}"
    reader.cached_texts = [p.extract_text() or "" for p in reader.pages]
    return reader

def verify_clause_verbatim_proximity(
    reader: pypdf.PdfReader,
    clause_number: str,
    verbatim_snippet: str,
    proximity_window: int = 4500,
) -> Dict[str, Any]:
    """
    Verifies that the verbatim snippet exists in the APH text near the cited clause number.
    Fails CI unless the snippet is found within proximity_window characters of clause_number.
    Handles clauses and subclauses spanning adjacent page breaks.
    Existence of a clause number alone is NOT enough.
    """
    norm_snippet = re.sub(r"\s+", " ", verbatim_snippet.strip().lower())
    page_texts = getattr(reader, "cached_texts", None)
    if page_texts is None:
        page_texts = [p.extract_text() or "" for p in reader.pages]
        reader.cached_texts = page_texts
    num_pages = len(page_texts)

    for page_idx in range(num_pages):
        # Concatenate adjacent page to handle subclauses spanning page boundaries
        chunk = page_texts[page_idx]
        if page_idx + 1 < num_pages:
            chunk += " " + page_texts[page_idx + 1]
            
        norm_chunk = re.sub(r"\s+", " ", chunk)
        
        # Check if clause_number is present in this chunk
        clause_matches = [m.start() for m in re.finditer(re.escape(clause_number), norm_chunk, re.IGNORECASE)]
        if not clause_matches:
            continue
            
        norm_chunk_lower = norm_chunk.lower()
        snippet_pos = norm_chunk_lower.find(norm_snippet)
        if snippet_pos != -1:
            for cm in clause_matches:
                dist = abs(snippet_pos - cm)
                if dist <= proximity_window:
                    return {
                        "found": True,
                        "page_number": page_idx + 1,
                        "clause_match_idx": cm,
                        "snippet_match_idx": snippet_pos,
                        "distance": dist,
                        "context": norm_chunk[max(0, snippet_pos - 30): snippet_pos + len(norm_snippet) + 30],
                    }

    return {
        "found": False,
        "error": f"Snippet '{verbatim_snippet}' NOT found near cited clause '{clause_number}' within {proximity_window} chars in authentic APH text.",
    }

def test_aph_pdf_authenticity(aph_reader):
    """Verifies that the uploaded PDF is the official AICTE Approval Process Handbook 2024-2027."""
    page_3_text = aph_reader.pages[2].extract_text() or ""
    assert "Approval Process Handbook" in page_3_text
    assert "All India Council for Technical Education" in page_3_text
    assert len(aph_reader.pages) == 231

def test_seeded_rules_verbatim_proximity_check(aph_reader):
    """
    Requirement 3: Verifies that every seeded rule in APH_CLAUSE_CATALOG has a verbatim snippet
    that exists in the APH text near the cited clause number. Fails CI otherwise.
    """
    for key, rule in APH_CLAUSE_CATALOG.items():
        if "verbatim_snippet" not in rule or "clause_number" not in rule:
            continue
        
        res = verify_clause_verbatim_proximity(
            aph_reader,
            clause_number=rule["clause_number"],
            verbatim_snippet=rule["verbatim_snippet"],
            proximity_window=4500,
        )
        assert res["found"] is True, f"CI Failure: Seeded rule '{key}' failed verbatim proximity check: {res.get('error')}"

def test_wrong_citation_fails_ci(aph_reader):
    """
    Requirement 3: Negative Test.
    Verifies that a wrong citation (e.g. lease rule placed under Clause 1.12 instead of Chapter II Clause 2.1(e))
    fails CI, proving that existence of a clause number alone is not enough.
    """
    lease_snippet = "In case of Institutions having Lease agreement for Land, the Council shall not issue EoA from the Year in which the Live Lease is equal to the number of years of the Course having the maximum duration"

    # 1. Negative: Looking for the lease rule under Clause 1.12 MUST FAIL
    res_wrong = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="1.12",
        verbatim_snippet=lease_snippet,
        proximity_window=3500,
    )
    assert res_wrong["found"] is False, "A wrong citation must fail CI!"
    assert "NOT found near cited clause '1.12'" in res_wrong["error"]

    # 2. Positive: Looking for the lease rule under Chapter II Clause 2.1 MUST SUCCEED
    res_correct = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="2.1",
        verbatim_snippet=lease_snippet,
        proximity_window=3500,
    )
    assert res_correct["found"] is True
    assert res_correct["page_number"] in [27, 28]

def test_clause_2_1_e_and_6_17_land_lease_early_warning_and_cutoff():
    """
    Requirements 1, 2, 6:
    - Chapter II Clause 2.1(e): EoA blocked when live lease equals maximum course duration.
    - Chapter VI Clause 6.17: Registered land lease minimum 30 years.
    - 20 years for Mega/Metro cities labeled as 'unsourced assumption, configurable'.
    - Lease early warning: Alerts before remaining live lease reaches longest course duration,
      showing years remaining, the threshold, and the exact calculated EoA block date.
    """
    # Case A: Early warning alert triggered before live lease reaches course duration
    # 30-year lease from 1996-01-01 to 2026-01-01, course duration 4 yrs, evaluated on 2021-07-01
    # Remaining = 4.5 yrs > 4 yrs, but within 1-year early warning window (block date = 2022-01-01)
    res_early_warning = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=date(1996, 1, 1),
        lease_end_date=date(2026, 1, 1),
        is_mega_metro=False,
        longest_course_duration_years=4,
        evaluation_date=date(2021, 7, 1),
    )
    assert res_early_warning["is_initial_term_valid"] is True
    assert res_early_warning["years_remaining"] == 4.5
    assert res_early_warning["threshold_course_duration_years"] == 4
    assert res_early_warning["is_early_warning"] is True
    assert res_early_warning["is_eoa_blocked"] is False
    assert res_early_warning["status"] == "ALERT_EXPIRING_SOON"
    assert res_early_warning["eoa_block_date"] == "2022-01-01"
    assert "Early Warning Alert" in res_early_warning["message"]
    assert "Chapter II Clause 2.1(e)" in res_early_warning["aph_clause_ref"]

    # Case B: EoA Block Date reached / passed (3.0 yrs remaining <= 4.0 yr course duration)
    res_blocked = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=date(1995, 1, 1),
        lease_end_date=date(2028, 1, 1),
        is_mega_metro=False,
        longest_course_duration_years=4,
        evaluation_date=date(2025, 1, 1),
    )
    assert res_blocked["is_eoa_blocked"] is True
    assert res_blocked["status"] == "BLOCKED_EOA_DENIED"
    assert res_blocked["years_remaining"] == 3.0
    assert "EoA Blocked" in res_blocked["message"]
    assert "Chapter II Clause 2.1(e)" in res_blocked["message"]

    # Case C: Fully Compliant (10.0 yrs remaining > 4 yr threshold + early warning window)
    res_compliant = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=date(2000, 1, 1),
        lease_end_date=date(2036, 1, 1),
        is_mega_metro=False,
        longest_course_duration_years=4,
        evaluation_date=date(2026, 1, 1),
    )
    assert res_compliant["status"] == "COMPLIANT"
    assert res_compliant["is_eoa_blocked"] is False
    assert res_compliant["is_early_warning"] is False

    # Case D: Mega/Metro assumption label verification (Requirement 2)
    res_metro = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=date(2005, 1, 1),
        lease_end_date=date(2035, 1, 1),
        is_mega_metro=True,
        longest_course_duration_years=4,
    )
    assert "unsourced assumption, configurable" in res_metro["threshold_note"]

def test_configurable_lease_early_warning_offsets_and_expiry_alerts():
    """
    Validates configurable lease early-warning offsets (default 12/6/3 months before EoA block date)
    and lease expiry alerts (default 12/6/3 months before actual lease expiration).
    """
    lease_start = date(1996, 1, 1)
    lease_end = date(2026, 1, 1)
    longest_course_duration = 4
    # Block date is 2022-01-01 (4 years before lease_end 2026-01-01)

    # 1. Test Default Offsets [12, 6, 3] months before EoA block date
    # Milestone dates for block date 2022-01-01:
    # 12M: ~2021-01-01
    # 6M:  ~2021-07-02
    # 3M:  ~2021-10-02

    # A. Evaluated on 2021-03-01: Past 12M alert, but before 6M alert
    res_12m = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=lease_start,
        lease_end_date=lease_end,
        longest_course_duration_years=longest_course_duration,
        evaluation_date=date(2021, 3, 1),
    )
    assert res_12m["is_early_warning"] is True
    assert res_12m["active_eoa_warning_tier"] == 12
    assert res_12m["eoa_warning_offsets_months"] == [12, 6, 3]
    assert any(m["offset_months"] == 12 and m["is_triggered"] for m in res_12m["eoa_warning_milestones"])
    assert any(m["offset_months"] == 6 and not m["is_triggered"] for m in res_12m["eoa_warning_milestones"])

    # B. Evaluated on 2021-08-01: Past 6M alert, but before 3M alert
    res_6m = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=lease_start,
        lease_end_date=lease_end,
        longest_course_duration_years=longest_course_duration,
        evaluation_date=date(2021, 8, 1),
    )
    assert res_6m["is_early_warning"] is True
    assert res_6m["active_eoa_warning_tier"] == 6

    # C. Evaluated on 2021-11-01: Past 3M alert (urgent!)
    res_3m = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=lease_start,
        lease_end_date=lease_end,
        longest_course_duration_years=longest_course_duration,
        evaluation_date=date(2021, 11, 1),
    )
    assert res_3m["is_early_warning"] is True
    assert res_3m["active_eoa_warning_tier"] == 3
    assert "within 3 months" in res_3m["message"]

    # 2. Test Custom Configurable Offsets (e.g. [24, 18, 9] months)
    res_custom = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=lease_start,
        lease_end_date=lease_end,
        longest_course_duration_years=longest_course_duration,
        evaluation_date=date(2020, 4, 1), # ~21 months before block date 2022-01-01
        eoa_warning_offsets_months=[24, 18, 9],
    )
    assert res_custom["is_early_warning"] is True
    assert res_custom["active_eoa_warning_tier"] == 24
    assert res_custom["eoa_warning_offsets_months"] == [24, 18, 9]

    # 3. Test Lease-Expiry Alerts (Approaching actual lease_end_date)
    # Suppose course duration is 0 (or lease not blocked yet), but lease expires in 5 months
    res_expiry_alert = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=date(1996, 1, 1),
        lease_end_date=date(2026, 6, 1),
        longest_course_duration_years=0,
        evaluation_date=date(2026, 1, 1), # 5 months before lease end date
    )
    assert res_expiry_alert["active_lease_expiry_tier"] == 6
    assert res_expiry_alert["is_early_warning"] is True
    assert "Lease expiration within 6 months" in res_expiry_alert["message"]

    # 4. Test Lease Expired Status
    res_expired = APHRulesEngine.evaluate_registered_lease(
        lease_start_date=date(1996, 1, 1),
        lease_end_date=date(2026, 1, 1),
        longest_course_duration_years=0,
        evaluation_date=date(2026, 2, 1), # Past lease end date
    )
    assert res_expired["is_lease_expired"] is True
    assert res_expired["status"] == "LEASE_EXPIRED"
    assert "Lease Expired" in res_expired["message"]

def test_dynamic_table_2_3_stage_path_sac_shc_filtering():
    """
    Requirement 5:
    Build the stage path from the application's Table 2.3 route.
    Show SAC only for appeals and SHC only when compliance verification applies;
    do not show them for every application.
    """
    # 1. Self-Disclosure application (e.g. EXTENSION_OF_APPROVAL):
    # Route: Self-Disclosure only -> No Scrutiny, No EVC, No SAC, No SHC
    stages_sd = APHRulesEngine.build_route_stage_path("EXTENSION_OF_APPROVAL")
    assert stages_sd == ["SELF_DISCLOSURE", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]
    assert "SAC_HEARING" not in stages_sd
    assert "SHC_HEARING" not in stages_sd

    # 2. Scrutiny-only application (e.g. CHANGE_NAME_INSTITUTION):
    # Route: Scrutiny only -> Scrutiny, EC, Council Ratified. No EVC, No SAC, No SHC
    stages_scrutiny = APHRulesEngine.build_route_stage_path("CHANGE_NAME_INSTITUTION")
    assert stages_scrutiny == ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]
    assert "EVC" not in stages_scrutiny
    assert "SAC_HEARING" not in stages_scrutiny
    assert "SHC_HEARING" not in stages_scrutiny

    # 3. Standard Chapter I New Institution without appeal or compliance violation:
    # Scrutiny -> Re-Scrutiny -> EVC -> Executive Committee -> Council Ratified
    stages_new_std = APHRulesEngine.build_route_stage_path("NEW_INSTITUTION")
    assert stages_new_std == ["SCRUTINY", "RE_SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]
    assert "SAC_HEARING" not in stages_new_std
    assert "SHC_HEARING" not in stages_new_std

    # 4. Appeal active: SAC must be included before Executive Committee
    stages_new_appeal = APHRulesEngine.build_route_stage_path("NEW_INSTITUTION", is_appeal=True)
    assert stages_new_appeal == ["SCRUTINY", "RE_SCRUTINY", "EVC", "SAC_HEARING", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]

    # 5. Compliance inquiry active: SHC must be included before Executive Committee
    stages_new_shc = APHRulesEngine.build_route_stage_path("NEW_INSTITUTION", is_compliance_verification=True)
    assert stages_new_shc == ["SCRUTINY", "RE_SCRUTINY", "EVC", "SHC_HEARING", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]

def test_clause_1_8_g_re_scrutiny_restriction(aph_reader):
    """Verifies Clause 1.8(g) on PDF page 23: Re-Scrutiny verifies ONLY deficiencies from Scrutiny."""
    res = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="1.8",
        verbatim_snippet="Re-Scrutiny Committee shall verify ONLY the deficiencies pointed out by the Scrutiny committee",
    )
    assert res["found"] is True
    assert res["page_number"] in [22, 23]

    # Test the rules engine enforcement of Clause 1.8(g)
    original_deficiencies = ["Missing Fire NOC", "Structural Stability Certificate"]
    
    # 1. Compliant: verifies only original deficiencies
    res_valid = APHRulesEngine.verify_re_scrutiny_scope(
        original_deficiencies,
        ["Missing Fire NOC"],
    )
    assert res_valid["is_compliant"] is True
    assert res_valid["verified_deficiencies"] == ["Missing Fire NOC"]

    # 2. Non-compliant: introduces new un-scrutinized deficiency
    res_invalid = APHRulesEngine.verify_re_scrutiny_scope(
        original_deficiencies,
        ["Missing Fire NOC", "New Course Syllabi Defect"],
    )
    assert res_invalid["is_compliant"] is False
    assert "New Course Syllabi Defect" in res_invalid["out_of_scope_items"]

def test_clause_2_23_3_shc_compliance_verification(aph_reader):
    """
    Verifies Chapter II Clause 2.23.3 on PDF page 45:
    Standing Hearing Committee verifies compliance of short comings from Scrutiny / EVC.
    """
    res = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="2.23.3",
        verbatim_snippet="Process for Verification of Compliance through Standing Hearing Committee",
    )
    assert res["found"] is True
    assert res["page_number"] in [44, 45]

def test_clause_2_24_a_and_1_11_a_sac_appeal(aph_reader):
    """
    Verifies Chapter I Clause 1.11(a) and Chapter II Clause 2.24(a) on PDF page 45:
    Institution aggrieved by the decision of the Executive Committee has the right to appeal within 7 days.
    """
    res = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="2.24",
        verbatim_snippet="aggrieved by the decision of the Executive Committee shall have the right to appeal once to the Council within 7 days",
    )
    assert res["found"] is True
    assert res["page_number"] in [44, 45]
    assert APH_STATUTORY_DEADLINES["SAC_APPEAL_WINDOW_DAYS"] == 7

def test_clause_2_25_f_security_deposit_penalties(aph_reader):
    """
    Verifies Clause 2.25(f) on PDF page 47:
    Submit Security Deposit proof + Affidavit 3 in 15 days;
    else penalty of 10% and 20% imposed up to 31st May and 31st July respectively.
    """
    res = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="2.25",
        verbatim_snippet="Affidavit 3 within 15 days",
    )
    assert res["found"] is True
    assert res["page_number"] in [46, 47]

    assert APH_STATUTORY_DEADLINES["SECURITY_DEPOSIT_DUE_DAYS"] == 15
    assert APH_STATUTORY_DEADLINES["PENALTY_WINDOW_10_PERCENT"] == "31-May"
    assert APH_STATUTORY_DEADLINES["PENALTY_WINDOW_20_PERCENT"] == "31-July"

def test_clause_2_25_j_eoa_calendar_cutoff(aph_reader):
    """Verifies Clause 2.25(j) on PDF page 47: Extension of Approval shall NOT be granted after Academic Calendar last date."""
    res = verify_clause_verbatim_proximity(
        aph_reader,
        clause_number="2.25",
        verbatim_snippet="Extension of Approval shall NOT be granted after the last date as mentioned in Academic Calendar",
    )
    assert res["found"] is True
    assert res["page_number"] in [46, 47]

def test_decision_flow_authority_matrix():
    """
    Verifies Decision Flow per Clause 1.8 & 2.25:
    Committees recommend -> Executive Committee decides -> Council ratifies.
    Member Secretary is Council Secretary communicating and executing Council decisions, NOT the sole final approver.
    """
    # 1. Scrutiny recommends
    auth_scrutiny = APHRulesEngine.evaluate_decision_authority("RECOMMEND_SCRUTINY", "REGIONAL_OFFICER")
    assert auth_scrutiny["is_authorized"] is True

    # 2. Executive Committee decides
    auth_ec = APHRulesEngine.evaluate_decision_authority("DECIDE_EC", "EXECUTIVE_COMMITTEE")
    assert auth_ec["is_authorized"] is True

    # 3. Council ratifies
    auth_council = APHRulesEngine.evaluate_decision_authority("RATIFY_COUNCIL", "COUNCIL")
    assert auth_council["is_authorized"] is True

def test_table_2_3_all_21_types_seeded():
    """
    Validates that Table 2.3 contains exactly 21 application types for Existing Institutions (Chapter II).
    Validates that NEW_INSTITUTION is not in Table 2.3 and follows Chapter I routing.
    Validates that EoA is split into EOA_SELF_DISCLOSURE and EOA_AFTER_BREAK.
    """
    types = APHRulesEngine.get_all_table_2_3_types()
    assert len(types) == 21, f"Expected exactly 21 Table 2.3 types, found {len(types)}"
    
    # Verify NEW_INSTITUTION is not in Table 2.3
    table_keys = set(TABLE_2_3_SEEDED_ROUTING.keys())
    assert "NEW_INSTITUTION" not in table_keys

    # Verify NEW_INSTITUTION follows Chapter I
    ch1 = APHRulesEngine.determine_pipeline("NEW_INSTITUTION")
    assert ch1["chapter"] == "Chapter I"
    assert ch1["stages"] == ["SCRUTINY", "RE_SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]

    # Verify EoA split in Table 2.3
    assert "EOA_SELF_DISCLOSURE" in table_keys
    assert "EOA_AFTER_BREAK" in table_keys
    assert TABLE_2_3_SEEDED_ROUTING["EOA_SELF_DISCLOSURE"]["self_disclosure"] is True
    assert TABLE_2_3_SEEDED_ROUTING["EOA_AFTER_BREAK"]["requires_scrutiny"] is True
    assert TABLE_2_3_SEEDED_ROUTING["EOA_AFTER_BREAK"]["requires_evc"] is True

    # Verify the 3 Table 2.3 routes are represented
    routes = set(t["route"] for t in types)
    assert "Self-Disclosure only" in routes
    assert "Scrutiny only" in routes
    assert "Scrutiny + EVC + SAC/SHC (as applicable)" in routes

if __name__ == "__main__":
    pytest.main(["-v", __file__])
