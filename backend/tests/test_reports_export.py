"""
Unit tests for Reports Export (PDF/Excel/CSV) and Impact Metrics.
Validates:
1. Default-deny on unauthenticated export requests.
2. Formatted PDF generation with PDF-1.4 headers and content.
3. Genuine Excel (.xlsx) generation with PK zip magic bytes and openpyxl validity.
4. Operational impact metrics including reminders, escalations, follow-ups avoided, and officer hours saved with explicit assumptions.
5. Tamper-evident audit ledger logging upon export.
"""

import os
import sys
import io
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
import openpyxl
from tests.http_client import AppTestClient
from app.auth import create_access_token
from app.database import SessionLocal
from app.models import AuditTrail, User

client = AppTestClient()

@pytest.fixture
def super_admin_token():
    return create_access_token({"sub": "usr-member-sec", "role": "SUPER_ADMIN"})

@pytest.fixture
def regional_officer_token():
    return create_access_token({"sub": "usr-ro-01", "role": "REGIONAL_OFFICER", "region_id": "reg-swro"})

def test_unauthenticated_export_denied():
    """Negative test: Calling export without authentication returns 401."""
    resp = client.get("/api/v1/reports/export")
    assert resp.status_code == 401

def test_export_pdf_format(super_admin_token):
    """Verify official report export in PDF format."""
    resp = client.get(
        "/api/v1/reports/export?report_type=APPLICATIONS_PIPELINE&format=pdf",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 200
    assert "application/pdf" in resp.headers.get("content-type", "")
    assert "attachment;" in resp.headers.get("content-disposition", "")
    assert resp.content.startswith(b"%PDF-1.4")

def test_export_excel_format(super_admin_token):
    """Verify report export produces a real .xlsx OpenXML workbook."""
    resp = client.get(
        "/api/v1/reports/export?report_type=APPLICATIONS_PIPELINE&format=excel",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in resp.headers.get("content-type", "")
    assert "attachment;" in resp.headers.get("content-disposition", "")
    assert ".xlsx" in resp.headers.get("content-disposition", "")
    # Standard ZIP / OpenXML magic bytes
    assert resp.content.startswith(b"PK\x03\x04"), "Excel file must start with PK zip header"
    # Verify openpyxl can parse the returned workbook without errors
    wb = openpyxl.load_workbook(io.BytesIO(resp.content))
    assert len(wb.sheetnames) > 0
    ws = wb.active
    assert ws.cell(row=1, column=1).value is not None

def test_sla_breach_report_export(super_admin_token):
    """Verify SLA breach audit report export."""
    resp = client.get(
        "/api/v1/reports/export?report_type=SLA_BREACH_AUDIT&format=csv",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment;" in resp.headers.get("content-disposition", "")

def test_impact_metrics_endpoint(super_admin_token):
    """Verify calculation and output of the operational & academic risk metrics endpoint."""
    resp = client.get(
        "/api/v1/reports/impact-metrics",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "SUCCESS"
    metrics = data["metrics"]
    assert "seats_at_risk" in metrics
    assert "institutions_with_critical_deficits" in metrics
    assert "faculty_cadre_deficits" in metrics
    assert "tuition_revenue_at_risk_inr_cr" in metrics
    # Item 5 requirements:
    assert metrics["reminders_sent_automatically"] == 42
    assert metrics["escalations_fired_on_time"] == 18
    assert metrics["followups_avoided"] == 64
    assert metrics["officer_hours_saved"] == 128
    # Assumptions shown:
    assumptions = data["assumptions"]
    assert "officer_hours_saved_note" in assumptions
    assert "seats_per_institution" in assumptions
    assert "annual_tuition_per_seat" in assumptions

def test_export_audit_trail_logging(super_admin_token):
    """Verify that exporting any report records a non-repudiable audit ledger entry."""
    db = SessionLocal()
    initial_count = db.query(AuditTrail).filter(AuditTrail.action_type == "REPORT_EXPORTED").count()

    resp = client.get(
        "/api/v1/reports/export?report_type=INSTITUTIONAL_COMPLIANCE&format=csv",
        headers={"Authorization": f"Bearer {super_admin_token}"},
    )
    assert resp.status_code == 200

    new_count = db.query(AuditTrail).filter(AuditTrail.action_type == "REPORT_EXPORTED").count()
    assert new_count > initial_count
    db.close()

