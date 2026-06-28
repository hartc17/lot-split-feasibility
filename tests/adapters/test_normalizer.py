"""Tests for parcel normalizer — area calculation and field mapping."""
import uuid
from datetime import UTC, datetime

import pytest

from app.adapters.normalizer import compute_area_sqft, normalize
from app.adapters.base import ParcelRecord

# A small square polygon near Kyle TX (roughly 80ft × 125ft equivalent in degrees)
# 0.001° longitude ≈ 295ft, 0.001° latitude ≈ 365ft at lat 30
# Use a smaller box: 0.00028° lon × 0.00018° lat ≈ 82ft × 65ft ≈ 5,330 sqft
_SMALL_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [-97.8800, 29.9900],
        [-97.8797, 29.9900],
        [-97.8797, 29.9902],
        [-97.8800, 29.9902],
        [-97.8800, 29.9900],
    ]],
}

# ~1-acre equivalent at lat 30°:
# 1° lon ≈ 96,488m; 1° lat ≈ 111,195m
# 1 acre = 4,046.86 m²; square side ≈ 63.6m → 0.000659° lon × 0.000572° lat
_ACRE_POLYGON = {
    "type": "Polygon",
    "coordinates": [[
        [-97.88000, 29.99000],
        [-97.87934, 29.99000],
        [-97.87934, 29.99057],
        [-97.88000, 29.99057],
        [-97.88000, 29.99000],
    ]],
}


def test_compute_area_sqft_small_parcel_plausible():
    """A small box near Kyle should be between 1,000 and 50,000 sqft."""
    area = compute_area_sqft(_SMALL_POLYGON)
    assert 1_000 < area < 50_000, f"Expected plausible residential area, got {area:.0f} sqft"


def test_compute_area_sqft_acre_parcel_within_tolerance():
    """1-acre polygon should produce area within 5% of 43,560 sqft."""
    area = compute_area_sqft(_ACRE_POLYGON)
    assert area == pytest.approx(43_560, rel=0.05), (
        f"Expected ~43,560 sqft, got {area:.0f}"
    )


def test_compute_area_sqft_is_positive():
    area = compute_area_sqft(_SMALL_POLYGON)
    assert area > 0


def test_area_acres_consistent_with_sqft():
    """normalize() must compute area_acres = area_sqft / 43_560."""
    rec = _make_record()
    result = normalize(rec, uuid.uuid4(), None)
    assert result["area_acres"] == pytest.approx(result["area_sqft"] / 43_560.0, rel=1e-9)


def test_normalize_returns_all_required_keys():
    rec = _make_record()
    result = normalize(rec, uuid.uuid4(), None)
    required = {
        "jurisdiction_id", "apn", "geometry", "centroid",
        "area_sqft", "area_acres", "zoning_district_id", "zoning_code_raw",
        "existing_structures_count", "raw_assessor_data", "data_fetched_at",
    }
    assert required.issubset(result.keys())


def test_normalize_passes_through_zoning_district_id():
    zd_id = uuid.uuid4()
    rec = _make_record()
    result = normalize(rec, uuid.uuid4(), zd_id)
    assert result["zoning_district_id"] == zd_id


def test_normalize_none_zoning_district_id_allowed():
    rec = _make_record()
    result = normalize(rec, uuid.uuid4(), None)
    assert result["zoning_district_id"] is None


def test_normalize_data_fetched_at_is_recent():
    rec = _make_record()
    result = normalize(rec, uuid.uuid4(), None)
    now = datetime.now(UTC)
    delta = abs((result["data_fetched_at"] - now).total_seconds())
    assert delta < 5, "data_fetched_at should be within 5 seconds of now"


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _make_record(**kwargs) -> ParcelRecord:
    defaults = dict(
        apn="R102610",
        geometry_geojson=_SMALL_POLYGON,
        address_normalized=None,
        zoning_code_raw="R-1-2",
        owner_name=None,
        assessed_land_value=None,
        assessed_improvement_value=None,
        last_sale_price=None,
        last_sale_date=None,
        existing_structures_count=0,
        raw_source_data={"PROP_ID": "R102610"},
    )
    defaults.update(kwargs)
    return ParcelRecord(**defaults)
