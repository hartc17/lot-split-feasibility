"""
Verify model classes are importable and have required columns.
No DB connection required.
"""

from sqlalchemy import inspect as sa_inspect


def test_jurisdiction_model_importable():
    from app.models.jurisdiction import Jurisdiction

    cols = {c.key for c in sa_inspect(Jurisdiction).columns}
    required = {"id", "name", "state", "fips_code", "minor_subdivision_threshold"}
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_zoning_district_model_importable():
    from app.models.zoning_district import ZoningDistrict

    cols = {c.key for c in sa_inspect(ZoningDistrict).columns}
    required = {
        "id",
        "jurisdiction_id",
        "code",
        "min_lot_area_sqft",
        "min_lot_width_ft",
        "setback_front_ft",
        "setback_side_ft",
        "setback_rear_ft",
        "allows_flag_lots",
        "last_verified_date",
        "source_ordinance_section",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_parcel_model_importable():
    from app.models.parcel import Parcel

    cols = {c.key for c in sa_inspect(Parcel).columns}
    required = {
        "id",
        "jurisdiction_id",
        "apn",
        "geometry",
        "area_sqft",
        "zoning_district_id",
        "zoning_code_raw",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_feasibility_report_model_importable():
    from app.models.feasibility_report import FeasibilityReport

    cols = {c.key for c in sa_inspect(FeasibilityReport).columns}
    required = {
        "id",
        "parcel_id",
        "status",
        "overall_score",
        "recommendation",
        "risk_flags",
        "requested_at",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"
