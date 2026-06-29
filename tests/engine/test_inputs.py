"""Tests for engine input builders."""
import pytest
from shapely.geometry import LineString, Polygon

from app.engine.inputs import (
    build_parcel_geometry_input,
    build_zoning_rules_input,
    extract_edge,
    extract_edges,
)
from app.engine.types import ParcelGeometryInput, ZoningRulesInput
from app.parsers.geojson import parse_geojson

_POLYGON_4326 = {
    "type": "Polygon",
    "coordinates": [[
        [-97.88000, 29.99000],
        [-97.87934, 29.99000],
        [-97.87934, 29.99057],
        [-97.88000, 29.99057],
        [-97.88000, 29.99000],
    ]],
}

_ZONING_DICT = {
    "district_code": "R-1-2",
    "min_lot_area_sqft": 6825,
    "min_lot_width_ft": 65,
    "setback_front_ft": 25,
    "setback_side_ft": 8,
    "setback_rear_ft": 15,
    "minor_subdivision_threshold": 4,
}


# --- extract_edges / extract_edge ---

def test_extract_edge_returns_linestring():
    poly_4326 = parse_geojson(_POLYGON_4326)
    edge = extract_edge(poly_4326, 0)
    assert isinstance(edge, LineString)
    assert len(list(edge.coords)) == 2


def test_extract_edge_correct_coords():
    poly = Polygon([(0, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    edge0 = extract_edge(poly, 0)
    assert list(edge0.coords) == [(0.0, 0.0), (100.0, 0.0)]

    edge1 = extract_edge(poly, 1)
    assert list(edge1.coords) == [(100.0, 0.0), (100.0, 125.0)]


def test_extract_edge_out_of_range_raises():
    poly = Polygon([(0, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    with pytest.raises(ValueError, match="out of range"):
        extract_edge(poly, 4)


def test_extract_edge_negative_index_raises():
    poly = Polygon([(0, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    with pytest.raises(ValueError, match="out of range"):
        extract_edge(poly, -1)


def test_extract_edges_merges_contiguous():
    poly = Polygon([(0, 0), (50, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    merged = extract_edges(poly, [0, 1])
    assert list(merged.coords) == [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]


def test_extract_edges_single_index_matches_extract_edge():
    poly = Polygon([(0, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    assert list(extract_edges(poly, [0]).coords) == list(extract_edge(poly, 0).coords)


def test_extract_edges_non_contiguous_raises():
    poly = Polygon([(0, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    with pytest.raises(ValueError, match="not contiguous"):
        extract_edges(poly, [0, 2])


def test_extract_edges_out_of_range_raises():
    poly = Polygon([(0, 0), (100, 0), (100, 125), (0, 125), (0, 0)])
    with pytest.raises(ValueError, match="out of range"):
        extract_edges(poly, [0, 99])


# --- build_parcel_geometry_input ---

def test_build_parcel_geometry_input_returns_correct_type():
    poly_4326 = parse_geojson(_POLYGON_4326)
    result = build_parcel_geometry_input(poly_4326, frontage_edge_indices=[0])
    assert isinstance(result, ParcelGeometryInput)
    assert isinstance(result.boundary, Polygon)
    assert isinstance(result.frontage_edge, LineString)


def test_build_parcel_geometry_input_projected_to_feet():
    """Boundary polygon should be in feet — area roughly 43,560 for a ~1-acre parcel."""
    poly_4326 = parse_geojson(_POLYGON_4326)
    result = build_parcel_geometry_input(poly_4326, frontage_edge_indices=[0])
    area_sqft = result.boundary.area
    assert 40_000 < area_sqft < 48_000, f"Expected ~43,560 sqft, got {area_sqft:.0f}"


def test_build_parcel_geometry_input_invalid_edge_raises():
    poly_4326 = parse_geojson(_POLYGON_4326)
    with pytest.raises(ValueError, match="out of range"):
        build_parcel_geometry_input(poly_4326, frontage_edge_indices=[99])


def test_build_parcel_geometry_input_multi_edge_merges():
    poly_4326 = parse_geojson(_POLYGON_4326)
    single = build_parcel_geometry_input(poly_4326, frontage_edge_indices=[0])
    multi  = build_parcel_geometry_input(poly_4326, frontage_edge_indices=[0, 1])
    assert multi.frontage_edge.length > single.frontage_edge.length


def test_build_parcel_geometry_input_passes_district_code():
    poly_4326 = parse_geojson(_POLYGON_4326)
    result = build_parcel_geometry_input(poly_4326, [0], zoning_district_code="R-1-2")
    assert result.zoning_district_code == "R-1-2"


# --- build_zoning_rules_input ---

def test_build_zoning_rules_input_returns_correct_type():
    result = build_zoning_rules_input(_ZONING_DICT)
    assert isinstance(result, ZoningRulesInput)


def test_build_zoning_rules_input_missing_field_raises():
    bad = {k: v for k, v in _ZONING_DICT.items() if k != "min_lot_area_sqft"}
    with pytest.raises(ValueError, match="Missing required"):
        build_zoning_rules_input(bad)


def test_build_zoning_rules_input_zero_value_raises():
    bad = {**_ZONING_DICT, "min_lot_width_ft": 0}
    with pytest.raises(ValueError, match="must be positive"):
        build_zoning_rules_input(bad)


def test_build_zoning_rules_input_defaults():
    result = build_zoning_rules_input(_ZONING_DICT)
    assert result.requires_public_road_frontage is True
    assert result.allows_flag_lots is False
