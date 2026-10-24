"""
Tests for Group E: Cleanup, Fictional Personas, HQ Bureau Scope, and Hash Chain Verification
16. Fictional names only for personas; remove local absolute file paths from docs.
17. Treat HQ as Bureau scope, not a region. Rename "Merkle-style" to "hash chain".
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.database import SessionLocal
from app.models import User, Region
from app.routers.auth_routes import get_demo_personas

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_fictional_names_only(db):
    """Clause 16: Ensure no real active council members are in personas or seeded users."""
    personas_data = get_demo_personas(db)
    personas = personas_data["personas"]

    # Assert no real official names
    for p in personas:
        assert "Rajive Kumar" not in p["name"], f"Real name found in persona: {p['name']}"

    db_users = db.query(User).all()
    for u in db_users:
        assert "Rajive Kumar" not in u.full_name, f"Real name found in DB: {u.full_name}"

    # Verify Member Secretary is fictional Dr. Arvind Ramanathan
    ms = db.query(User).filter(User.role == "SUPER_ADMIN").first()
    assert ms is not None
    assert "Dr. Arvind Ramanathan" in ms.full_name

def test_hq_treated_as_bureau_scope_not_region(db):
    """
    Clause 17: Treat HQ as Bureau scope, not a geographical region.
    Regions table must contain only geographical regional offices (SWRO, SRO, etc.)
    HQ users have region_id = None (Bureau / Council scope).
    """
    # 7 geographical regional offices
    regions = db.query(Region).all()
    reg_codes = [r.code for r in regions]
    assert "SWRO" in reg_codes
    assert "SRO" in reg_codes
    assert "WRO" in reg_codes
    assert "NRO" in reg_codes
    assert "ERO" in reg_codes
    assert "CRO" in reg_codes
    assert "NWRO" in reg_codes

    # HQ users must have region_id = None (Bureau Scope)
    hq_users = db.query(User).filter(User.role.in_(["BUREAU_HEAD", "BUREAU_OFFICER", "SUPER_ADMIN", "SAC_SHC_MEMBER"])).all()
    assert len(hq_users) >= 3
    for u in hq_users:
        assert u.region_id is None, f"HQ user {u.email} should have region_id=None representing Bureau scope"

def test_no_local_absolute_paths_in_docs():
    """Clause 16: Assert no local absolute Windows drive paths exist in documentation."""
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    docs_to_check = [
        os.path.join(base_dir, "README.md"),
        os.path.join(base_dir, "aicte_system_comprehensive_architecture_guide.md"),
    ]

    for doc_path in docs_to_check:
        if os.path.exists(doc_path):
            with open(doc_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "c:\\users" not in content.lower(), f"Local path found in {doc_path}"
                assert "onedrive" not in content.lower(), f"OneDrive path found in {doc_path}"
                assert "merkle-style" not in content.lower(), f"Merkle-style found in {doc_path}"

def test_tests_run_on_isolated_temp_database():
    """TASK 0a: Verify that test suite runs on an isolated temporary database, NEVER touching the dev database."""
    from app.config import settings
    assert "aicte_test_isolated" in settings.DATABASE_URL
    assert not settings.DATABASE_URL.endswith("aicte_dev.db")
    assert "aicte_pytest_isolated_" in settings.DATABASE_URL

