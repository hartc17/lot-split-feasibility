"""Tests for /v1/parse/* endpoints — no DB, no network."""

from fastapi.testclient import TestClient

from app.api.app import app

client = TestClient(app)

_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-97.88000, 29.99000],
            [-97.87934, 29.99000],
            [-97.87934, 29.99057],
            [-97.88000, 29.99057],
            [-97.88000, 29.99000],
        ]
    ],
}

_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [{"type": "Feature", "geometry": _POLYGON, "properties": {}}],
}

_KML_BYTES = b"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
  <Document>
    <Placemark>
      <Polygon>
        <outerBoundaryIs>
          <LinearRing>
            <coordinates>
              -97.8800,29.9900,0
              -97.8793,29.9900,0
              -97.8793,29.9908,0
              -97.8800,29.9908,0
              -97.8800,29.9900,0
            </coordinates>
          </LinearRing>
        </outerBoundaryIs>
      </Polygon>
    </Placemark>
  </Document>
</kml>"""


def test_parse_geojson_bare_polygon():
    resp = client.post("/v1/parse/geojson", json=_POLYGON)
    assert resp.status_code == 200
    data = resp.json()
    assert data["polygon"]["type"] == "Polygon"
    assert len(data["edges"]) == 4
    assert data["area_sqft"] > 0
    assert data["area_acres"] > 0


def test_parse_geojson_feature_collection():
    resp = client.post("/v1/parse/geojson", json=_FEATURE_COLLECTION)
    assert resp.status_code == 200
    assert resp.json()["polygon"]["type"] == "Polygon"


def test_parse_geojson_edges_have_length():
    resp = client.post("/v1/parse/geojson", json=_POLYGON)
    edges = resp.json()["edges"]
    assert all(e["length_ft"] > 0 for e in edges)
    assert [e["index"] for e in edges] == [0, 1, 2, 3]


def test_parse_geojson_invalid_type_returns_400():
    resp = client.post("/v1/parse/geojson", json={"type": "Point", "coordinates": [-97.88, 29.99]})
    assert resp.status_code == 400


def test_parse_kml_valid():
    resp = client.post(
        "/v1/parse/kml",
        files={"file": ("parcel.kml", _KML_BYTES, "application/vnd.google-earth.kml+xml")},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["polygon"]["type"] == "Polygon"
    assert len(data["edges"]) > 0


def test_parse_kml_empty_file_returns_400():
    resp = client.post(
        "/v1/parse/kml",
        files={"file": ("empty.kml", b"", "application/vnd.google-earth.kml+xml")},
    )
    assert resp.status_code == 400


def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
