"""
=============================================================================
DETERMINISTIC APH RULES ENGINE & STAGE ROUTING
=============================================================================
Based on AICTE Approval Process Handbook (APH 2024-25 to 2026-27):
- Table 2.3 (Page 30 / PDF Page 46): Official Processing Steps by Nature of Application
  Routes:
  1. Self-Disclosure only (ONLY_SELF_DISCLOSURE)
  2. Scrutiny only (ONLY_SCRUTINY)
  3. Scrutiny + EVC + SAC/SHC (as applicable) (SCRUTINY_EVC_SAC)
- Clause 1.8 & 2.23.1: Scrutiny / Re-Scrutiny Process
  - Clause 1.8(g): Re-Scrutiny verifies ONLY deficiencies from Scrutiny.
- Clause 1.8(d/e/i) & 2.25: Decision Flow
  - Scrutiny / EVC / SHC / SAC recommend -> Executive Committee decides -> Council ratifies.
  - Member Secretary is NOT the sole final approver.
- Clause 1.11 & 2.24: Standing Appellate Committee (SAC) 7-day Appeal Window
- Clause 2.25(f): Security Deposit + Affidavit 3 in 15 days (10% penalty to 31 May, 20% to 31 July)
- Clause 1.10(ii): LoA valid for 2 Academic Years
- Chapter II Clause 2.1(e): EoA blocked when live lease equals maximum course duration
- Chapter VI Clause 6.17: Registered land lease minimum 30 years
=============================================================================
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, date

# Official APH 2024-27 Statutory Deadlines & Parameters
APH_STATUTORY_DEADLINES = {
    "SAC_APPEAL_WINDOW_DAYS": 7,          # Clause 1.11(a): 7-day appeal after LoD
    "SECURITY_DEPOSIT_DUE_DAYS": 15,       # Clause 2.25(f) & 1.12: Security Deposit + Affidavit 3 in 15 days
    "PENALTY_WINDOW_10_PERCENT": "31-May", # Clause 2.25(f): 10% penalty window up to 31st May
    "PENALTY_WINDOW_20_PERCENT": "31-July",# Clause 2.25(f): 20% penalty window up to 31st July (beyond which approval withdrawn)
    "NON_ADMISSION_AFFIDAVIT_DAYS": 7,     # 7-day non-admission affidavit
    "LOA_VALIDITY_YEARS": 2,               # Clause 1.10(ii): LoA valid 2 academic years from issuance
    "EOA_ACADEMIC_CALENDAR_CUTOFF": True,  # Clause 2.25(j): EoA blocked after Academic Calendar cutoff
    "MIN_LEASE_YEARS_STANDARD": 30,        # Chapter VI Clause 6.17: 30+ years registered lease deed
    "MIN_LEASE_YEARS_MEGA_METRO": 20,      # unsourced assumption, configurable (not found in APH 2024-27; Clause 6.17 requires 30 years)
}

# Official APH 2024-27 Clause Registry with Verbatim Snippet Provenance
APH_CLAUSE_CATALOG = {
    "EOA_SELF_DISCLOSURE": {
        "clause": "Chapter II, Clause 2.5",
        "clause_number": "2.5",
        "page": 28,
        "title": "Extension of Approval based on Self-Disclosure",
        "summary": "Grant of Extension of Approval based on online self-disclosure of facilities ensuring fulfillment of all APH norms.",
        "verbatim_snippet": "Extension of Approval based on Self-Disclosure",
    },
    "NEW_INSTITUTION_SCRUTINY": {
        "clause": "Chapter I, Clause 1.8",
        "clause_number": "1.8",
        "page": 22,
        "title": "Process for Evaluation of Application by Scrutiny / Re-Scrutiny Committee",
        "summary": "Evaluation of applicant documents by committee comprising Professor, Advocate (Bar Council), and Architect (CoA).",
        "verbatim_snippet": "Scrutiny / Re-Scrutiny Committee",
    },
    "RE_SCRUTINY_SCOPE": {
        "clause": "Chapter I, Clause 1.8(g)",
        "clause_number": "1.8",
        "page": 23,
        "title": "Re-Scrutiny Scope Verification Restriction",
        "summary": "The Re-Scrutiny Committee shall verify ONLY the deficiencies pointed out by the Scrutiny committee as per norms.",
        "verbatim_snippet": "Re-Scrutiny Committee shall verify ONLY the deficiencies pointed out by the Scrutiny committee",
    },
    "NEW_INSTITUTION_EVC": {
        "clause": "Chapter I, Clause 1.9",
        "clause_number": "1.9",
        "page": 23,
        "title": "Process for Evaluation of Application by Expert Visit Committee (EVC)",
        "summary": "Physical/online inspection of infrastructure, equipment, and faculty readiness with 30-minute geotagged video recording.",
        "verbatim_snippet": "Expert Visit Committee",
    },
    "INCREASE_INTAKE_EVC": {
        "clause": "Chapter II, Clause 2.6",
        "clause_number": "2.6",
        "page": 30,
        "title": "Scrutiny and EVC for Increase in Intake / New Courses",
        "summary": "Scrutiny and EVC conducted for any increase in intake in existing or new courses before first batch passes out.",
        "verbatim_snippet": "Increase in Intake",
    },
    "SAC_APPEAL_WINDOW": {
        "clause": "Chapter I Clause 1.11(a) / Chapter II Clause 2.24(a)",
        "clause_number": "2.24",
        "page": 45,
        "title": "Standing Appellate Committee (SAC) 7-Day Appeal Window",
        "summary": "Institution aggrieved by the decision of the Executive Committee shall have the right to appeal once to the Council within 7 days.",
        "verbatim_snippet": "aggrieved by the decision of the Executive Committee shall have the right to appeal once to the Council within 7 days",
    },
    "SHC_COMPLIANCE_VERIFICATION": {
        "clause": "Chapter II, Clause 2.23.3",
        "clause_number": "2.23.3",
        "page": 45,
        "title": "Process for Verification of Compliance through Standing Hearing Committee",
        "summary": "Verification of compliance short comings through Standing Hearing Committee whose recommendations are placed before Executive Committee.",
        "verbatim_snippet": "Process for Verification of Compliance through Standing Hearing Committee",
    },
    "DECISION_FLOW_COUNCIL": {
        "clause": "Chapter I Clause 1.8 & Chapter II Clause 2.25(a)",
        "clause_number": "2.25",
        "page": 47,
        "title": "Executive Committee Decision & Council Ratification",
        "summary": "Scrutiny / EVC / SHC / SAC provide recommendations. Executive Committee decides. Council ratifies. Member Secretary is NOT the final approving authority.",
        "verbatim_snippet": "Executive Committee",
    },
    "LAND_LEASE_LIVE_CUTOFF": {
        "clause": "Chapter II, Clause 2.1(e)",
        "clause_number": "2.1",
        "page": 28,
        "title": "Extension of Approval Land Live Lease Restriction",
        "summary": "Council shall not issue EoA from the year in which the Live Lease is equal to the number of years of the Course having maximum duration unless extended for a further 30 years.",
        "verbatim_snippet": "In case of Institutions having Lease agreement for Land, the Council shall not issue EoA from the Year in which the Live Lease is equal to the number of years of the Course having the maximum duration. However, if such Institutions submit the Lease extended for a further 30  years, application shall be considered for EoA.",
    },
    "LAND_LEASE_MINIMUM_30_YEARS": {
        "clause": "Chapter VI, Clause 6.17",
        "clause_number": "6.17",
        "page": 72,
        "title": "Registered Land Lease Minimum 30 Years Requirement",
        "summary": "Land required shall be on a long term lease for a minimum period of 30 years.",
        "verbatim_snippet": "long term lease for a minimum period of 30 years",
    },
    "LAND_LEASE_30_YEARS": {
        "clause": "Chapter II Clause 2.1(e) & Chapter VI Clause 6.17",
        "clause_number": "2.1",
        "page": 28,
        "title": "Registered Land Lease 30 Years & Live Lease EoA Block",
        "summary": "Live lease must exceed longest course duration or be extended for a further 30 years (Clause 2.1(e)). Registered lease must be minimum 30 years (Clause 6.17).",
        "verbatim_snippet": "In case of Institutions having Lease agreement for Land, the Council shall not issue EoA from the Year in which the Live Lease is equal to the number of years of the Course having the maximum duration. However, if such Institutions submit the Lease extended for a further 30  years, application shall be considered for EoA.",
    },
    "SECURITY_DEPOSIT_PENALTY": {
        "clause": "Chapter II, Clause 2.25(f)",
        "clause_number": "2.25",
        "page": 47,
        "title": "Security Deposit, Affidavit 3 and Penalty Windows",
        "summary": "Submission within 15 days; 10% penalty imposed up to 31st May, 20% penalty up to 31st July, beyond which approval is withdrawn.",
        "verbatim_snippet": "Affidavit 3 within 15 days",
    },
    "EOA_ACADEMIC_CALENDAR_CUTOFF": {
        "clause": "Chapter II, Clause 2.25(j)",
        "clause_number": "2.25",
        "page": 47,
        "title": "Extension of Approval Academic Calendar Cutoff",
        "summary": "Extension of Approval shall NOT be granted after the last date as mentioned in Academic Calendar.",
        "verbatim_snippet": "Extension of Approval shall NOT be granted after the last date as mentioned in Academic Calendar",
    },
    "TABLE_2_3_ROUTING": {
        "clause": "Chapter II, Table 2.3",
        "clause_number": "Table-2.3",
        "page": 46,
        "title": "Different Steps Involved in the Processing of the Applications",
        "summary": "Prescribes statutory routing across Self-Disclosure only, Scrutiny only, and Scrutiny + EVC + SAC/SHC (as applicable).",
        "verbatim_snippet": "Different Steps Involved in the Processing of the Applications",
    },
    "FIRE_SAFETY_NOC": {
        "clause": "Chapter VI, Clause 6.17",
        "clause_number": "6.17",
        "page": 72,
        "title": "Valid Fire Safety & Built-up Certificate Requirement",
        "summary": "The Technical Institutions shall follow Norms for Built-up requirements as provided in Annexure-3 of the Approval Process Handbook.",
        "verbatim_snippet": "Built-up requirements",
    },
    "PRINCIPAL_QUALIFICATION": {
        "clause": "Chapter VII, Clause 7.4(b)",
        "clause_number": "7.4",
        "page": 71,
        "title": "Requirement of Regular Qualified Principal / Director",
        "summary": "Institution not having qualified Principal for more than 12 months liable for penal action till appointment is completed.",
        "verbatim_snippet": "Principal",
    },
}

# -----------------------------------------------------------------------------
# TABLE-DRIVEN ROUTER FROM APH TABLE 2.3 (Page 30 / PDF Page 46)
# Routes:
# 1. Self-Disclosure only
# 2. Scrutiny only
# 3. Scrutiny + EVC + SAC/SHC (as applicable)
# -----------------------------------------------------------------------------
ROUTE_SELF_DISCLOSURE = "Self-Disclosure only"
ROUTE_SCRUTINY_ONLY = "Scrutiny only"
ROUTE_SCRUTINY_EVC_SAC = "Scrutiny + EVC + SAC/SHC (as applicable)"

TABLE_2_3_SEEDED_ROUTING: Dict[str, Dict[str, Any]] = {
    # 1. Extension of Approval based on Self-Disclosure
    "EOA_SELF_DISCLOSURE": {
        "nature_of_application": "Extension of Approval based on Self-Disclosure",
        "route": ROUTE_SELF_DISCLOSURE,
        "pipeline_name": "ONLY_SELF_DISCLOSURE",
        "documents": "Annexure-2",
        "self_disclosure": True,
        "requires_scrutiny": False,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SELF_DISCLOSURE", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.5 & Table 2.3 (Page 30)",
        "sla_days_total": 7, # sample value, configurable
    },
    # 2. Introduction/ Continuation of seats for Non Resident Indian(s)
    "NRI_SEATS": {
        "nature_of_application": "Introduction/ Continuation of seats for Non Resident Indian(s)",
        "route": ROUTE_SELF_DISCLOSURE,
        "pipeline_name": "ONLY_SELF_DISCLOSURE",
        "documents": "Annexure-2",
        "self_disclosure": True,
        "requires_scrutiny": False,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SELF_DISCLOSURE", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.11 & Table 2.3 (Page 30)",
        "sla_days_total": 7, # sample value, configurable
    },
    # 3. Conversion of Diploma Level into Degree Level and vice-versa
    "CONVERSION_DIPLOMA_DEGREE": {
        "nature_of_application": "Conversion of Diploma Level into Degree Level and vice-versa",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.14 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 4. Change in Name of Institution / Affiliating University
    "CHANGE_NAME_INSTITUTION": {
        "nature_of_application": "Change in the Name of the Institution or affiliating University/ Board or Type of Institution",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.8 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 5. Start new Programme/ Level in existing Institutions
    "NEW_PROGRAMME": {
        "nature_of_application": "To start new Programme/ Level in the existing Institutions",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.7 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 6. Merger of Institutions under same / different Trust
    "MERGER": {
        "nature_of_application": "Merger of Institutions under the same/ Different Trust/ Society/ Company operating in same Campus / City",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.13 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 7. Extension of Approval after a break / Restoration of Intake
    "EOA_AFTER_BREAK": {
        "nature_of_application": "Extension of Approval of the existing Institutions after a break in preceding AY / Restoration of Intake / Hibernation",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.15 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 8. Supernumerary seats for Foreign Nationals / OCI / Gulf
    "FN_OCI_GULF_SEATS": {
        "nature_of_application": "Introduction/ Continuation of supernumerary seats for Foreign Nationals/ OCI/ Gulf Countries",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.12 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 9. Increase in Intake / Additional Course(s)
    "INCREASE_INTAKE": {
        "nature_of_application": "Increase in Intake/ Additional Course(s)",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.6 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 10. Introduction of Integrated / Dual Degree Course
    "INTEGRATED_DUAL_DEGREE": {
        "nature_of_application": "Introduction of Integrated/Dual Degree Course",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.9 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 11. Introduction/ Continuation of Fellow Programme in Management
    "FELLOW_PROGRAMME": {
        "nature_of_application": "Introduction/ Continuation of Fellow Programme in Management",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.10 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 12. Change in Name of Course / Merger / Reduction in Intake
    "CHANGE_COURSE_NAME_REDUCTION": {
        "nature_of_application": "Change in Name of Course / Merger of Courses / Reduction in Intake",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.16 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 13. Collaboration and Twinning Programme
    "COLLABORATION_TWINNING": {
        "nature_of_application": "Introduction/ Continuation of Collaboration and Twinning Programme",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.18 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 14. Change of Site / Location
    "CHANGE_OF_SITE": {
        "nature_of_application": "Change of Site/ Location",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.17 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 15. Closure of Institution
    "CLOSURE": {
        "nature_of_application": "Closure of the Institution",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.21 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 16. Conversion of Women's Institution into Co-ed
    "CONVERSION_WOMEN_COED": {
        "nature_of_application": "Conversion of Women's Institution into Co-ed Institution and vice-versa",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.19 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 17. Closure of Programme / Course
    "CLOSURE_PROGRAMME": {
        "nature_of_application": "Closure of Programme(s)/ Course(s)",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.20 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 18. Change in Bank Details
    "CHANGE_BANK_DETAILS": {
        "nature_of_application": "Change in the Bank Details",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.22 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 19. Change in Name of Trust / Society
    "CHANGE_TRUST_NAME": {
        "nature_of_application": "Change in the Name of the Trust/ Society/ Company",
        "route": ROUTE_SCRUTINY_ONLY,
        "pipeline_name": "ONLY_SCRUTINY",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.23 & Table 2.3 (Page 30)",
        "sla_days_total": 14, # sample value, configurable
    },
    # 20. Conversion to Deemed-to-be-University
    "CONVERSION_DEEMED_UNIVERSITY": {
        "nature_of_application": "Type of Institution (Institution converted into a Deemed-to-be-University)",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.24 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
    # 21. Online Learning / ODL courses
    "ODL_ONLINE_LEARNING": {
        "nature_of_application": "Online Learning / ODL courses",
        "route": ROUTE_SCRUTINY_EVC_SAC,
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "documents": "Annexure-2",
        "self_disclosure": False,
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
        "requires_shc": False,  # SHC applies ONLY for compliance hearings
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
        "aph_clause_ref": "Chapter II, Clause 2.25 & Table 2.3 (Page 30)",
        "sla_days_total": 28, # sample value, configurable
    },
}

# Chapter I: Establishment of New Technical Institution (Chapter I, Clause 1.8 & 1.9)
# Follows: Scrutiny -> Re-Scrutiny -> EVC -> Executive Committee -> Council
CHAPTER_1_NEW_INSTITUTION_ROUTING: Dict[str, Any] = {
    "nature_of_application": "Setting up of New Technical Institution",
    "route": ROUTE_SCRUTINY_EVC_SAC,
    "pipeline_name": "SCRUTINY_EVC_SAC",
    "chapter": "Chapter I",
    "documents": "Annexure-1",
    "self_disclosure": False,
    "requires_scrutiny": True,
    "requires_re_scrutiny": True,
    "requires_evc": True,
    "requires_sac": False,  # SAC applies ONLY for appeals per Clause 1.11 / 2.24
    "requires_shc": False,  # SHC applies ONLY for compliance hearings
    "stages": ["SCRUTINY", "RE_SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
    "aph_clause_ref": "Chapter I, Clause 1.8 & 1.9 (Pages 22-24)",
    "sla_days_total": 45, # design choice, configurable
}

# Backwards compatibility map including Chapter I and Table 2.3
APH_PIPELINE_MAP: Dict[str, Dict[str, Any]] = {
    **TABLE_2_3_SEEDED_ROUTING,
    "NEW_INSTITUTION": CHAPTER_1_NEW_INSTITUTION_ROUTING,
}

# Alias mapping for flexible lookup
_TYPE_ALIASES = {
    "CLOSURE_INSTITUTION": "CLOSURE",
    "CLOSURE_OF_INSTITUTION": "CLOSURE",
    "NEW_PROG": "NEW_PROGRAMME",
    "INCREASE_IN_INTAKE": "INCREASE_INTAKE",
    "MERGER_INSTITUTIONS": "MERGER",
    "SITE_CHANGE": "CHANGE_OF_SITE",
    "EOA": "EOA_SELF_DISCLOSURE",
    "EXTENSION_OF_APPROVAL": "EOA_SELF_DISCLOSURE",
    "EOA_SELF_DISCLOSURE": "EOA_SELF_DISCLOSURE",
    "EOA_BREAK": "EOA_AFTER_BREAK",
    "RESTORATION_INTAKE": "EOA_AFTER_BREAK",
    "EOA_AFTER_BREAK": "EOA_AFTER_BREAK",
    "ODL": "ODL_ONLINE_LEARNING",
}


class APHRulesEngine:
    """
    Deterministic rules engine deciding application routing, SLAs, deadlines, and APH provenance.
    Purely deterministic; zero LLM modification of state or deadlines.
    """

    @staticmethod
    def get_all_table_2_3_types() -> List[Dict[str, Any]]:
        """Returns all seeded Table 2.3 application types and routes."""
        res = []
        for key, val in TABLE_2_3_SEEDED_ROUTING.items():
            res.append({
                "code": key,
                "nature_of_application": val["nature_of_application"],
                "route": val["route"],
                "pipeline_name": val["pipeline_name"],
                "documents": val["documents"],
                "requires_scrutiny": val["requires_scrutiny"],
                "requires_evc": val["requires_evc"],
                "requires_sac": val["requires_sac"],
                "clause_ref": val["aph_clause_ref"],
            })
        return res

    @staticmethod
    def determine_pipeline(application_type: str) -> Dict[str, Any]:
        """
        Determines the official processing pipeline from APH Table 2.3.
        Routes:
        - Self-Disclosure only (ONLY_SELF_DISCLOSURE)
        - Scrutiny only (ONLY_SCRUTINY)
        - Scrutiny + EVC + SAC/SHC (as applicable) (SCRUTINY_EVC_SAC)
        """
        clean_type = application_type.upper().strip()
        resolved_key = _TYPE_ALIASES.get(clean_type, clean_type)
        if resolved_key == "NEW_INSTITUTION":
            return CHAPTER_1_NEW_INSTITUTION_ROUTING
        pipeline_info = TABLE_2_3_SEEDED_ROUTING.get(resolved_key)
        
        if not pipeline_info:
            # Fallback to Scrutiny + EVC if unrecognized
            return {
                "nature_of_application": application_type,
                "route": ROUTE_SCRUTINY_EVC_SAC,
                "pipeline_name": "SCRUTINY_EVC_SAC",
                "documents": "Annexure-2",
                "self_disclosure": False,
                "requires_scrutiny": True,
                "requires_evc": True,
                "requires_sac": False,
                "requires_shc": False,
                "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"],
                "aph_clause_ref": "APH 2024-27, clause TBD [Sample value, configurable]",
                "sla_days_total": 28,
            }
        return pipeline_info

    @staticmethod
    def build_route_stage_path(
        application_type: str,
        is_appeal: bool = False,
        is_compliance_verification: bool = False,
    ) -> List[str]:
        """
        Builds the stage path dynamically from the application's Table 2.3 route.
        Shows SAC only for appeals and SHC only when compliance verification applies;
        never shows them universally for every application.
        """
        pipeline = APHRulesEngine.determine_pipeline(application_type)
        stages = list(pipeline.get("stages", ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]))
        
        # Insert conditional hearing stages before EXECUTIVE_COMMITTEE
        if "EXECUTIVE_COMMITTEE" in stages:
            ec_index = stages.index("EXECUTIVE_COMMITTEE")
            if is_compliance_verification:
                stages.insert(ec_index, "SHC_HEARING")
                ec_index += 1
            if is_appeal:
                stages.insert(ec_index, "SAC_HEARING")
        return stages

    @staticmethod
    def get_next_stage(pipeline_name: str, current_stage: str) -> Optional[str]:
        """
        Calculates next stage in deterministic sequence.
        Returns None if application has completed the final stage (COUNCIL_RATIFIED).
        """
        # Standing hearings advance to Executive Committee
        if current_stage in ["SAC_HEARING", "STANDING_HEARING", "SHC_HEARING"]:
            return "EXECUTIVE_COMMITTEE"

        if pipeline_name in ["SCRUTINY_EVC", "NEW_INSTITUTION"]:
            stages = CHAPTER_1_NEW_INSTITUTION_ROUTING["stages"]
            if current_stage in stages:
                curr_idx = stages.index(current_stage)
                if curr_idx + 1 < len(stages):
                    return stages[curr_idx + 1]
                return None

        for p_key, p_val in TABLE_2_3_SEEDED_ROUTING.items():
            if p_val["pipeline_name"] == pipeline_name:
                stages = p_val["stages"]
                if current_stage in stages:
                    curr_idx = stages.index(current_stage)
                    if curr_idx + 1 < len(stages):
                        return stages[curr_idx + 1]
                    return None
        
        # Default fallback sequence
        default_seq = ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_RATIFIED"]
        if current_stage in default_seq:
            curr_idx = default_seq.index(current_stage)
            if curr_idx + 1 < len(default_seq):
                return default_seq[curr_idx + 1]
        return None

    @staticmethod
    def calculate_stage_sla(stage_name: str) -> int:
        """
        Allocated SLA working days per stage.
        Labeled strictly as: [Sample value, configurable].
        Not statutory. Statutory dates come from Academic Calendar & Public Notice.
        """
        slas = {
            "SELF_DISCLOSURE": 3,
            "SCRUTINY": 7,
            "RE_SCRUTINY": 5,
            "EVC": 10,
            "STANDING_HEARING": 7,
            "STANDING_APPELLATE": 7,
            "EXECUTIVE_COMMITTEE": 5,
            "COUNCIL_RATIFIED": 4,
        }
        return slas.get(stage_name, 7)

    @staticmethod
    def verify_re_scrutiny_scope(
        original_scrutiny_deficiencies: List[str],
        items_to_verify: List[str],
    ) -> Dict[str, Any]:
        """
        APH Clause 1.8(g) Enforcement:
        The Re-Scrutiny Committee shall verify ONLY the deficiencies pointed out
        by the Scrutiny committee. Any additional deficiency not logged during preliminary
        scrutiny cannot be introduced at this stage.
        """
        allowed = set(d.strip().lower() for d in original_scrutiny_deficiencies)
        verified = []
        out_of_scope = []
        for item in items_to_verify:
            if item.strip().lower() in allowed:
                verified.append(item)
            else:
                out_of_scope.append(item)

        is_compliant = len(out_of_scope) == 0
        return {
            "is_compliant": is_compliant,
            "verified_deficiencies": verified,
            "out_of_scope_items": out_of_scope,
            "aph_clause_ref": "Chapter I, Clause 1.8(g) (Page 7)",
            "rule": "Re-Scrutiny verifies ONLY deficiencies from Scrutiny.",
            "message": (
                "Re-Scrutiny verification scope compliant with Clause 1.8(g)."
                if is_compliant
                else f"Scope Violation: Items {out_of_scope} were not identified during preliminary Scrutiny."
            ),
        }

    @staticmethod
    def evaluate_decision_authority(
        stage_action: str,
        actor_role: str,
    ) -> Dict[str, Any]:
        """
        APH Clause 1.8(d/e/i) & Clause 2.25:
        Decision Flow & Authority Matrix:
        - Scrutiny / Re-Scrutiny: Recommends only.
        - EVC: Recommends only.
        - SHC: Verifies compliance.
        - SAC: Hears appeals.
        - Executive Committee (EC): Decides approval / rejection.
        - Council: Ratifies the Executive Committee decision.
        - Member Secretary is NOT the sole final approver.
        """
        matrix = {
            "RECOMMEND_SCRUTINY": ["REGIONAL_OFFICER", "SCRUTINY_MEMBER"],
            "RECOMMEND_EVC": ["COMMITTEE_MEMBER", "REGIONAL_OFFICER"],
            "VERIFY_SHC": ["BUREAU_OFFICER", "SHC_MEMBER"],
            "HEAR_SAC": ["SAC_MEMBER", "BUREAU_OFFICER"],
            "DECIDE_EC": ["EXECUTIVE_COMMITTEE", "BUREAU_OFFICER"],
            "RATIFY_COUNCIL": ["COUNCIL", "SUPER_ADMIN"],
        }
        allowed_roles = matrix.get(stage_action, ["SUPER_ADMIN"])
        is_authorized = actor_role in allowed_roles
        return {
            "stage_action": stage_action,
            "actor_role": actor_role,
            "is_authorized": is_authorized,
            "allowed_roles": allowed_roles,
            "decision_flow_rule": "Committees recommend -> Executive Committee decides -> Council ratifies.",
            "aph_clause_ref": "Chapter I Clause 1.8 & Chapter II Clause 2.25",
        }

    @staticmethod
    def evaluate_registered_lease(
        lease_start_date: date,
        lease_end_date: date,
        is_mega_metro: bool = False,
        longest_course_duration_years: int = 4,
        evaluation_date: Optional[date] = None,
        eoa_warning_offsets_months: Optional[List[int]] = None,
        lease_expiry_offsets_months: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Registered Land Lease Logic per Chapter II Clause 2.1(e) & Chapter VI Clause 6.17:
        - Registered lease minimum period: 30 years (Chapter VI Clause 6.17).
        - 20 years for Mega/Metro cities: unsourced assumption, configurable (not found in APH 2024-27).
        - Chapter II Clause 2.1(e): The Council shall not issue EoA from the Year in which
          the Live Lease is equal to the number of years of the Course having maximum duration.
        - Calculates: years remaining, course duration threshold, exact EoA block date,
          configurable early warning alerts (default 12/6/3 months before EoA block date),
          lease expiry alerts (default 12/6/3 months before lease expiration), and EoA block status.
        """
        if evaluation_date is None:
            evaluation_date = date.today()

        if eoa_warning_offsets_months is None:
            eoa_warning_offsets_months = [12, 6, 3]
        if lease_expiry_offsets_months is None:
            lease_expiry_offsets_months = [12, 6, 3]

        total_lease_days = (lease_end_date - lease_start_date).days
        total_lease_years = round(total_lease_days / 365.25, 2)
        
        # Standard statutory minimum is 30 years per Clause 6.17.
        # 20 years for Mega/Metro is labeled as: unsourced assumption, configurable.
        threshold_years = 20.0 if is_mega_metro else 30.0
        threshold_note = (
            "20 years for Mega/Metro cities (unsourced assumption, configurable; standard statutory requirement is 30 years per Clause 6.17)"
            if is_mega_metro
            else "30 years registered lease deed per Chapter VI Clause 6.17"
        )

        remaining_days = (lease_end_date - evaluation_date).days
        years_remaining = round(remaining_days / 365.25, 2)

        # Block date: exact date when remaining live lease equals longest course duration
        block_days = int(longest_course_duration_years * 365.25)
        block_date = lease_end_date - timedelta(days=block_days)

        is_blocked = remaining_days <= block_days

        # Configurable early warning milestones for EoA Block Date (default 12/6/3 months)
        eoa_warning_milestones = []
        active_eoa_tier = None
        for offset_m in sorted(eoa_warning_offsets_months, reverse=True):
            alert_offset_days = int(offset_m * 30.4375)
            target_alert_date = block_date - timedelta(days=alert_offset_days)
            is_trig = (evaluation_date >= target_alert_date) and not is_blocked
            if is_trig:
                active_eoa_tier = offset_m
            eoa_warning_milestones.append({
                "offset_months": offset_m,
                "alert_date": target_alert_date.isoformat(),
                "is_triggered": is_trig,
            })

        # Configurable lease expiry alerts (default 12/6/3 months before lease end date)
        is_lease_expired = evaluation_date >= lease_end_date
        lease_expiry_milestones = []
        active_lease_expiry_tier = None
        for offset_m in sorted(lease_expiry_offsets_months, reverse=True):
            alert_offset_days = int(offset_m * 30.4375)
            target_alert_date = lease_end_date - timedelta(days=alert_offset_days)
            is_trig = (evaluation_date >= target_alert_date) and not is_lease_expired
            if is_trig:
                active_lease_expiry_tier = offset_m
            lease_expiry_milestones.append({
                "offset_months": offset_m,
                "alert_date": target_alert_date.isoformat(),
                "is_triggered": is_trig,
            })

        is_early_warning = (active_eoa_tier is not None) or (active_lease_expiry_tier is not None)

        if is_lease_expired:
            status = "LEASE_EXPIRED"
            message = f"Lease Expired: The registered land lease expired on {lease_end_date.isoformat()}."
        elif is_blocked:
            status = "BLOCKED_EOA_DENIED"
            message = (
                f"EoA Blocked: Remaining live lease ({years_remaining} yrs) has reached maximum course duration threshold "
                f"({longest_course_duration_years} yrs). Extension of Approval cannot be issued unless extended for a further 30 years per Chapter II Clause 2.1(e)."
            )
        elif is_early_warning:
            status = "ALERT_EXPIRING_SOON"
            alerts = []
            if active_eoa_tier is not None:
                alerts.append(f"EoA block threshold within {active_eoa_tier} months")
            if active_lease_expiry_tier is not None:
                alerts.append(f"Lease expiration within {active_lease_expiry_tier} months")
            message = (
                f"Early Warning Alert: Remaining live lease ({years_remaining} yrs) is approaching maximum course duration threshold "
                f"({longest_course_duration_years} yrs) [{', '.join(alerts)}]. "
                f"EoA will be blocked on {block_date.isoformat()} unless extended for a further 30 years per Chapter II Clause 2.1(e)."
            )
        else:
            status = "COMPLIANT"
            message = f"Lease Compliant: {years_remaining} years remaining (Threshold: {threshold_years} yrs). EoA block date: {block_date.isoformat()}."

        return {
            "total_lease_years": total_lease_years,
            "required_threshold_years": threshold_years,
            "threshold_note": threshold_note,
            "is_initial_term_valid": total_lease_years >= threshold_years,
            "years_remaining": max(0.0, years_remaining),
            "longest_course_duration_years": longest_course_duration_years,
            "threshold_course_duration_years": longest_course_duration_years,
            "block_date": block_date.isoformat(),
            "eoa_block_date": block_date.isoformat(),
            "lease_end_date": lease_end_date.isoformat(),
            "is_eoa_blocked": is_blocked,
            "is_lease_expired": is_lease_expired,
            "is_early_warning": is_early_warning,
            "alert_triggered": is_early_warning or is_blocked or is_lease_expired,
            "status": status,
            "message": message,
            "eoa_warning_offsets_months": eoa_warning_offsets_months,
            "lease_expiry_offsets_months": lease_expiry_offsets_months,
            "active_eoa_warning_tier": active_eoa_tier,
            "active_lease_expiry_tier": active_lease_expiry_tier,
            "eoa_warning_milestones": eoa_warning_milestones,
            "lease_expiry_milestones": lease_expiry_milestones,
            "aph_clause_ref": "Chapter II Clause 2.1(e) & Chapter VI Clause 6.17",
        }

    @staticmethod
    def get_clause_provenance(action_or_clause_key: str) -> Dict[str, Any]:
        """
        Returns the exact APH 2024-27 clause, title, handbook page number, and summary.
        """
        return APH_CLAUSE_CATALOG.get(
            action_or_clause_key,
            {
                "clause": "APH 2024-27, clause TBD",
                "page": 0,
                "title": "General Approval Provision",
                "summary": "Sample value, configurable pending APH 2024-27 compilation.",
            },
        )
