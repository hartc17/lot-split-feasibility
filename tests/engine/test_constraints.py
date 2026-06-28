import pytest
from shapely.geometry import Polygon

from app.engine.constraints import apply_constraints
from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ConstraintType,
    LotLayoutType,
    LotResult,
    RiskCategory,
    ScenarioResult,
    SubdivisionReviewTier,
)


def _make_dummy_scenario(lot_geometries: list[Polygon]) -> ScenarioResult:
    lots = [
        LotResult(
            geometry=g,
            area_sqft=g.area,
            frontage_ft=40.0,
            buildable_width_ft=40.0,
            buildable_depth_ft=g.area / 40.0,
            has_direct_frontage=True,
            meets_min_lot_size=True,
            meets_min_frontage=True,
            has_buildable_envelope=True,
        )
        for g in lot_geometries
    ]
    return ScenarioResult(
        lot_layout_type=LotLayoutType.SIMPLE_HALVE,
        resulting_lots=lots,
        num_resulting_lots=len(lots),
        requires_variance=False,
        requires_rezone=False,
        requires_flag_lot_provision=False,
        subdivision_review_tier=SubdivisionReviewTier.ADMINISTRATIVE_MINOR,
    )


def test_no_constraints_passes_all_scenarios():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])
    result = apply_constraints([scenario], [])
    assert len(result) == 1


def test_blocking_constraint_covering_lot_removes_scenario():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])

    # Floodway covers all of lot_b
    floodway = ConstraintInput(
        constraint_type=ConstraintType.FLOOD_ZONE,
        severity=ConstraintSeverity.BLOCKING,
        geometry=Polygon([(40, 0), (80, 0), (80, 125), (40, 125)]),
    )
    result = apply_constraints([scenario], [floodway])
    assert result == [], "Scenario with BLOCKING constraint on a lot should be removed"


def test_blocking_constraint_on_partial_lot_removes_scenario():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])

    # Floodway covers >80% of lot_b
    floodway = ConstraintInput(
        constraint_type=ConstraintType.FLOOD_ZONE,
        severity=ConstraintSeverity.BLOCKING,
        geometry=Polygon([(40, 20), (80, 20), (80, 125), (40, 125)]),
    )
    result = apply_constraints([scenario], [floodway])
    assert result == []


def test_significant_constraint_adds_risk_flag_but_keeps_scenario():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])

    wetland = ConstraintInput(
        constraint_type=ConstraintType.WETLAND,
        severity=ConstraintSeverity.SIGNIFICANT,
        geometry=Polygon([(50, 100), (80, 100), (80, 125), (50, 125)]),
    )
    result = apply_constraints([scenario], [wetland])
    assert len(result) == 1
    flag_categories = [f.category for f in result[0].risk_flags]
    assert RiskCategory.WETLAND_EXPOSURE in flag_categories


def test_fixture6_floodway_removes_scenarios_with_flood_exposure():
    """Both resulting lots in a side-by-side split extend into the rear floodway."""
    from app.engine.strategies.simple_halve import run_simple_halve
    from tests.fixtures.parcels import fixture_6_flood_zone
    parcel, zoning, structures, constraints = fixture_6_flood_zone()
    scenarios = run_simple_halve(parcel, zoning, structures)
    filtered = apply_constraints(scenarios, constraints)
    for scenario in filtered:
        for lot in scenario.resulting_lots:
            floodway = constraints[0]
            overlap = lot.geometry.intersection(floodway.geometry)
            assert overlap.area / lot.area_sqft < 0.5, \
                "Remaining lot has >50% flood exposure"
