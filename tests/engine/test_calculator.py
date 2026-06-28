"""
Integration tests for calculate_subdivision_scenarios against all 7 spec fixtures.
No DB, no network. Pure function with synthetic inputs.
"""
import pytest
from app.engine.calculator import calculate_subdivision_scenarios
from app.engine.types import LotLayoutType, RiskCategory, SubdivisionReviewTier
from tests.fixtures.parcels import (
    fixture_1_clean_split,
    fixture_2_area_shortfall,
    fixture_3_flag_lot_allowed,
    fixture_4_flag_lot_disallowed,
    fixture_5_structure_conflict,
    fixture_6_flood_zone,
    fixture_7_multi_district,
)


# ---------------------------------------------------------------------------
# Fixture 1: Clean rectangular 2x parcel — must produce valid SIMPLE_HALVE
# ---------------------------------------------------------------------------

def test_fixture1_produces_scenarios():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert len(result.scenarios) >= 1
    assert result.data_gap is False
    assert result.disqualifying_flags == []


def test_fixture1_primary_scenario_is_simple_halve():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    primary = result.scenarios[0]
    assert primary.lot_layout_type == LotLayoutType.SIMPLE_HALVE
    assert primary.num_resulting_lots == 2


def test_fixture1_both_lots_valid():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    for lot in result.scenarios[0].resulting_lots:
        assert lot.meets_min_lot_size is True
        assert lot.meets_min_frontage is True
        assert lot.has_buildable_envelope is True
        assert lot.has_direct_frontage is True


def test_fixture1_no_variance_required():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios[0].requires_variance is False


# ---------------------------------------------------------------------------
# Fixture 2: 1.8x minimum area — must produce 0 scenarios with clear explanation
# ---------------------------------------------------------------------------

def test_fixture2_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture2_has_area_shortfall_flag():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_categories = [f.category for f in result.disqualifying_flags]
    assert RiskCategory.ZONING_AREA_SHORTFALL in flag_categories


def test_fixture2_flag_message_contains_both_areas():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag = next(f for f in result.disqualifying_flags
                if f.category == RiskCategory.ZONING_AREA_SHORTFALL)
    assert "9,000" in flag.message or "9000" in flag.message
    assert "10,000" in flag.message or "10000" in flag.message


def test_fixture2_data_gap_is_false():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.data_gap is False


# ---------------------------------------------------------------------------
# Fixture 3: Deep narrow parcel, flag lots ALLOWED — must produce FLAG_LOT scenario
# ---------------------------------------------------------------------------

def test_fixture3_produces_flag_lot_scenario():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert len(result.scenarios) >= 1
    assert any(s.lot_layout_type == LotLayoutType.FLAG_LOT for s in result.scenarios)


def test_fixture3_flag_lot_front_has_frontage():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_scenario = next(s for s in result.scenarios if s.lot_layout_type == LotLayoutType.FLAG_LOT)
    front = flag_scenario.resulting_lots[0]
    assert front.has_direct_frontage is True
    assert front.meets_min_lot_size is True


def test_fixture3_flag_lot_rear_has_no_direct_frontage():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_scenario = next(s for s in result.scenarios if s.lot_layout_type == LotLayoutType.FLAG_LOT)
    rear = flag_scenario.resulting_lots[1]
    assert rear.has_direct_frontage is False
    assert rear.meets_min_lot_size is True


def test_fixture3_flag_lot_marked_as_flag_provision():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_scenario = next(s for s in result.scenarios if s.lot_layout_type == LotLayoutType.FLAG_LOT)
    assert flag_scenario.requires_flag_lot_provision is True


# ---------------------------------------------------------------------------
# Fixture 4: Same parcel, flag lots DISALLOWED — must produce 0 scenarios
# ---------------------------------------------------------------------------

def test_fixture4_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_4_flag_lot_disallowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture4_has_flag_lot_not_allowed_flag():
    parcel, zoning, structures, constraints = fixture_4_flag_lot_disallowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    all_flags = result.disqualifying_flags + [
        f for s in result.scenarios for f in s.risk_flags
    ]
    flag_categories = [f.category for f in all_flags]
    assert RiskCategory.REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED in flag_categories


# ---------------------------------------------------------------------------
# Fixture 5: Existing structure blocks all valid splits
# ---------------------------------------------------------------------------

def test_fixture5_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_5_structure_conflict()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture5_has_structure_conflict_flag():
    parcel, zoning, structures, constraints = fixture_5_structure_conflict()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_categories = [f.category for f in result.disqualifying_flags]
    assert RiskCategory.EXISTING_STRUCTURE_CONFLICT in flag_categories


# ---------------------------------------------------------------------------
# Fixture 6: Floodway covers rear third — invalidates scenarios with flood exposure
# ---------------------------------------------------------------------------

def test_fixture6_all_surviving_scenarios_avoid_floodway():
    parcel, zoning, structures, constraints = fixture_6_flood_zone()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    floodway_geom = constraints[0].geometry
    for scenario in result.scenarios:
        for lot in scenario.resulting_lots:
            overlap = lot.geometry.intersection(floodway_geom)
            coverage = overlap.area / lot.area_sqft if lot.area_sqft > 0 else 0
            assert coverage < 0.50, (
                f"Lot in surviving scenario has {coverage:.0%} flood coverage"
            )


# ---------------------------------------------------------------------------
# Fixture 7: Parcel straddles two zoning districts — must flag, not guess
# ---------------------------------------------------------------------------

def test_fixture7_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_7_multi_district()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture7_has_multi_district_flag():
    parcel, zoning, structures, constraints = fixture_7_multi_district()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_categories = [f.category for f in result.disqualifying_flags]
    assert RiskCategory.MULTI_DISTRICT_PARCEL in flag_categories


def test_fixture7_data_gap_is_false():
    parcel, zoning, structures, constraints = fixture_7_multi_district()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.data_gap is False
