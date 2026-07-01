"""
HTTP-layer tests for POST /v1/split/compute.
No DB, no network. Uses FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient

from app.api.app import app

client = TestClient(app)

# A real WGS84 parcel rectangle (approximately 80x125ft near Austin, TX)
_PARCEL = {
    "type": "Polygon",
    "coordinates": [[
        [-97.7500, 30.2500],
        [-97.7490, 30.2500],
        [-97.7490, 30.2513],
        [-97.7500, 30.2513],
        [-97.7500, 30.2500],
    ]],
}

# A vertical split line through the parcel
_SPLIT_LINE = {
    "type": "LineString",
    "coordinates": [[-97.7495, 30.2490], [-97.7495, 30.2520]],
}

_ZONING = {
    "district_code": "R-1",
    "min_lot_area_sqft": 5000,
    "min_lot_width_ft": 40,
    "setback_front_ft": 20,
    "setback_side_ft": 5,
    "setback_rear_ft": 20,
    "requires_public_road_frontage": True,
    "allows_flag_lots": False,
    "flag_lot_min_access_strip_ft": 20,
    "minor_subdivision_threshold": 4,
}


def test_compute_split_returns_200():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    assert resp.status_code == 200


def test_compute_split_returns_two_sections():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    data = resp.json()
    assert len(data["sections"]) == 2


def test_compute_split_section_fields_present():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    section = resp.json()["sections"][0]
    for field in [
        "geometry", "area_sqft", "area_acres", "frontage_ft",
        "buildable_width_ft", "buildable_depth_ft",
        "has_direct_frontage", "meets_min_lot_size",
        "meets_min_frontage", "has_buildable_envelope",
    ]:
        assert field in section, f"Missing field: {field}"


def test_compute_split_geometry_is_wgs84_polygon():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    for section in resp.json()["sections"]:
        assert section["geometry"]["type"] == "Polygon"
        lon = section["geometry"]["coordinates"][0][0][0]
        # Should be a plausible WGS84 longitude (not feet)
        assert -180 < lon < 180


def test_compute_split_all_sections_viable_field():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    data = resp.json()
    assert "all_sections_viable" in data
    assert isinstance(data["all_sections_viable"], bool)


def test_compute_split_returns_flags_list():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    assert isinstance(resp.json()["flags"], list)


def test_compute_split_invalid_geometry_returns_400():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": {"type": "Point", "coordinates": [-97.75, 30.25]},
            "split_lines": [_SPLIT_LINE],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    assert resp.status_code == 422


def test_compute_split_empty_split_lines_returns_422():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [],
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    assert resp.status_code == 422


def test_compute_split_default_frontage_indices_when_omitted():
    resp = client.post(
        "/v1/split/compute",
        json={
            "geometry": _PARCEL,
            "split_lines": [_SPLIT_LINE],
            "zoning": _ZONING,
        },
    )
    assert resp.status_code == 200


def test_feasibility_includes_manual_split_when_split_lines_provided():
    resp = client.post(
        "/v1/feasibility",
        json={
            "geometry": _PARCEL,
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
            "split_lines": [_SPLIT_LINE],
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["manual_split"] is not None
    assert "sections" in data["manual_split"]
    assert "all_sections_viable" in data["manual_split"]


def test_feasibility_manual_split_none_when_no_split_lines():
    resp = client.post(
        "/v1/feasibility",
        json={
            "geometry": _PARCEL,
            "frontage_edge_indices": [0],
            "zoning": _ZONING,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["manual_split"] is None
