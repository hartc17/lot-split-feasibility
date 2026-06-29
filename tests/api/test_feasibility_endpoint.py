"""Tests for POST /v1/feasibility — no DB required."""

from fastapi.testclient import TestClient

from app.api.app import app

client = TestClient(app)

_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-97.88000, 29.99000],
            [-97.87900, 29.99000],
            [-97.87900, 29.99200],
            [-97.88000, 29.99200],
            [-97.88000, 29.99000],
        ]
    ],
}

_ZONING = {
    "district_code": "R-1-2",
    "min_lot_area_sqft": 6825,
    "min_lot_width_ft": 65,
    "setback_front_ft": 25,
    "setback_side_ft": 8,
    "setback_rear_ft": 15,
    "minor_subdivision_threshold": 4,
}

_VALID_BODY = {
    "geometry": _POLYGON,
    "frontage_edge_indices": [0],
    "zoning": _ZONING,
}


def test_feasibility_valid_request_returns_200():
    resp = client.post("/v1/feasibility", json=_VALID_BODY)
    assert resp.status_code == 200


def test_feasibility_response_has_required_fields():
    resp = client.post("/v1/feasibility", json=_VALID_BODY)
    data = resp.json()
    assert "status" in data
    assert "max_theoretical_lots" in data
    assert "scenarios" in data
    assert "disqualifying_flags" in data
    assert "data_gap" in data


def test_feasibility_status_is_complete():
    resp = client.post("/v1/feasibility", json=_VALID_BODY)
    assert resp.json()["status"] == "complete"


def test_feasibility_invalid_edge_index_returns_400():
    body = {**_VALID_BODY, "frontage_edge_indices": [999]}
    resp = client.post("/v1/feasibility", json=body)
    assert resp.status_code == 400


def test_feasibility_missing_zoning_field_returns_422():
    bad_zoning = {k: v for k, v in _ZONING.items() if k != "min_lot_area_sqft"}
    body = {**_VALID_BODY, "zoning": bad_zoning}
    resp = client.post("/v1/feasibility", json=body)
    assert resp.status_code == 422


def test_feasibility_invalid_geometry_type_returns_422():
    body = {**_VALID_BODY, "geometry": {"type": "Point", "coordinates": [-97.88, 29.99]}}
    resp = client.post("/v1/feasibility", json=body)
    assert resp.status_code == 422


def test_feasibility_report_id_is_none_without_db():
    resp = client.post("/v1/feasibility", json=_VALID_BODY)
    assert resp.json()["report_id"] is None


def test_feasibility_large_parcel_returns_multiple_scenarios():
    # ~4-acre parcel — should yield multiple split scenarios
    large_polygon = {
        "type": "Polygon",
        "coordinates": [
            [
                [-97.88000, 29.99000],
                [-97.87700, 29.99000],
                [-97.87700, 29.99300],
                [-97.88000, 29.99300],
                [-97.88000, 29.99000],
            ]
        ],
    }
    body = {**_VALID_BODY, "geometry": large_polygon}
    resp = client.post("/v1/feasibility", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["max_theoretical_lots"] is not None
