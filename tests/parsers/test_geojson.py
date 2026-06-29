"""Tests for GeoJSON parser."""

import pytest
from shapely.geometry import Polygon

from app.parsers.geojson import parse_geojson

_POLYGON_COORDS = [
    [-97.8800, 29.9900],
    [-97.8793, 29.9900],
    [-97.8793, 29.9908],
    [-97.8800, 29.9908],
    [-97.8800, 29.9900],
]

_BARE_POLYGON = {"type": "Polygon", "coordinates": [_POLYGON_COORDS]}

_FEATURE = {
    "type": "Feature",
    "geometry": _BARE_POLYGON,
    "properties": {},
}

_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [_FEATURE],
}


def test_parse_bare_polygon():
    result = parse_geojson(_BARE_POLYGON)
    assert isinstance(result, Polygon)
    assert result.is_valid


def test_parse_feature():
    result = parse_geojson(_FEATURE)
    assert isinstance(result, Polygon)


def test_parse_feature_collection():
    result = parse_geojson(_FEATURE_COLLECTION)
    assert isinstance(result, Polygon)


def test_parse_multipolygon_returns_largest():
    multi = {
        "type": "MultiPolygon",
        "coordinates": [
            [_POLYGON_COORDS],
            [
                [
                    [-97.87, 29.99],
                    [-97.869, 29.99],
                    [-97.869, 29.991],
                    [-97.87, 29.991],
                    [-97.87, 29.99],
                ]
            ],
        ],
    }
    result = parse_geojson(multi)
    assert isinstance(result, Polygon)


def test_parse_point_raises():
    with pytest.raises(ValueError):
        parse_geojson({"type": "Point", "coordinates": [-97.88, 29.99]})


def test_empty_feature_collection_raises():
    with pytest.raises(ValueError):
        parse_geojson({"type": "FeatureCollection", "features": []})


def test_feature_with_no_geometry_raises():
    with pytest.raises(ValueError):
        parse_geojson({"type": "Feature", "geometry": None, "properties": {}})


def test_unknown_type_raises():
    with pytest.raises(ValueError, match="Unrecognised"):
        parse_geojson({"type": "LineString", "coordinates": []})
