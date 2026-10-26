"""
Database engine and session management with dual-workspace isolation (Live vs Sandbox).
- Live workspace: aicte_live.db (strict production schema, real accounts only)
- Sandbox workspace: aicte_sandbox.db (demonstration schema, synthetic institutions, demo personas)
"""

import os
from typing import Dict, Optional
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from fastapi import Request
from app.config import settings
from app.models import Base
from app.workspace import resolve_workspace, current_workspace_var

_root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def _get_database_url_for_workspace(ws: str) -> str:
    clean_ws = (ws or "live").strip().lower()
    custom_url = os.getenv(f"DATABASE_URL_{clean_ws.upper()}")
    if custom_url:
        return custom_url

    base_url = settings.DATABASE_URL
    if base_url.startswith("sqlite"):
        db_filename = f"aicte_{clean_ws}.db"
        return f"sqlite:///{os.path.join(_root_dir, db_filename)}"
    else:
        # PostgreSQL or MySQL: Append workspace suffix to db name if not provided
        if "/" in base_url:
            parts = base_url.rsplit("/", 1)
            return f"{parts[0]}/{parts[1]}_{clean_ws}"
        return f"{base_url}_{clean_ws}"

_engines: Dict[str, Engine] = {}
_session_makers: Dict[str, sessionmaker] = {}

def get_engine(workspace: str = "live") -> Engine:
    ws = (workspace or "live").strip().lower()
    if ws not in _engines:
        db_url = _get_database_url_for_workspace(ws)
        is_sqlite = db_url.startswith("sqlite")
        connect_args = {"check_same_thread": False, "timeout": 30} if is_sqlite else {}
        
        eng = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        if is_sqlite:
            @event.listens_for(eng, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.close()
        _engines[ws] = eng
    return _engines[ws]

def get_session_maker(workspace: str = "live") -> sessionmaker:
    ws = (workspace or "live").strip().lower()
    if ws not in _session_makers:
        eng = get_engine(ws)
        _session_makers[ws] = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return _session_makers[ws]

# Default exports for backward compatibility
engine = get_engine("live")
SessionLocal = get_session_maker("live")

def init_db(workspace: Optional[str] = None):
    """Initializes database tables for a specific workspace or both live and sandbox."""
    workspaces = [workspace] if workspace else ["live", "sandbox"]
    for ws in workspaces:
        eng = get_engine(ws)
        Base.metadata.create_all(bind=eng)
        if eng.url.drivername.startswith("sqlite"):
            try:
                with eng.connect() as conn:
                    # users table columns
                    res = conn.execute(text("PRAGMA table_info(users)"))
                    cols = {row[1] for row in res.fetchall()}
                    if "verification_token_expires_at" not in cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN verification_token_expires_at DATETIME"))
                    if "token_version" not in cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN token_version INTEGER DEFAULT 0"))
                    if "quiet_hours_start" not in cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN quiet_hours_start INTEGER DEFAULT 22"))
                    if "quiet_hours_end" not in cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN quiet_hours_end INTEGER DEFAULT 6"))
                    if "quiet_hours_enabled" not in cols:
                        conn.execute(text("ALTER TABLE users ADD COLUMN quiet_hours_enabled BOOLEAN DEFAULT 1"))

                    # institutional_documents table columns
                    res_docs = conn.execute(text("PRAGMA table_info(institutional_documents)"))
                    doc_cols = {row[1] for row in res_docs.fetchall()}
                    if "application_id" not in doc_cols:
                        conn.execute(text("ALTER TABLE institutional_documents ADD COLUMN application_id VARCHAR(36)"))

                    # application_stages table columns
                    res_stages = conn.execute(text("PRAGMA table_info(application_stages)"))
                    stage_cols = {row[1] for row in res_stages.fetchall()}
                    if "assigned_user_id" not in stage_cols:
                        conn.execute(text("ALTER TABLE application_stages ADD COLUMN assigned_user_id VARCHAR(36)"))

                    conn.commit()
            except Exception:
                pass


def get_db(request: Request = None):
    """
    FastAPI dependency yielding a workspace-scoped database session.
    Derives workspace dynamically from JWT claim or X-Workspace header.
    """
    ws = resolve_workspace(request)
    session_factory = get_session_maker(ws)
    db: Session = session_factory()
    try:
        yield db
    finally:
        db.close()
