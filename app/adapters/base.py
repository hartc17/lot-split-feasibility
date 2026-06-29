from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from app.models.jurisdiction import Jurisdiction


@dataclass
class ParcelRecord:
    """Normalized fields from a county data source, before DB upsert."""

    apn: str
    geometry_geojson: dict  # GeoJSON Polygon, EPSG:4326
    address_normalized: str | None
    zoning_code_raw: str | None
    owner_name: str | None
    assessed_land_value: float | None
    assessed_improvement_value: float | None
    last_sale_price: float | None
    last_sale_date: date | None
    existing_structures_count: int
    raw_source_data: dict = field(default_factory=dict)


@dataclass
class FieldMapping:
    """
    Maps canonical field roles to the county GIS layer's actual attribute names.
    None means the field is absent in this layer.
    """

    apn: str
    address: str | None = None
    zoning_code: str | None = None
    owner_name: str | None = None
    assessed_land: str | None = None
    assessed_improvement: str | None = None
    last_sale_price: str | None = None
    last_sale_date: str | None = None
    structures_count: str | None = None

    @classmethod
    def from_dict(cls, d: dict) -> FieldMapping:
        return cls(
            apn=d["apn"],
            address=d.get("address"),
            zoning_code=d.get("zoning_code"),
            owner_name=d.get("owner_name"),
            assessed_land=d.get("assessed_land"),
            assessed_improvement=d.get("assessed_improvement"),
            last_sale_price=d.get("last_sale_price"),
            last_sale_date=d.get("last_sale_date"),
            structures_count=d.get("structures_count"),
        )


@dataclass
class JurisdictionConfig:
    """Everything the generic adapter needs to query one jurisdiction's ArcGIS service."""

    jurisdiction_name: str
    feature_server_url: str
    field_mapping: FieldMapping
    date_format: str = "%Y-%m-%d"

    @classmethod
    def from_orm(cls, jurisdiction: Jurisdiction) -> JurisdictionConfig:
        """
        Build config from a Jurisdiction DB record.
        Raises ValueError if GIS columns are not populated.
        """
        if not jurisdiction.gis_feature_server_url:
            raise ValueError(
                f"Jurisdiction '{jurisdiction.name}' has no gis_feature_server_url. "
                "Run the seed script for this jurisdiction before using the parcel adapter."
            )
        field_map: dict = jurisdiction.gis_field_map or {}
        if "apn" not in field_map:
            raise ValueError(
                f"Jurisdiction '{jurisdiction.name}' gis_field_map is missing required key 'apn'."
            )
        return cls(
            jurisdiction_name=jurisdiction.name,
            feature_server_url=jurisdiction.gis_feature_server_url,
            field_mapping=FieldMapping.from_dict(field_map),
        )


class ParcelAdapter(Protocol):
    def fetch_by_apn(self, apn: str) -> ParcelRecord | None: ...
    def fetch_by_location(self, lat: float, lon: float) -> ParcelRecord | None: ...
