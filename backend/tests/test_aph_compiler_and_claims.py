"""
Tests for Group C: Accuracy of Claims & Differentiator Verification
- Priority scorer renamed to "Weighted Risk Score with Factor Contributions"
- APH compiler 5-step lifecycle: upload -> LLM draft -> admin diff -> human approval -> versioned activation
- EVC dispatch: recommend panels for officer confirmation (portal selection) with configurable conflict policy assumptions
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import Application, LLMDraft, RuleVersion
from app.scoped_dal import RequestContext
from app.routers.signature_features import (
    get_single_app_shap,
    get_next_best_action_queue,
    compile_aph_handbook,
    get_aph_compiler_diff,
    approve_compiled_aph_ruleset,
    CompileAPHRequest,
)
from app.routers.evc_hub import suggest_smart_panel, SuggestPanelRequest

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_priority_scorer_rename_and_factor_contributions(db):
    """Clause 10: Verify priority scorer is titled Weighted Risk Score with Factor Contributions."""
    app = db.query(Application).first()
    assert app is not None

    res = get_single_app_shap(application_id=app.id, db=db)
    assert "weighted risk score with per-factor contributions" in res["scorer_name"].lower()
    assert "weighted risk score with per-factor contributions" in res["model_type"].lower()
    assert "factor_contributions" in res
    assert len(res["factor_contributions"]) >= 4

    # Every factor must have an explicit contribution and impact
    for factor in res["factor_contributions"]:
        assert "factor_name" in factor
        assert "factor_contribution" in factor
        assert factor["impact"] in ["INCREASES_RISK", "REDUCES_RISK"]

    # Queue must also feature factor breakdown
    queue_res = get_next_best_action_queue(db=db)
    assert queue_res["count"] > 0
    first_item = queue_res["queue"][0]
    assert "factor_contributions" in first_item
    assert "weighted_risk_score" in first_item

def test_aph_compiler_full_5_step_flow(db):
    """
    Clause 11: APH compiler flow:
    upload/raw text -> LLM draft -> admin diff -> human approval -> versioned activation.
    """
    officer_a_ctx = RequestContext(user_id="usr-aph-compiler-officer-a", role="REGIONAL_OFFICER")
    officer_b_ctx = RequestContext(user_id="usr-aph-compiler-officer-b", role="BUREAU_HEAD")

    # Step 1 & 2: Upload / Generate LLM Draft
    req = CompileAPHRequest(
        aph_edition="2024-25 to 2026-27",
        raw_text_snippet="Approval Process Handbook 2024-27 Chapter II Clause 2.1 Land Norms",
    )
    draft_res = compile_aph_handbook(payload=req, ctx=officer_a_ctx, db=db)
    assert draft_res["status"] == "COMPILATION_DRAFTED"
    assert draft_res["classification"] == "SUGGEST_ONLY"
    draft_id = draft_res["draft_id"]

    draft_record = db.query(LLMDraft).filter(LLMDraft.id == draft_id).first()
    assert draft_record is not None
    assert draft_record.status == "PENDING_HUMAN_REVIEW"
    assert draft_record.requester_id == officer_a_ctx.user_id

    # Step 3: Admin Diff Review
    diff_res = get_aph_compiler_diff(draft_id=draft_id, db=db)
    assert diff_res["status"] == "DIFF_GENERATED"
    assert "workflow_steps" in diff_res
    assert len(diff_res["workflow_steps"]) == 5
    assert "active_version" in diff_res
    assert "diff_text" in diff_res

    # Step 4: Human Approval Gate with Pairwise SoD
    # Self-approval must be blocked
    with pytest.raises(Exception):
        approve_compiled_aph_ruleset(draft_id=draft_id, ctx=officer_a_ctx, db=db)

    # Different officer approves
    approval_res = approve_compiled_aph_ruleset(draft_id=draft_id, ctx=officer_b_ctx, db=db)
    assert approval_res["status"] == "OFFICIALLY_ACTIVATED"
    assert approval_res["approved_by"] == officer_b_ctx.user_id

    # Step 5: Versioned Activation in DB
    db.refresh(draft_record)
    assert draft_record.status in ["APPROVED", "ACCEPTED_OFFICIAL"]
    assert draft_record.approver_id == officer_b_ctx.user_id

    active_rule = db.query(RuleVersion).filter(RuleVersion.approved_by == officer_b_ctx.user_id).first()
    assert active_rule is not None
    assert active_rule.is_active is True

def test_evc_dispatch_portal_selection_and_configurable_rules(db):
    """
    Clause 12: EVC dispatch:
    - Recommend panels for officer confirmation (portal selection)
    - Mark expert-conflict rules as policy assumptions, configurable
    """
    app = db.query(Application).first()
    assert app is not None

    req = SuggestPanelRequest(
        application_id=app.id,
        proposed_date="2026-11-15",
        mode="ON_SITE",
    )
    res = suggest_smart_panel(payload=req, db=db)

    assert res["classification"] == "SUGGEST_ONLY"
    assert "Recommend panels for officer confirmation (portal selection)" in res["dispatch_mode"]
    assert "policy assumptions, configurable" in res["conflict_rules"]
    assert len(res["suggested_panel"]) >= 3
    for expert in res["suggested_panel"]:
        assert "clause_ref" in expert
        assert "conflict_free" in expert

def test_verifier_marks_wrong_citation_unverified():
    """Task 1 Test: Wrong page citation fails the verifier and is marked UNVERIFIED."""
    from app.llm_adapter import LLMAdapter
    # Quote from page 23 placed under cited page 99
    pdf_pages = {
        23: "Process for Evaluation of the Application by the Scrutiny/ Re-Scrutiny Committee",
        99: "Unrelated page content with completely different text."
    }
    rules = [{
        "rule_id": "test_wrong_page",
        "category": "routing_rules",
        "clause_id": "Chapter I, Clause 1.8",
        "page_number": 99,
        "verbatim_quote": "Process for Evaluation of the Application by the Scrutiny/ Re-Scrutiny Committee"
    }]
    verified_rules, confidence, all_passed = LLMAdapter.verify_rules(rules, pdf_pages)
    assert verified_rules[0]["verification_status"] == "UNVERIFIED"
    assert "Quote not found verbatim" in verified_rules[0]["verifier_reason"]
    assert all_passed is False
    assert confidence == 0.0

def test_verifier_marks_tampered_quote_unverified():
    """Task 1 Test: Tampered quote fails the verifier and is marked UNVERIFIED."""
    from app.llm_adapter import LLMAdapter
    pdf_pages = {
        72: "The Technical Institutions shall follow Norms for Built-up requirements as provided in Annexure"
    }
    rules = [{
        "rule_id": "test_tampered_quote",
        "category": "land_norms",
        "clause_id": "Chapter VI, Clause 6.17",
        "page_number": 72,
        "verbatim_quote": "The Technical Institutions shall NEVER follow Norms for Built-up requirements"
    }]
    verified_rules, confidence, all_passed = LLMAdapter.verify_rules(rules, pdf_pages)
    assert verified_rules[0]["verification_status"] == "UNVERIFIED"
    assert all_passed is False

def test_unverified_rule_cannot_be_approved(db):
    """Task 1 Test: Draft containing UNVERIFIED rules cannot be approved/activated."""
    from fastapi import HTTPException
    from app.models import LLMDraft
    
    officer_a = RequestContext(user_id="usr-test-officer-requester", role="REGIONAL_OFFICER")
    officer_b = RequestContext(user_id="usr-test-officer-approver", role="BUREAU_HEAD")
    
    unverified_yaml = """# AICTE APH Ruleset
routing_rules:
  NEW_INSTITUTION:
    pipeline: SCRUTINY_EVC
    verification: UNVERIFIED
    verbatim_quote: "Tampered Quote"
"""
    draft = LLMDraft(
        draft_type="APH_RULE_DRAFT",
        related_entity_type="RULESET",
        related_entity_id="APH-TEST-UNVERIFIED",
        prompt_hash="dummy-prompt-hash-1234",
        model_version="OFFLINE DETERMINISTIC EXTRACTOR",
        generated_content=unverified_yaml,
        confidence_score=0.4,
        source_citations="[]",
        status="PENDING_HUMAN_REVIEW",
        requester_id=officer_a.user_id,
    )
    db.add(draft)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        approve_compiled_aph_ruleset(draft_id=draft.id, ctx=officer_b, db=db)
    
    assert exc_info.value.status_code == 400
    assert "unverified rules detected" in exc_info.value.detail.lower()

def test_no_key_fallback_is_labelled_offline_extractor(db):
    """Task 1 Test: When no API key is provided, system falls back to OFFLINE DETERMINISTIC EXTRACTOR."""
    import os
    from app.llm_adapter import LLMAdapter
    
    old_key = os.environ.get("LLM_API_KEY")
    if "LLM_API_KEY" in os.environ:
        del os.environ["LLM_API_KEY"]
    if "OPENAI_API_KEY" in os.environ:
        del os.environ["OPENAI_API_KEY"]
    
    adapter = LLMAdapter()
    assert adapter.is_offline is True
    assert adapter.model_name == "OFFLINE DETERMINISTIC EXTRACTOR"
    
    req = CompileAPHRequest(aph_edition="2024-25 to 2026-27")
    officer = RequestContext(user_id="usr-test-offline-label", role="REGIONAL_OFFICER")
    res = compile_aph_handbook(payload=req, ctx=officer, db=db)
    assert res["extractor_model"] == "OFFLINE DETERMINISTIC EXTRACTOR"
    assert res["is_offline_extractor"] is True

def test_copilot_bm25_weak_evidence_guard(db):
    """Task 1 Test: Query with weak/absent statutory evidence answers 'not found in APH'."""
    from app.routers.copilot_chat import copilot_chat, ChatRequest
    payload = ChatRequest(
        message="What is quantum gravity and who won the 2026 world cup football match?"
    )
    resp = copilot_chat(payload=payload, db=db)
    assert "not found in aph" in resp.answer_markdown.lower()
    assert len(resp.citations) == 0
    assert resp.confidence_score == 0.0
