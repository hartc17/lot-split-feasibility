"""Tests for ArcGISParcelAdapter — all HTTP is mocked, no network calls."""
import json
from unittest.mock import MagicMock

import pytest
import requests

from app.adapters.arcgis import ArcGISParcelAdapter
from app.adapters.base import FieldMapping, JurisdictionConfig

# ------------------------------------------------------------------
# Shared fixtures
# ------------------------------------------------------------------

# A tiny square polygon near Kyle TX in EPSG:4326
_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [-97.880, 29.990],
        [-97.879, 29.990],
        [-97.879, 29.991],
        [-97.880, 29.991],
        [-97.880, 29.990],
    ]],
}

_FEATURE = {
    "type": "Feature",
    "geometry": _POLYGON_GEOJSON,
    "properties": {
        "PROP_ID": "R102610",
        "Class": "A",
    },
}

_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [_FEATURE],
}

_EMPTY_COLLECTION = {
    "type": "FeatureCollection",
    "features": [],
}


@pytest.fixture()
def config() -> JurisdictionConfig:
    return JurisdictionConfig(
        jurisdiction_name="Test County",
        feature_server_url="https://example.com/arcgis/rest/services/Parcels/FeatureServer/0",
        field_mapping=FieldMapping(apn="PROP_ID"),
    )


@pytest.fixture()
def adapter(config: JurisdictionConfig) -> ArcGISParcelAdapter:
    return ArcGISParcelAdapter(config)


def _mock_response(data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    if status_code >= 400:
        resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
    else:
        resp.raise_for_status.return_value = None
    return resp


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------

def test_fetch_by_apn_returns_record(adapter, mocker):
    mocker.patch.object(adapter._session, "get", return_value=_mock_response(_FEATURE_COLLECTION))
    record = adapter.fetch_by_apn("R102610")
    assert record is not None
    assert record.apn == "R102610"
    assert record.geometry_geojson["type"] == "Polygon"
    assert record.existing_structures_count == 0


def test_fetch_by_apn_returns_none_when_no_features(adapter, mocker):
    mocker.patch.object(adapter._session, "get", return_value=_mock_response(_EMPTY_COLLECTION))
    record = adapter.fetch_by_apn("NOTFOUND")
    assert record is None


def test_fetch_by_apn_raises_on_http_error(adapter, mocker):
    mocker.patch.object(
        adapter._session, "get",
        return_value=_mock_response({}, status_code=500),
    )
    with pytest.raises(requests.HTTPError):
        adapter.fetch_by_apn("R102610")


def test_fetch_by_apn_builds_correct_query_url(adapter, mocker):
    mock_get = mocker.patch.object(
        adapter._session, "get",
        return_value=_mock_response(_FEATURE_COLLECTION),
    )
    adapter.fetch_by_apn("R102610")
    call_args = mock_get.call_args
    url = call_args[0][0]
    params = call_args[1]["params"]
    assert url.endswith("/query")
    assert "PROP_ID" in params["where"]
    assert "R102610" in params["where"]
    assert params["f"] == "geojson"
    assert params["returnGeometry"] == "true"


def test_fetch_by_location_returns_record(adapter, mocker):
    mocker.patch.object(adapter._session, "get", return_value=_mock_response(_FEATURE_COLLECTION))
    record = adapter.fetch_by_location(lat=29.990, lon=-97.880)
    assert record is not None
    assert record.apn == "R102610"


def test_fetch_by_location_builds_point_query(adapter, mocker):
    mock_get = mocker.patch.object(
        adapter._session, "get",
        return_value=_mock_response(_FEATURE_COLLECTION),
    )
    adapter.fetch_by_location(lat=29.990, lon=-97.880)
    params = mock_get.call_args[1]["params"]
    assert params["geometryType"] == "esriGeometryPoint"
    assert "-97.88" in params["geometry"]
    assert "29.99" in params["geometry"]


def test_multiple_features_uses_first_and_warns(adapter, mocker, caplog):
    two_features = {
        "type": "FeatureCollection",
        "features": [_FEATURE, {**_FEATURE, "properties": {"PROP_ID": "R102611", "Class": "A"}}],
    }
    mocker.patch.object(adapter._session, "get", return_value=_mock_response(two_features))
    import logging
    with caplog.at_level(logging.WARNING, logger="app.adapters.arcgis"):
        record = adapter.fetch_by_apn("R102610")
    assert record.apn == "R102610"
    assert "2 features" in caplog.text


def test_parse_feature_with_optional_fields(mocker):
    config = JurisdictionConfig(
        jurisdiction_name="Full County",
        feature_server_url="https://example.com/arcgis/rest/services/P/FeatureServer/0",
        field_mapping=FieldMapping(
            apn="PROP_ID",
            address="SITUS_ADDR",
            assessed_land="LAND_VAL",
            last_sale_date="SALE_DATE",
        ),
        date_format="%m/%d/%Y",
    )
    adapter = ArcGISParcelAdapter(config)
    feature = {
        "geometry": _POLYGON_GEOJSON,
        "properties": {
            "PROP_ID": "R999",
            "SITUS_ADDR": "123 Main St",
            "LAND_VAL": "85000.50",
            "SALE_DATE": "03/15/2023",
        },
    }
    record = adapter._parse_feature(feature)
    assert record.apn == "R999"
    assert record.address_normalized == "123 Main St"
    assert record.assessed_land_value == pytest.approx(85000.50)
    from datetime import date
    assert record.last_sale_date == date(2023, 3, 15)
