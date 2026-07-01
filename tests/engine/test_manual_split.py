"""
Unit tests for evaluate_manual_split().
All geometries in feet, frontage along y=0.
"""

import pytest
from shapely.geometry import LineString, Polygon

from app.engine.manual_split import evaluate_manual_split
from app.engine.types import ParcelGeometryInput, RiskCategory, ZoningRulesInput


def _rect(w: float, d: float) -> Polygon:
    return Polygon([(0, 0), (w, 0), (w, d), (0, d)])


def _parcel(w: float, d: float) -> ParcelGeometryInput:
    return ParcelGeometryInput(
        boundary=_rect(w, d),
        frontage_edge=LineString([(0, 0), (w, 0)]),
        zoning_district_code="R-1",
    )


_ZONING = ZoningRulesInput(
    min_lot_area_sqft=5000,
    min_lot_width_ft=40,
    setback_front_ft=20,
    setback_side_ft=5,
    setback_rear_ft=20,
    requires_public_road_frontage=True,
    allows_flag_lots=False,
    minor_subdivision_threshold=4,
    min_road_frontage_ft=40,
)


def test_single_vertical_cut_produces_two_lots():
    parcel = _parcel(80, 125)
    cut = LineString([(40, -10), (40, 135)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    assert len(result.lots) == 2


def test_lots_sum_to_parcel_area():
    parcel = _parcel(80, 125)
    cut = LineString([(40, -10), (40, 135)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    total = sum(lot.area_sqft for lot in result.lots)
    assert abs(total - 80 * 125) < 1.0


def test_even_split_both_lots_viable():
    parcel = _parcel(80, 125)
    cut = LineString([(40, -10), (40, 135)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    assert result.all_lots_viable is True
    assert all(lot.meets_min_lot_size for lot in result.lots)
    assert all(lot.meets_min_frontage for lot in result.lots)


def test_each_lot_has_correct_frontage():
    parcel = _parcel(80, 125)
    cut = LineString([(40, -10), (40, 135)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    assert all(lot.has_direct_frontage for lot in result.lots)
    for lot in result.lots:
        assert abs(lot.frontage_ft - 40.0) < 2.0


def test_area_shortfall_flag_on_tiny_lots():
    parcel = _parcel(80, 80)  # 6400 sqft, can't make two 5000 sqft lots
    cut = LineString([(40, -10), (40, 90)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    flag_cats = [f.category for f in result.flags]
    assert RiskCategory.ZONING_AREA_SHORTFALL in flag_cats
    assert result.all_lots_viable is False


def test_uneven_cut_area_shortfall():
    parcel = _parcel(80, 125)
    cut = LineString([(10, -10), (10, 135)])  # 10ft strip vs 70ft remainder
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    # 10x125 = 1250 sqft < 5000 minimum
    assert any(not lot.meets_min_lot_size for lot in result.lots)
    assert RiskCategory.ZONING_AREA_SHORTFALL in [f.category for f in result.flags]


def test_two_cuts_produce_three_lots():
    parcel = _parcel(120, 125)
    cut1 = LineString([(40, -10), (40, 135)])
    cut2 = LineString([(80, -10), (80, 135)])
    result = evaluate_manual_split(parcel, [cut1, cut2], _ZONING)
    assert len(result.lots) == 3


def test_non_crossing_line_returns_original():
    parcel = _parcel(80, 125)
    # Line entirely outside the parcel should not split it
    outside_line = LineString([(200, 0), (200, 125)])
    result = evaluate_manual_split(parcel, [outside_line], _ZONING)
    assert len(result.lots) == 1


def test_area_acres_conversion():
    parcel = _parcel(80, 125)
    cut = LineString([(40, -10), (40, 135)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    for lot in result.lots:
        assert abs(lot.area_acres - lot.area_sqft / 43560.0) < 0.0001


def test_no_frontage_flag_for_interior_lot():
    # Wide parcel split horizontally - rear section has no road frontage
    parcel = _parcel(80, 250)
    # Horizontal cut at y=125: front lot gets frontage, rear lot does not
    cut = LineString([(-10, 125), (90, 125)])
    result = evaluate_manual_split(parcel, [cut], _ZONING)
    assert len(result.lots) == 2
    has_frontage = [lot.has_direct_frontage for lot in result.lots]
    assert True in has_frontage
    assert False in has_frontage
    assert RiskCategory.INSUFFICIENT_ROAD_ACCESS in [f.category for f in result.flags]


def test_frontage_shortfall_flag():
    zoning_wide = ZoningRulesInput(
        min_lot_area_sqft=1000,
        min_lot_width_ft=40,
        setback_front_ft=10,
        setback_side_ft=5,
        setback_rear_ft=10,
        requires_public_road_frontage=True,
        allows_flag_lots=False,
        minor_subdivision_threshold=4,
        min_road_frontage_ft=50,  # requires 50ft but each lot gets only 30ft
    )
    parcel = _parcel(60, 125)
    cut = LineString([(30, -10), (30, 135)])
    result = evaluate_manual_split(parcel, [cut], zoning_wide)
    flag_cats = [f.category for f in result.flags]
    assert RiskCategory.ZONING_FRONTAGE_SHORTFALL in flag_cats


def test_no_road_frontage_required_skips_frontage_check():
    zoning_no_frontage = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        setback_front_ft=20,
        setback_side_ft=5,
        setback_rear_ft=20,
        requires_public_road_frontage=False,
        allows_flag_lots=False,
        minor_subdivision_threshold=4,
    )
    parcel = _parcel(80, 250)
    # Horizontal cut creates a rear lot with no road frontage
    cut = LineString([(-10, 125), (90, 125)])
    result = evaluate_manual_split(parcel, [cut], zoning_no_frontage)
    # With requires_public_road_frontage=False, meets_min_frontage should be True
    assert all(lot.meets_min_frontage for lot in result.lots)
