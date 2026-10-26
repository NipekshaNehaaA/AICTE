"""
FastAPI Main Application Entrypoint for AICTE Approval & Compliance System (SIH26262).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Depends, HTTPException, status, Request
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

@app.get("/api/v1/documents/{document_id}/preview")
def preview_document_root_alias(
    document_id: str,
    version: Optional[int] = None,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    from app.routers.compliance_registry import preview_regulatory_document
    return preview_regulatory_document(document_id, version, ctx, db)

@app.get("/api/v1/documents/{document_id}/access-control")
def access_control_document_root_alias(
    document_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
):
    from app.routers.compliance_registry import get_document_access_control
    return get_document_access_control(document_id, ctx, db)

@app.on_event("startup")
def on_startup():
    if settings.ENV.lower() == "production" and (settings.DEMO_MODE or settings.EVALUATOR_MODE):
        raise RuntimeError("Fatal Security Violation: Startup refused. DEMO_MODE or EVALUATOR_MODE cannot be enabled when ENV=production.")
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
    init_db("live")
    init_db("sandbox")
    
    # Ensure storage directories exist
    os.makedirs(os.path.join(settings.STORAGE_LOCAL_DIR, "live"), exist_ok=True)
    os.makedirs(os.path.join(settings.STORAGE_LOCAL_DIR, "sandbox"), exist_ok=True)

    # Idempotent auto-seed on startup for both Live and Sandbox
    from app.database import get_session_maker
    from app.models import Region, User, Institution
    from app.auth import verify_password, hash_password
    import logging
    logger = logging.getLogger("uvicorn.error")

    # 1. Seed Live workspace if needed
    live_sm = get_session_maker("live")
    db_live = live_sm()
    try:
        if db_live.query(Region).count() == 0 or db_live.query(User).count() == 0:
            from app.seed import seed_database
            seed_database("live")
    except Exception as e:
        print(f"Startup live database seeding notice: {e}")
    finally:
        db_live.close()

    # 2. Seed Sandbox workspace if needed
    sandbox_sm = get_session_maker("sandbox")
    db_sandbox = sandbox_sm()
    try:
        if db_sandbox.query(Region).count() == 0 or db_sandbox.query(Institution).count() == 0:
            from app.seed import seed_database
            seed_database("sandbox")
    except Exception as e:
        print(f"Startup sandbox database seeding notice: {e}")
    finally:
        db_sandbox.close()

    # DEFECT 4: Live database hygiene and default password self-check
    if settings.ENV.lower() == "production":
        db = live_sm()
        try:
            # 0. Ensure production administrator account exists from configuration
            admin_email = (settings.ADMIN_EMAIL or "admin@aicte-india.org").strip().lower()
            admin_pass = settings.ADMIN_INITIAL_PASSWORD or "AdminInitialPass@2026"
            admin_user = db.query(User).filter(User.email == admin_email).first()
            if not admin_user:
                admin_user = User(
                    email=admin_email,
                    password_hash=hash_password(admin_pass),
                    full_name="AICTE System Administrator",
                    role="SUPER_ADMIN",
                    region_id=None,
                    mfa_enabled=True,
                    must_change_password=True,
                    is_active=True,
                )
                db.add(admin_user)
                db.commit()

            # 1. Detect and disable demo accounts in live DB if password unchanged
            all_users = db.query(User).all()
            for u in all_users:
                is_demo = (
                    u.email.endswith("@fictional-aicte.edu.in")
                    or u.email in {
                        "member.secretary@aicte-india.org",
                        "bureau.head@aicte-india.org",
                        "approval.bureau@aicte-india.org",
                        "sac.appellate@aicte-india.org",
                        "auditor.compliance@aicte-india.org",
                    }
                    or u.email.startswith("ro.")
                    or u.email.startswith("rd.")
                    or u.email.startswith("expert.")
                    or u.email.startswith("scrutiny.")
                    or (u.institution and getattr(u.institution, "is_synthetic", False))
                )
                if is_demo and u.is_active:
                    if verify_password("DemoPassword@123", u.password_hash):
                        logger.warning(
                            "CRITICAL SECURITY WARNING: Demo account '%s' detected in live database with default credentials. Disabling account (is_active=False).",
                            u.email,
                        )
                        u.is_active = False
            db.commit()

            # 2. Startup self-check: Fail boot if ANY active user matches a known default password hash
            active_users = db.query(User).filter(User.is_active == True).all()
            for u in active_users:
                if verify_password("DemoPassword@123", u.password_hash):
                    raise RuntimeError(
                        f"Production Security Boot Refused: Active user '{u.email}' matches a known default password hash ('DemoPassword@123'). All active production accounts must use unique passwords."
                    )
        finally:
            db.close()

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
def health_check(request: Request):
    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENV,
        "workspace": ws,
        "database": f"SQLite Dual-Engine ({ws}) / Postgres RLS ready",
        "authority_matrix_active": True,
        "demo_mode": (ws == "sandbox"),
    }

@app.get("/api/v1/system/mode")
@app.get("/system/mode")
def get_system_mode(request: Request):
    """Returns current system execution mode (strictly evaluator_mode boolean only)."""
    from app.workspace import resolve_workspace
    ws = resolve_workspace(request)
    return {
        "evaluator_mode": (ws == "sandbox"),
    }

@app.post("/api/v1/system/evaluator-mode")
@app.post("/system/evaluator-mode")
def set_evaluator_mode():
    """
    Runtime mode mutation is permanently removed.
    Workspaces ('live' and 'sandbox') are selected per-request safely without server-wide flag mutations.
    """
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not Found: Runtime mode mutation is permanently disabled.")

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
