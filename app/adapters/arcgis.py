from __future__ import annotations

import logging
from datetime import date, datetime

import requests

from app.adapters.base import FieldMapping, JurisdictionConfig, ParcelRecord

logger = logging.getLogger(__name__)


class ArcGISParcelAdapter:
    """
    Generic ArcGIS REST FeatureServer adapter.
    Parameterized entirely by JurisdictionConfig — no county-specific code here.
    """

    def __init__(self, config: JurisdictionConfig, timeout: int = 15) -> None:
        self._config = config
        self._timeout = timeout
        self._session = requests.Session()

    def fetch_by_apn(self, apn: str) -> ParcelRecord | None:
        apn_field = self._config.field_mapping.apn
        params = {
            "where": f"{apn_field}='{apn}'",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
        }
        return self._query(params)

    def fetch_by_location(self, lat: float, lon: float) -> ParcelRecord | None:
        params = {
            "geometry": f"{lon},{lat}",
            "geometryType": "esriGeometryPoint",
            "spatialRel": "esriSpatialRelIntersects",
            "inSR": "4326",
            "outFields": "*",
            "returnGeometry": "true",
            "f": "geojson",
        }
        return self._query(params)

    def _query(self, params: dict) -> ParcelRecord | None:
        url = f"{self._config.feature_server_url}/query"
        logger.debug("ArcGIS query %s params=%s", url, params)
        response = self._session.get(url, params=params, timeout=self._timeout)
        response.raise_for_status()
        fc = response.json()
        features = fc.get("features", [])
        if not features:
            return None
        if len(features) > 1:
            logger.warning(
                "ArcGIS returned %d features; using first. url=%s params=%s",
                len(features),
                url,
                params,
            )
        return self._parse_feature(features[0])

    def _parse_feature(self, feature: dict) -> ParcelRecord:
        # ArcGIS GeoJSON uses "properties"; esriJSON uses "attributes"
        props: dict = feature.get("properties") or feature.get("attributes") or {}
        fm: FieldMapping = self._config.field_mapping

        def get_str(name: str | None) -> str | None:
            if name is None or name not in props or props[name] is None:
                return None
            return str(props[name]).strip() or None

        def get_float(name: str | None) -> float | None:
            v = get_str(name)
            if v is None:
                return None
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        def get_date(name: str | None) -> date | None:
            v = get_str(name)
            if v is None:
                return None
            try:
                return datetime.strptime(v, self._config.date_format).date()
            except ValueError:
                logger.debug("Could not parse date %r with format %s", v, self._config.date_format)
                return None

        def get_int(name: str | None, default: int = 0) -> int:
            v = get_float(name)
            return int(v) if v is not None else default

        apn_value = props.get(fm.apn)
        if apn_value is None:
            raise ValueError(
                f"APN field '{fm.apn}' missing from feature properties. "
                f"Available fields: {list(props.keys())}"
            )

        return ParcelRecord(
            apn=str(apn_value).strip(),
            geometry_geojson=feature["geometry"],
            address_normalized=get_str(fm.address),
            zoning_code_raw=get_str(fm.zoning_code),
            owner_name=get_str(fm.owner_name),
            assessed_land_value=get_float(fm.assessed_land),
            assessed_improvement_value=get_float(fm.assessed_improvement),
            last_sale_price=get_float(fm.last_sale_price),
            last_sale_date=get_date(fm.last_sale_date),
            existing_structures_count=get_int(fm.structures_count),
            raw_source_data=props,
        )
