"""
=============================================================================
DETERMINISTIC APH RULES ENGINE & STAGE ROUTING
=============================================================================
Based on AICTE Approval Process Handbook (APH 2024-25 to 2026-27):
- Table 2.3 (Page 30 / PDF Page 46): Official Processing Steps by Nature of Application
- Annexure-7 (Page 100 / PDF Page 116): Process Flow Chart for Approval (LoA / LoR)
- Clause 1.8 & 2.23.1: Scrutiny / Re-Scrutiny Process
- Clause 1.9 & 2.23.2: EVC Inspection Process
- Clause 1.11 & 2.24: Standing Appellate Committee (SAC) 7-day Appeal Window
- Clause 2.1(e) & 6.17(a): 30-Year Registered Land Lease Norms
=============================================================================
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

# Official APH 2024-27 Clause Registry with Page Provenance
APH_CLAUSE_CATALOG = {
    "EOA_SELF_DISCLOSURE": {
        "clause": "Chapter II, Clause 2.5",
        "page": 15,
        "title": "Extension of Approval based on Self-Disclosure",
        "summary": "Grant of Extension of Approval based on online self-disclosure of facilities ensuring fulfillment of all APH norms.",
    },
    "NEW_INSTITUTION_SCRUTINY": {
        "clause": "Chapter I, Clause 1.8",
        "page": 7,
        "title": "Process for Evaluation of Application by Scrutiny / Re-Scrutiny Committee",
        "summary": "Evaluation of applicant documents by committee comprising Professor, Advocate (Bar Council), and Architect (CoA).",
    },
    "NEW_INSTITUTION_EVC": {
        "clause": "Chapter I, Clause 1.9",
        "page": 8,
        "title": "Process for Evaluation of Application by Expert Visit Committee (EVC)",
        "summary": "Physical/online inspection of infrastructure, equipment, and faculty readiness with 30-minute geotagged video recording.",
    },
    "INCREASE_INTAKE_EVC": {
        "clause": "Chapter II, Clause 2.6(j)",
        "page": 17,
        "title": "Scrutiny and EVC for Increase in Intake / New Courses",
        "summary": "Scrutiny and EVC conducted for any increase in intake in existing or new courses before first batch passes out.",
    },
    "SAC_APPEAL_WINDOW": {
        "clause": "Chapter I Clause 1.11(a) / Chapter II Clause 2.24(a)",
        "page": 9,
        "title": "Statutory 7-Day Standing Appellate Committee (SAC) Appeal",
        "summary": "Applicant aggrieved by decision has the right to appeal through portal within 7 days from the date of issue of Letter of Deficiency (LoD).",
    },
    "LAND_LEASE_30_YEARS": {
        "clause": "Chapter II Clause 2.1(e) & Chapter VI Clause 6.17(a)",
        "page": 12,
        "title": "30-Year Registered Land Lease Requirement",
        "summary": "Live lease must be at least equal to maximum duration of course. If lease is near expiration, submission of lease extended for 30 years is mandatory.",
    },
    "FIRE_SAFETY_NOC": {
        "clause": "Chapter VI, Clause 6.17(i)",
        "page": 57,
        "title": "Valid Fire Safety Certificate Requirement",
        "summary": "Valid Fire Safety Certificate shall be obtained from Competent Authority before submitting application.",
    },
    "PRINCIPAL_QUALIFICATION": {
        "clause": "Chapter VII, Clause 7.4(b)",
        "page": 71,
        "title": "Requirement of Regular Qualified Principal / Director",
        "summary": "Institution not having qualified Principal for more than 12 months liable for penal action till appointment is completed.",
    },
}

# Official APH Table 2.3 Routing Pipelines (Page 30 / PDF Page 46)
APH_PIPELINE_MAP: Dict[str, Dict[str, Any]] = {
    "EXTENSION_OF_APPROVAL": {
        "pipeline_name": "ONLY_SELF_DISCLOSURE",
        "stages": ["SELF_DISCLOSURE", "COUNCIL_DECISION"],
        "requires_scrutiny": False,
        "requires_evc": False,
        "requires_sac": False,
        "aph_clause_ref": "Chapter II, Clause 2.5 (Page 15)",
        "sla_days_total": 7, # sample value, configurable
    },
    "NEW_INSTITUTION": {
        "pipeline_name": "SCRUTINY_EVC",
        "stages": ["SCRUTINY", "EVC", "EXECUTIVE_COMMITTEE", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": False,
        "aph_clause_ref": "Chapter I, Clause 1.8 & 1.9 (Pages 7-8)",
        "sla_days_total": 21,
    },
    "INCREASE_INTAKE": {
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "stages": ["SCRUTINY", "EVC", "STANDING_HEARING", "EXECUTIVE_COMMITTEE", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": True,
        "aph_clause_ref": "Chapter II, Clause 2.6 & Table 2.3 (Pages 16, 30)",
        "sla_days_total": 28,
    },
    "NEW_PROGRAMME": {
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "stages": ["SCRUTINY", "EVC", "STANDING_HEARING", "EXECUTIVE_COMMITTEE", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": True,
        "aph_clause_ref": "Chapter II, Clause 2.7 & Table 2.3 (Pages 17, 30)",
        "sla_days_total": 28,
    },
    "CHANGE_OF_SITE": {
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "stages": ["SCRUTINY", "EVC", "STANDING_HEARING", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": True,
        "aph_clause_ref": "Chapter II, Clause 2.17 & Table 2.3 (Pages 25, 30)",
        "sla_days_total": 28,
    },
    "CLOSURE": {
        "pipeline_name": "ONLY_SCRUTINY",
        "stages": ["SCRUTINY", "EXECUTIVE_COMMITTEE", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": False,
        "requires_sac": False,
        "aph_clause_ref": "Chapter II, Clause 2.21 & Table 2.3 (Pages 27, 30)",
        "sla_days_total": 14,
    },
    "CONVERSION_DIPLOMA_DEGREE": {
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "stages": ["SCRUTINY", "EVC", "STANDING_HEARING", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": True,
        "aph_clause_ref": "Chapter II, Clause 2.14 & Table 2.3 (Pages 23, 30)",
        "sla_days_total": 28,
    },
    "MERGER": {
        "pipeline_name": "SCRUTINY_EVC_SAC",
        "stages": ["SCRUTINY", "EVC", "STANDING_HEARING", "COUNCIL_DECISION"],
        "requires_scrutiny": True,
        "requires_evc": True,
        "requires_sac": True,
        "aph_clause_ref": "Chapter II, Clause 2.13 & Table 2.3 (Pages 21, 30)",
        "sla_days_total": 28,
    },
}

class APHRulesEngine:
    """
    Deterministic rules engine deciding application routing, SLAs, deadlines, and APH provenance.
    Purely deterministic; zero LLM modification of state or deadlines.
    """

    @staticmethod
    def determine_pipeline(application_type: str) -> Dict[str, Any]:
        """
        Determines the official processing pipeline from APH Table 2.3.
        """
        clean_type = application_type.upper().strip()
        pipeline_info = APH_PIPELINE_MAP.get(clean_type)
        if not pipeline_info:
            # Fallback to Scrutiny + EVC if unrecognized
            return {
                "pipeline_name": "CUSTOM_APH",
                "stages": ["SCRUTINY", "EVC", "COUNCIL_DECISION"],
                "requires_scrutiny": True,
                "requires_evc": True,
                "requires_sac": False,
                "aph_clause_ref": "APH 2024-27, clause TBD [Sample value, configurable]",
                "sla_days_total": 21,
            }
        return pipeline_info

    @staticmethod
    def get_next_stage(pipeline_name: str, current_stage: str) -> Optional[str]:
        """
        Calculates next stage in deterministic sequence.
        Returns None if application has completed the final stage.
        """
        # Find matching pipeline stages
        for p_key, p_val in APH_PIPELINE_MAP.items():
            if p_val["pipeline_name"] == pipeline_name:
                stages = p_val["stages"]
                if current_stage in stages:
                    curr_idx = stages.index(current_stage)
                    if curr_idx + 1 < len(stages):
                        return stages[curr_idx + 1]
                    return None
        
        # Default sequence
        default_seq = ["SCRUTINY", "EVC", "STANDING_HEARING", "COUNCIL_DECISION", "APPROVED"]
        if current_stage in default_seq:
            curr_idx = default_seq.index(current_stage)
            if curr_idx + 1 < len(default_seq):
                return default_seq[curr_idx + 1]
        return None

    @staticmethod
    def calculate_stage_sla(stage_name: str) -> int:
        """
        Allocated SLA working days per stage.
        Sample values, configurable pending APH compiler execution.
        """
        slas = {
            "SELF_DISCLOSURE": 3,
            "SCRUTINY": 7,
            "RE_SCRUTINY": 5,
            "EVC": 10,
            "STANDING_HEARING": 7,
            "STANDING_APPELLATE": 7, # Sourced from Clause 1.11(a) (7-day window)
            "EXECUTIVE_COMMITTEE": 5,
            "COUNCIL_DECISION": 4,
        }
        return slas.get(stage_name, 7)

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
