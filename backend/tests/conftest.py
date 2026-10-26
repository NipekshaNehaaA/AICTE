"""
Pytest configuration and session fixtures for AICTE backend test suite.
Ensures tests run on an isolated temporary database, NEVER touching the development DB.
"""

import os
import sys
import tempfile
import atexit
import shutil

# 1. Setup isolated temporary test database and storage directory before importing config or database
_test_db_dir = tempfile.mkdtemp(prefix="aicte_pytest_isolated_")
_test_db_file = os.path.join(_test_db_dir, "aicte_test_isolated.db")
os.environ["DATABASE_URL"] = f"sqlite:///{_test_db_file}"

_test_storage_dir = tempfile.mkdtemp(prefix="aicte_pytest_storage_")
os.environ["STORAGE_LOCAL_DIR"] = _test_storage_dir

# Ensure test suite runs with demo mode active by default for standard integration tests.
# Specific negative/isolation tests in test_jwt_and_demo_mode.py toggle DEMO_MODE explicitly.
os.environ["DEMO_MODE"] = "true"
os.environ["JWT_SECRET"] = "aicte-test-suite-cryptographic-signing-key-secret-2026"

from app.config import settings
settings.DATABASE_URL = f"sqlite:///{_test_db_file}"
settings.STORAGE_LOCAL_DIR = _test_storage_dir
settings.DEMO_MODE = True
settings.EVALUATOR_MODE = True
settings.EVALUATOR_ALLOW_TOGGLE = True
settings.SECRET_KEY = "aicte-test-suite-cryptographic-signing-key-secret-2026"

from app.storage import storage_service
if hasattr(storage_service, "base_dir"):
    storage_service.base_dir = _test_storage_dir

# 2. Bind SQLAlchemy engine to this isolated temporary database
from app.database import engine, init_db, SessionLocal
from app.models import Institution
init_db()

_test_db = SessionLocal()
try:
    if _test_db.query(Institution).count() == 0:
        from app.seed import seed_database
        seed_database()
except Exception:
    try:
        from app.seed import seed_database
        seed_database()
    except Exception:
        pass
finally:
    _test_db.close()

def _cleanup_isolated_test_db():
    try:
        engine.dispose()
        shutil.rmtree(_test_db_dir, ignore_errors=True)
        shutil.rmtree(_test_storage_dir, ignore_errors=True)
    except Exception:
        pass

atexit.register(_cleanup_isolated_test_db)
