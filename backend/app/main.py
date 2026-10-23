"""
FastAPI Main Application Entrypoint for AICTE Approval & Compliance System (SIH26262).
"""

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI
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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_routes.router)
app.include_router(intake_workflow.router)
app.include_router(alerts_escalation.router)
app.include_router(compliance_registry.router)
app.include_router(evc_hub.router)
app.include_router(signature_features.router)
app.include_router(audit_trail.router)
app.include_router(copilot_chat.router)

@app.on_event("startup")
def on_startup():
    init_db()

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
