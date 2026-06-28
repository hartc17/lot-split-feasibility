"""
Synthetic parcel fixtures for engine unit tests.
All coordinates in feet, frontage along y=0 (bottom edge).
These correspond exactly to the 7 fixtures in spec Section 6.3.
"""
from shapely.geometry import LineString, Polygon

from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ConstraintType,
    ParcelGeometryInput,
    StructureInput,
    ZoningRulesInput,
)

# Shared zoning defaults used across multiple fixtures
_BASE_ZONING = dict(
    setback_front_ft=20,
    setback_side_ft=5,
    setback_rear_ft=20,
    requires_public_road_frontage=True,
    allows_flag_lots=False,
    minor_subdivision_threshold=4,
    min_road_frontage_ft=40,
)


def _rect(width: float, depth: float) -> Polygon:
    """Axis-aligned rectangle from (0,0) to (width, depth)."""
    return Polygon([(0, 0), (width, 0), (width, depth), (0, depth)])


def _frontage(width: float) -> LineString:
    """Bottom edge of parcel as the frontage edge."""
    return LineString([(0, 0), (width, 0)])


def fixture_1_clean_split():
    """
    Fixture 1: 80x125ft parcel (10,000 sqft = 2x minimum).
    Ample frontage (80ft), no constraints, no structures.
    Expected: valid SIMPLE_HALVE into two 40x125ft lots.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    return parcel, zoning, [], []


def fixture_2_area_shortfall():
    """
    Fixture 2: 80x112.5ft parcel (9,000 sqft = 1.8x minimum).
    Same zoning as fixture 1. Cannot produce two 5,000 sqft lots.
    Expected: 0 valid scenarios; ZONING_AREA_SHORTFALL flag with actual numbers.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 112.5),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    return parcel, zoning, [], []


def fixture_3_flag_lot_allowed():
    """
    Fixture 3: 60x250ft parcel (15,000 sqft = 3x minimum).
    Frontage only 60ft — too narrow for SIMPLE_HALVE (needs 2x40ft=80ft).
    Flag lots allowed; access strip = 20ft min.
    Expected: valid FLAG_LOT scenario (40ft conventional front lot + L-shaped rear).
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(60, 250),
        frontage_edge=_frontage(60),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        allows_flag_lots=True,
        flag_lot_min_access_strip_ft=20,
        min_road_frontage_ft=40,
        setback_front_ft=20,
        setback_side_ft=5,
        setback_rear_ft=20,
        requires_public_road_frontage=True,
        minor_subdivision_threshold=4,
    )
    return parcel, zoning, [], []


def fixture_4_flag_lot_disallowed():
    """
    Fixture 4: Same 60x250ft parcel, same zoning but allows_flag_lots=False.
    SIMPLE_HALVE fails (too narrow). FLAG_LOT not evaluated (not allowed).
    Expected: 0 valid scenarios; REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED flag.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(60, 250),
        frontage_edge=_frontage(60),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        allows_flag_lots=False,
        flag_lot_min_access_strip_ft=None,
        min_road_frontage_ft=40,
        setback_front_ft=20,
        setback_side_ft=5,
        setback_rear_ft=20,
        requires_public_road_frontage=True,
        minor_subdivision_threshold=4,
    )
    return parcel, zoning, [], []


def fixture_5_structure_conflict():
    """
    Fixture 5: 80x125ft parcel (clean geometry), but existing 40x60ft house
    is centered such that no valid SIMPLE_HALVE split avoids setback violation.
    House: x=20..60, y=30..90. Any split at x=t must have t >= 65 (too wide)
    or t <= 15 (too narrow) to clear the 5ft side setback -- both fail min_lot_width=40.
    Expected: EXISTING_STRUCTURE_CONFLICT flag, 0 valid scenarios.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    # House footprint: x=20..60, y=30..90
    house = StructureInput(
        footprint=Polygon([(20, 30), (60, 30), (60, 90), (20, 90)])
    )
    return parcel, zoning, [house], []


def fixture_6_flood_zone():
    """
    Fixture 6: 80x125ft parcel. FEMA floodway (BLOCKING) covers back third
    (y=83..125, full width). A split at x=40 creates valid front lots but
    any rear-lot scenario with buildable envelope in the floodway is invalid.
    Expected: valid scenario for front half; any scenario putting buildable area
    in floodway is discarded.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    # Floodway covers the rear ~33% of the parcel
    floodway = ConstraintInput(
        constraint_type=ConstraintType.FLOOD_ZONE,
        severity=ConstraintSeverity.BLOCKING,
        geometry=Polygon([(0, 83), (80, 83), (80, 125), (0, 125)]),
    )
    return parcel, zoning, [], [floodway]


def fixture_7_multi_district():
    """
    Fixture 7: Parcel straddles two zoning districts (multi_district=True).
    Expected: MULTI_DISTRICT_PARCEL flag, 0 scenarios, data_gap=False.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
        multi_district=True,
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    return parcel, zoning, [], []
