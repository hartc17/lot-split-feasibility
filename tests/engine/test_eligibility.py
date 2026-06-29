import pytest
from tests.fixtures.parcels import (
    fixture_1_clean_split,
    fixture_2_area_shortfall,
    fixture_5_structure_conflict,
    fixture_7_multi_district,
)
from app.engine.eligibility import check_eligibility
from app.engine.types import RiskCategory


def test_clean_parcel_passes_eligibility():
    parcel, zoning, structures, _ = fixture_1_clean_split()
    flags = check_eligibility(parcel, zoning, structures)
    assert flags == [], f"Expected no flags, got: {flags}"


def test_area_shortfall_produces_flag():
    parcel, zoning, structures, _ = fixture_2_area_shortfall()
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.ZONING_AREA_SHORTFALL in categories


def test_area_shortfall_message_contains_actual_numbers():
    parcel, zoning, structures, _ = fixture_2_area_shortfall()
    flags = check_eligibility(parcel, zoning, structures)
    shortfall_flag = next(f for f in flags if f.category == RiskCategory.ZONING_AREA_SHORTFALL)
    # Message must say what the area IS and what's REQUIRED
    assert "9,000" in shortfall_flag.message or "9000" in shortfall_flag.message
    assert "10,000" in shortfall_flag.message or "10000" in shortfall_flag.message


def test_multi_district_produces_flag():
    parcel, zoning, structures, _ = fixture_7_multi_district()
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.MULTI_DISTRICT_PARCEL in categories



def test_structure_conflict_produces_flag():
    parcel, zoning, structures, _ = fixture_5_structure_conflict()
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.EXISTING_STRUCTURE_CONFLICT in categories
