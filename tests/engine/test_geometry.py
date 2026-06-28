import numpy as np
import pytest
from shapely.geometry import LineString, Polygon

from app.engine.geometry import (
    has_buildable_envelope,
    interior_normal,
    measure_frontage_width,
)
from app.engine.types import StructureInput, ZoningRulesInput


@pytest.fixture
def rect_parcel():
    return Polygon([(0, 0), (80, 0), (80, 125), (0, 125)])


@pytest.fixture
def bottom_frontage():
    return LineString([(0, 0), (80, 0)])


@pytest.fixture
def base_zoning():
    return ZoningRulesInput(
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


def test_interior_normal_points_upward_for_bottom_frontage(rect_parcel, bottom_frontage):
    v = interior_normal(bottom_frontage, rect_parcel)
    assert abs(v[0]) < 0.01, "x-component should be ~0"
    assert v[1] > 0.99, "y-component should be ~1.0 (pointing inward)"


def test_interior_normal_is_unit_vector(rect_parcel, bottom_frontage):
    v = interior_normal(bottom_frontage, rect_parcel)
    assert abs(np.linalg.norm(v) - 1.0) < 1e-9


def test_measure_frontage_width_full_lot(bottom_frontage):
    lot = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    p1, p2 = np.array(bottom_frontage.coords[0]), np.array(bottom_frontage.coords[-1])
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    width = measure_frontage_width(lot, u)
    assert abs(width - 40.0) < 0.1


def test_has_buildable_envelope_sufficient_lot(base_zoning):
    # 40x125ft lot; after 20ft front + 20ft rear + 5ft each side: 30x85ft buildable
    lot = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    assert has_buildable_envelope(lot, base_zoning, []) is True


def test_has_buildable_envelope_too_small_lot(base_zoning):
    # 10x30ft lot — after setbacks nothing remains
    lot = Polygon([(0, 0), (10, 0), (10, 30), (0, 30)])
    assert has_buildable_envelope(lot, base_zoning, []) is False


def test_has_buildable_envelope_with_blocking_structure(base_zoning):
    # 40x125ft lot, uniform setback = min(20,5,20) = 5ft → buildable zone = x=5..35, y=5..120
    # House at x=10..30, y=10..115; when buffered by 5ft it covers x=5..35, y=5..120 exactly,
    # leaving nothing for a new building.
    lot = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    house = StructureInput(footprint=Polygon([(10, 10), (30, 10), (30, 115), (10, 115)]))
    assert has_buildable_envelope(lot, base_zoning, [house]) is False
