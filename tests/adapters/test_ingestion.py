"""Tests for ParcelIngestionService and JurisdictionConfig.from_orm — mocked throughout."""
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.adapters.base import JurisdictionConfig, FieldMapping
from app.adapters.ingestion import ParcelIngestionService
from app.adapters.base import ParcelRecord

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[
        [-97.880, 29.990], [-97.879, 29.990],
        [-97.879, 29.991], [-97.880, 29.991],
        [-97.880, 29.990],
    ]],
}


def _make_jurisdiction(gis_url: str | None = "https://example.com/FeatureServer/0",
                       field_map: dict | None = None,
                       code_map: dict | None = None) -> MagicMock:
    j = MagicMock()
    j.id = uuid.uuid4()
    j.name = "City of Kyle, TX"
    j.gis_feature_server_url = gis_url
    j.gis_field_map = field_map or {"apn": "PROP_ID"}
    j.gis_zoning_code_map = code_map or {"R-1-2": "R-1-2"}
    return j


def _make_parcel_record(apn: str = "R102610") -> ParcelRecord:
    return ParcelRecord(
        apn=apn,
        geometry_geojson=_POLYGON_GEOJSON,
        address_normalized=None,
        zoning_code_raw="R-1-2",
        owner_name=None,
        assessed_land_value=None,
        assessed_improvement_value=None,
        last_sale_price=None,
        last_sale_date=None,
        existing_structures_count=0,
        raw_source_data={"PROP_ID": apn},
    )


def _make_session(existing_parcel=None) -> MagicMock:
    session = MagicMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_parcel
    session.execute.return_value = result
    return session


# ------------------------------------------------------------------
# JurisdictionConfig.from_orm
# ------------------------------------------------------------------

def test_from_orm_raises_if_no_gis_url():
    j = _make_jurisdiction(gis_url=None)
    with pytest.raises(ValueError, match="gis_feature_server_url"):
        JurisdictionConfig.from_orm(j)


def test_from_orm_raises_if_no_apn_field():
    j = _make_jurisdiction(field_map={"address": "ADDR"})  # missing 'apn'
    with pytest.raises(ValueError, match="apn"):
        JurisdictionConfig.from_orm(j)


def test_from_orm_builds_config_correctly():
    j = _make_jurisdiction(
        gis_url="https://example.com/FeatureServer/0",
        field_map={"apn": "PROP_ID", "address": "SITUS_ADDR"},
    )
    config = JurisdictionConfig.from_orm(j)
    assert config.jurisdiction_name == j.name
    assert config.feature_server_url == j.gis_feature_server_url
    assert config.field_mapping.apn == "PROP_ID"
    assert config.field_mapping.address == "SITUS_ADDR"


# ------------------------------------------------------------------
# ParcelIngestionService.ingest_by_apn
# ------------------------------------------------------------------

def test_ingest_by_apn_returns_none_when_adapter_returns_none():
    service = ParcelIngestionService()
    j = _make_jurisdiction()
    session = _make_session()
    with patch("app.adapters.ingestion.ArcGISParcelAdapter") as MockAdapter:
        MockAdapter.return_value.fetch_by_apn.return_value = None
        result = service.ingest_by_apn("NOTFOUND", j, session)
    assert result is None
    session.add.assert_not_called()


def test_ingest_by_apn_inserts_new_parcel():
    service = ParcelIngestionService()
    j = _make_jurisdiction()
    session = _make_session(existing_parcel=None)

    record = _make_parcel_record()
    with patch("app.adapters.ingestion.ArcGISParcelAdapter") as MockAdapter, \
         patch("app.adapters.ingestion.resolve_zoning_district_id", return_value=None):
        MockAdapter.return_value.fetch_by_apn.return_value = record
        result = service.ingest_by_apn("R102610", j, session)

    assert result is not None
    session.add.assert_called_once()


def test_ingest_by_apn_updates_existing_parcel():
    existing = MagicMock()
    existing.apn = "R102610"
    service = ParcelIngestionService()
    j = _make_jurisdiction()
    session = _make_session(existing_parcel=existing)

    record = _make_parcel_record()
    with patch("app.adapters.ingestion.ArcGISParcelAdapter") as MockAdapter, \
         patch("app.adapters.ingestion.resolve_zoning_district_id", return_value=None):
        MockAdapter.return_value.fetch_by_apn.return_value = record
        result = service.ingest_by_apn("R102610", j, session)

    assert result is existing
    session.add.assert_not_called()


def test_ingest_by_apn_raises_when_jurisdiction_not_configured():
    service = ParcelIngestionService()
    j = _make_jurisdiction(gis_url=None)
    session = _make_session()
    with pytest.raises(ValueError, match="gis_feature_server_url"):
        service.ingest_by_apn("R102610", j, session)


def test_ingest_by_apn_does_not_swallow_db_exception():
    service = ParcelIngestionService()
    j = _make_jurisdiction()

    session = MagicMock()
    session.execute.side_effect = Exception("DB connection lost")

    record = _make_parcel_record()
    with patch("app.adapters.ingestion.ArcGISParcelAdapter") as MockAdapter, \
         patch("app.adapters.ingestion.resolve_zoning_district_id", return_value=None):
        MockAdapter.return_value.fetch_by_apn.return_value = record
        with pytest.raises(Exception, match="DB connection lost"):
            service.ingest_by_apn("R102610", j, session)
