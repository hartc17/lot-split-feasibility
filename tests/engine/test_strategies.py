from shapely.geometry import LineString, Polygon

from app.engine.strategies.flag_lot import run_flag_lot
from app.engine.strategies.simple_halve import run_frontage_strip, run_simple_halve
from app.engine.types import LotLayoutType, ParcelGeometryInput, ZoningRulesInput
from tests.fixtures.parcels import (
    fixture_1_clean_split,
    fixture_2_area_shortfall,
    fixture_3_flag_lot_allowed,
    fixture_4_flag_lot_disallowed,
    fixture_5_structure_conflict,
)


class TestSimpleHalve:
    def test_fixture1_produces_two_lot_scenario(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_simple_halve(parcel, zoning, structures)
        assert len(results) == 1
        assert results[0].num_resulting_lots == 2
        assert results[0].lot_layout_type == LotLayoutType.SIMPLE_HALVE

    def test_fixture1_both_lots_meet_requirements(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_simple_halve(parcel, zoning, structures)
        for lot in results[0].resulting_lots:
            assert lot.meets_min_lot_size is True, f"Lot area {lot.area_sqft} < min"
            assert lot.meets_min_frontage is True, f"Lot frontage {lot.frontage_ft} < min"
            assert lot.has_direct_frontage is True
            assert lot.has_buildable_envelope is True

    def test_fixture1_lots_sum_to_parcel_area(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_simple_halve(parcel, zoning, structures)
        total = sum(lot.area_sqft for lot in results[0].resulting_lots)
        parcel_area = parcel.boundary.area
        assert abs(total - parcel_area) < 1.0  # within 1 sqft rounding

    def test_fixture2_produces_no_scenarios(self):
        parcel, zoning, structures, _ = fixture_2_area_shortfall()
        results = run_simple_halve(parcel, zoning, structures)
        assert results == []

    def test_fixture3_produces_no_scenarios_parcel_too_narrow(self):
        # 60ft frontage, 40ft min width — can't do two side-by-side 40ft lots
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_simple_halve(parcel, zoning, structures)
        assert results == []

    def test_fixture5_structure_conflict_produces_no_scenarios(self):
        parcel, zoning, structures, _ = fixture_5_structure_conflict()
        results = run_simple_halve(parcel, zoning, structures)
        assert results == []


class TestFrontageStrip:
    def test_wide_parcel_can_produce_three_lots(self):
        # 120ft wide x 125ft deep; min_lot_width=40ft → 3 lots possible
        parcel = ParcelGeometryInput(
            boundary=Polygon([(0, 0), (120, 0), (120, 125), (0, 125)]),
            frontage_edge=LineString([(0, 0), (120, 0)]),
            zoning_district_code="R-1",
        )
        zoning = ZoningRulesInput(
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
        results = run_frontage_strip(parcel, zoning, [])
        lot_counts = [r.num_resulting_lots for r in results]
        assert 3 in lot_counts

    def test_fixture1_also_found_by_frontage_strip(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_frontage_strip(parcel, zoning, structures)
        lot_counts = [r.num_resulting_lots for r in results]
        assert 2 in lot_counts


class TestFlagLot:
    def test_fixture3_produces_flag_lot_scenario(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        assert len(results) >= 1
        assert results[0].lot_layout_type == LotLayoutType.FLAG_LOT
        assert results[0].num_resulting_lots == 2

    def test_fixture3_front_lot_has_direct_frontage(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        front_lot = results[0].resulting_lots[0]
        assert front_lot.has_direct_frontage is True
        assert front_lot.meets_min_lot_size is True
        assert front_lot.meets_min_frontage is True

    def test_fixture3_rear_lot_has_no_direct_frontage_but_valid_area(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        rear_lot = results[0].resulting_lots[1]
        assert rear_lot.has_direct_frontage is False
        assert rear_lot.meets_min_lot_size is True

    def test_fixture3_scenario_marked_as_flag_lot_provision(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        assert results[0].requires_flag_lot_provision is True

    def test_fixture4_flag_lot_disallowed_returns_empty(self):
        parcel, zoning, structures, _ = fixture_4_flag_lot_disallowed()
        results = run_flag_lot(parcel, zoning, structures)
        assert results == []

    def test_fixture3_lots_cover_full_parcel_area(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        total = sum(lot.area_sqft for lot in results[0].resulting_lots)
        parcel_area = parcel.boundary.area
        assert abs(total - parcel_area) < 1.0
