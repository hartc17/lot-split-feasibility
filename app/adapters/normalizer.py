from __future__ import annotations

import uuid
from datetime import UTC, datetime

from geoalchemy2.shape import from_shape
from pyproj import Geod
from shapely.geometry import shape as to_shape

from app.adapters.base import ParcelRecord

_GEOD = Geod(ellps="WGS84")
_SQM_TO_SQFT = 10.7639104167


def compute_area_sqft(geometry_geojson: dict) -> float:
    """
    Geodetic area in square feet.
    Uses pyproj.Geod so no projection is needed — accurate for any EPSG:4326 polygon.
    """
    polygon = to_shape(geometry_geojson)
    area_m2, _ = _GEOD.geometry_area_perimeter(polygon)
    return abs(area_m2) * _SQM_TO_SQFT


def normalize(
    record: ParcelRecord,
    jurisdiction_id: uuid.UUID,
    zoning_district_id: uuid.UUID | None,
) -> dict:
    """
    Convert a ParcelRecord into a dict of Parcel column values ready for upsert.
    Computes area from geometry; does not trust county-reported area fields.
    """
    polygon = to_shape(record.geometry_geojson)
    area_sqft = compute_area_sqft(record.geometry_geojson)

    return {
        "jurisdiction_id": jurisdiction_id,
        "apn": record.apn,
        "address_normalized": record.address_normalized,
        "geometry": from_shape(polygon, srid=4326),
        "centroid": from_shape(polygon.centroid, srid=4326),
        "area_sqft": area_sqft,
        "area_acres": area_sqft / 43_560.0,
        "zoning_district_id": zoning_district_id,
        "zoning_code_raw": record.zoning_code_raw,
        "existing_structures_count": record.existing_structures_count,
        "assessed_land_value": record.assessed_land_value,
        "assessed_improvement_value": record.assessed_improvement_value,
        "last_sale_price": record.last_sale_price,
        "last_sale_date": record.last_sale_date,
        "owner_name": record.owner_name,
        "raw_assessor_data": record.raw_source_data,
        "data_fetched_at": datetime.now(UTC),
    }
