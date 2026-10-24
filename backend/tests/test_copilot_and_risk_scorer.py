"""
Unit tests for AICTE Compliance & APH Copilot and weighted risk score with per-factor contributions (SIH26262).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import Application
from app.routers.copilot_chat import get_suggested_prompts, copilot_chat, ChatRequest
from app.routers.signature_features import get_single_app_shap, get_next_best_action_queue

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_copilot_suggested_prompts():
    """Verify that suggested prompts are available for quick 1-click evaluation."""
    data = get_suggested_prompts()
    assert "suggested_prompts" in data
    assert len(data["suggested_prompts"]) >= 5
    assert any("Deficiency" in p["label"] for p in data["suggested_prompts"])
    assert any("Lease" in p["label"] for p in data["suggested_prompts"])

def test_copilot_grounded_clause_citations(db):
    """Verify that Copilot queries return accurate APH clause citations and adhere to SUGGEST-ONLY boundary."""
    payload = ChatRequest(
        message="What is the cure window and procedure if scrutiny committee issues a deficiency memo?"
    )
    resp = copilot_chat(payload=payload, db=db)
    assert resp.authority_boundary == "SUGGEST_ONLY"
    assert resp.confidence_score >= 0.85
    assert len(resp.citations) > 0
    clauses = [c.clause for c in resp.citations]
    assert any("1.8" in c for c in clauses)
    assert "SUGGEST-ONLY" in resp.statutory_banner

def test_copilot_case_specific_context(db):
    """Verify that Copilot can report docket status when provided with an application ID."""
    app_record = db.query(Application).first()
    assert app_record is not None, "Need at least one seeded application"

    payload = ChatRequest(
        message="What is the current status and stage of my application?",
        application_id=app_record.id,
    )
    resp = copilot_chat(payload=payload, db=db)
    assert app_record.application_no in resp.answer_markdown
    assert resp.context_data is not None
    assert resp.context_data["application_no"] == app_record.application_no

def test_risk_score_factor_contributions_waterfall(db):
    """Verify that priority scorer returns weighted risk score with per-factor contributions."""
    app_record = db.query(Application).first()
    assert app_record is not None, "Need at least one seeded application"

    data = get_single_app_shap(application_id=app_record.id, db=db)
    assert "weighted risk score with per-factor contributions" in data["model_type"].lower()
    assert "weighted risk score with per-factor contributions" in data["scorer_name"].lower()
    assert "factor_contributions" in data
    assert "base_value" in data
    assert data["base_value"] == 0.35 # 35% baseline
    assert len(data["features"]) >= 4

    for feat in data["features"]:
        assert "feature" in feat
        assert "factor_name" in feat
        assert "factor_contribution" in feat
        assert "impact" in feat
        assert feat["impact"] in ["INCREASES_RISK", "REDUCES_RISK"]

def test_next_best_action_embedded_risk_factors(db):
    """Verify that the Next-Best-Action queue items include embedded risk factor contribution breakdowns."""
    data = get_next_best_action_queue(region_code="SWRO", db=db)
    assert "queue" in data
    if len(data["queue"]) > 0:
        first = data["queue"][0]
        assert "factor_contributions" in first or "shap_attribution" in first
        factors = first.get("factor_breakdown") or first["shap_attribution"]
        assert "features" in factors
        assert len(factors["features"]) >= 3
