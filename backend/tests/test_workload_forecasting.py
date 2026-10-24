"""
Unit and integration tests for Deterministic Workload-Based Breach Forecasting Model.
Verifies:
1. Higher load / reduced staffing produces later projected completion date.
2. Gazetted holidays and weekends properly advance working-day calendar projection.
3. Fixed seed produces identical, 100% deterministic Monte-Carlo probability bands (P10, P50, P90).
4. API endpoint get_single_app_forecast returns explainable queueing forecast.
5. API endpoint run_what_if_simulation computes impacts from workload engine.
"""

from datetime import datetime, timedelta, date
import pytest
from app.database import SessionLocal
from app.models import Application, HolidayCalendar
from app.scoped_dal import RequestContext
from app.workload_forecasting import WorkloadForecastEngine, workload_engine
from app.routers.signature_features import (
    get_single_app_forecast,
    run_what_if_simulation,
    WhatIfRequest,
)

@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()

def test_working_day_calculation_with_holidays():
    """Verify is_working_day and add_working_days correctly skip weekends and gazetted holidays."""
    # 2026-01-23 is Friday.
    # 2026-01-24 is Saturday (weekend).
    # 2026-01-25 is Sunday (weekend).
    # 2026-01-26 is Monday (Republic Day holiday).
    # 2026-01-27 is Tuesday (working day).
    start = date(2026, 1, 23)
    republic_day = date(2026, 1, 26)
    holidays = [republic_day]

    assert WorkloadForecastEngine.is_working_day(start, holidays) is True
    assert WorkloadForecastEngine.is_working_day(date(2026, 1, 24), holidays) is False
    assert WorkloadForecastEngine.is_working_day(date(2026, 1, 25), holidays) is False
    assert WorkloadForecastEngine.is_working_day(republic_day, holidays) is False
    assert WorkloadForecastEngine.is_working_day(date(2026, 1, 27), holidays) is True

    # Advancing 1 working day from Friday Jan 23 should land on Tuesday Jan 27!
    end_date, calendar_days = WorkloadForecastEngine.add_working_days(start, 1, holidays)
    assert end_date == date(2026, 1, 27)
    assert calendar_days == 4 # Sat, Sun, Mon, Tue

def test_holiday_shifts_projected_completion_date(db):
    """Adding a holiday to HolidayCalendar shifts the expected completion date further out."""
    now = datetime(2026, 8, 10, 10, 0, 0) # Monday
    app = db.query(Application).first()
    assert app is not None

    # Baseline forecast with existing holidays
    f1 = workload_engine.compute_workload_forecast(app, db, current_time=now)

    # Insert a gazetted holiday during the projection window
    h_date = now.date() + timedelta(days=2) # Wednesday
    # Remove if existing
    db.query(HolidayCalendar).filter(HolidayCalendar.holiday_date == h_date).delete()
    new_h = HolidayCalendar(name="Festival Holiday", holiday_date=h_date, is_national=True)
    db.add(new_h)
    db.commit()

    f2 = workload_engine.compute_workload_forecast(app, db, current_time=now)

    # Completion date with holiday must be >= completion date without holiday
    d1 = datetime.strptime(f1["projected_completion_date"], "%Y-%m-%d").date()
    d2 = datetime.strptime(f2["projected_completion_date"], "%Y-%m-%d").date()
    assert d2 >= d1

def test_reduced_staffing_increases_delay(db):
    """Reduced staffing capacity results in a later projected completion date."""
    app = db.query(Application).first()
    assert app is not None
    now = datetime(2026, 5, 4, 10, 0, 0)

    # Full staffing (1.0)
    forecast_full = workload_engine.compute_workload_forecast(
        app, db, current_time=now, staffing_efficiency_ratio=1.0
    )
    # 50% staffing (0.5)
    forecast_half = workload_engine.compute_workload_forecast(
        app, db, current_time=now, staffing_efficiency_ratio=0.5
    )

    d_full = datetime.strptime(forecast_full["projected_completion_date"], "%Y-%m-%d").date()
    d_half = datetime.strptime(forecast_half["projected_completion_date"], "%Y-%m-%d").date()

    assert d_half > d_full
    assert forecast_half["breach_probability"] >= forecast_full["breach_probability"]

def test_deterministic_reproducibility_with_fixed_seed(db):
    """Evaluating the workload model twice for the same app produces identical results."""
    app = db.query(Application).first()
    assert app is not None
    now = datetime(2026, 6, 1, 9, 0, 0)

    res1 = workload_engine.compute_workload_forecast(app, db, current_time=now, fixed_seed=42)
    res2 = workload_engine.compute_workload_forecast(app, db, current_time=now, fixed_seed=42)

    assert res1["projected_completion_date"] == res2["projected_completion_date"]
    assert res1["breach_probability"] == res2["breach_probability"]
    assert res1["probability_band"] == res2["probability_band"]
    assert res1["probability_band"]["p10_optimistic_date"] <= res1["probability_band"]["p50_median_date"]
    assert res1["probability_band"]["p50_median_date"] <= res1["probability_band"]["p90_conservative_date"]

def test_api_single_application_forecast(db):
    """Router function get_single_app_forecast returns workload queueing model."""
    app = db.query(Application).first()
    assert app is not None

    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER", region_id=app.region_id)
    data = get_single_app_forecast(application_id=app.id, ctx=ctx, db=db)

    assert data["model_type"] == "forecast from workload model"
    assert "projected_completion_date" in data
    assert "probability_band" in data
    assert "p10_optimistic_date" in data["probability_band"]
    assert "p50_median_date" in data["probability_band"]
    assert "p90_conservative_date" in data["probability_band"]
    assert len(data["assumptions"]) > 0

def test_api_what_if_simulation_workload_model(db):
    """Router function run_what_if_simulation returns model_label 'forecast from workload model'."""
    ctx = RequestContext(user_id="usr-ro-1", role="REGIONAL_OFFICER")
    req = WhatIfRequest(inspector_shortage_percent=30, staffing_level_percent=60)
    data = run_what_if_simulation(payload=req, ctx=ctx, db=db)

    assert data["model_label"] == "forecast from workload model"
    assert "simulation_parameters" in data
    assert "impact_projections" in data
    assert "predicted_sla_breaches" in data["impact_projections"]
    assert "assumptions" in data

def test_different_cases_get_different_projections(db):
    """
    Validates Task 0b requirement:
    Different cases with different stages, SLA deadlines, or queue positions
    must receive distinct P10/P50/P90 projections rather than duplicate bucketed dates.
    """
    now = datetime(2026, 9, 1, 9, 0, 0)
    apps = db.query(Application).filter(Application.status.in_(["IN_PROGRESS", "ESCALATED"])).limit(5).all()
    assert len(apps) >= 2, "Need at least 2 applications for differentiation test"

    app1 = apps[0]
    app2 = apps[1]

    # Ensure app1 and app2 have different attributes (stage and deadline)
    app1.current_stage = "SCRUTINY"
    app1.sla_deadline = now + timedelta(days=12)
    app1.submitted_at = now - timedelta(days=5)

    app2.current_stage = "EVC_COMMITTEE"
    app2.sla_deadline = now + timedelta(days=28)
    app2.submitted_at = now - timedelta(days=1)
    db.commit()

    f1 = workload_engine.compute_workload_forecast(app1, db, current_time=now)
    f2 = workload_engine.compute_workload_forecast(app2, db, current_time=now)

    # Different stages & queue positions must produce different completion dates and probability bands
    assert f1["projected_completion_date"] != f2["projected_completion_date"]
    assert (
        f1["probability_band"]["p10_optimistic_date"] != f2["probability_band"]["p10_optimistic_date"] or
        f1["probability_band"]["p50_median_date"] != f2["probability_band"]["p50_median_date"] or
        f1["probability_band"]["p90_conservative_date"] != f2["probability_band"]["p90_conservative_date"]
    )
