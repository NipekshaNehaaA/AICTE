"""
FastAPI Main Application Entrypoint for AICTE Approval & Compliance System (SIH26262).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import init_db
from app.routers import (
    intake_workflow,
    alerts_escalation,
    compliance_registry,
    evc_hub,
    signature_features,
    audit_trail,
    copilot_chat,
    auth_routes,
    demo_scenario,
    reports_analytics,
    adapters,
)
from app.rules_engine import APH_CLAUSE_CATALOG, APH_PIPELINE_MAP

# Initialize FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Integrated AICTE Approval Workflow Automation, Compliance Monitoring and Alert Management System (PS SIH26262)",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS Middleware for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from app.scoped_dal import SecurityScopeError, SoDViolationError, RequestContext
from app.auth import get_request_context
from app.database import get_db
from sqlalchemy.orm import Session
from typing import Optional

# Include Routers
app.include_router(auth_routes.router)
app.include_router(intake_workflow.router)
app.include_router(alerts_escalation.router)
app.include_router(compliance_registry.router)
app.include_router(evc_hub.router)
app.include_router(signature_features.router)
app.include_router(audit_trail.router)
app.include_router(copilot_chat.router)
app.include_router(demo_scenario.router)
app.include_router(reports_analytics.router)
app.include_router(adapters.router)

@app.exception_handler(SecurityScopeError)
def security_scope_error_handler(request, exc):
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.exception_handler(SoDViolationError)
def sod_violation_error_handler(request, exc):
    return JSONResponse(status_code=403, content={"detail": str(exc)})

@app.get("/api/v1/documents/{document_id}/download")
def download_document_root_alias(
    document_id: str,
    version: Optional[int] = None,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    from app.routers.compliance_registry import download_regulatory_document
    return download_regulatory_document(document_id, version, ctx, db)

@app.on_event("startup")
def on_startup():
    if not settings.DEMO_MODE:
        jwt_secret = os.getenv("JWT_SECRET") or os.getenv("JWT_SECRET_KEY")
        weak_placeholders = {
            "secret",
            "changeme",
            "password",
            "12345678",
            "aicte-cryptographic-signing-key-secret-2026",
            "your-secure-at-least-32-chars-long-jwt-secret-key-here",
        }
        if not jwt_secret:
            raise RuntimeError("JWT_SECRET environment variable must be set when DEMO_MODE is false (production mode).")
        if len(jwt_secret.strip()) < 32 or jwt_secret.strip() in weak_placeholders:
            raise RuntimeError("JWT_SECRET environment variable is too weak (< 32 characters or default placeholder) when DEMO_MODE is false (production mode).")
    init_db()
    
    # Idempotent auto-seed on startup if tables/data are missing
    try:
        from app.database import SessionLocal
        from app.models import Institution
        db = SessionLocal()
        try:
            if db.query(Institution).count() == 0:
                from app.seed import seed_database
                seed_database()
        finally:
            db.close()
    except Exception as e:
        try:
            from app.seed import seed_database
            seed_database()
        except Exception as seed_err:
            print(f"Startup database seeding notice: {seed_err}")

    # Start APScheduler on real clock with catch-up evaluation
    try:
        import sys
        if os.getenv("TESTING", "false").lower() != "true" and "pytest" not in sys.modules:
            from app.scheduler import regulatory_scheduler
            regulatory_scheduler.start_scheduler(interval_minutes=60)
    except Exception as sched_err:
        print(f"Scheduler startup notice: {sched_err}")

@app.on_event("shutdown")
def on_shutdown():
    try:
        from app.scheduler import regulatory_scheduler
        regulatory_scheduler.shutdown_scheduler()
    except Exception:
        pass

@app.get("/health")
@app.get("/api/v1/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "database": "SQLite (Dev Scoped DAL) / Postgres RLS ready",
        "authority_matrix_active": True,
        "demo_mode": settings.DEMO_MODE,
    }

@app.get("/api/v1/system/mode")
def get_system_mode():
    """Returns current system execution mode (EVALUATOR_MODE / DEMO_MODE flag, environment)."""
    return {
        "demo_mode": settings.DEMO_MODE,
        "evaluator_mode": settings.EVALUATOR_MODE,
        "environment": settings.ENV,
        "version": settings.VERSION,
    }

@app.post("/api/v1/system/evaluator-mode")
def set_evaluator_mode(payload: dict):
    """Admin toggle for Evaluator Mode at runtime."""
    enabled = bool(payload.get("enabled", False))
    settings.EVALUATOR_MODE = enabled
    settings.DEMO_MODE = enabled
    return {
        "status": "SUCCESS",
        "evaluator_mode": settings.EVALUATOR_MODE,
        "demo_mode": settings.DEMO_MODE,
        "message": f"Evaluator Mode {'activated' if enabled else 'deactivated'} successfully.",
    }

@app.get("/api/v1/rules/aph-catalog")
def get_aph_catalog():
    """Returns the official compiled APH 2024-27 clause catalog and pipelines."""
    return {
        "aph_version": "2024-25 to 2026-27",
        "pipelines": APH_PIPELINE_MAP,
        "clauses": APH_CLAUSE_CATALOG,
    }

@app.get("/api/v1/rules/provenance/{key}")
def get_clause_provenance(key: str):
    """Returns exact APH clause, page, and description for a given rule key."""
    from app.rules_engine import APHRulesEngine
    return APHRulesEngine.get_clause_provenance(key)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
