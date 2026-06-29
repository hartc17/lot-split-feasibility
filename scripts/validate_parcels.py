"""
Spot-check real parcels against the county GIS.
Calls the ArcGIS adapter directly (real HTTP — not mocked).

Usage:
    python scripts/validate_parcels.py --apns R102610,R102611,R102612

Outputs a table: APN | geometry? | area_sqft | zoning_code_raw | status
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from app.adapters.arcgis import ArcGISParcelAdapter
from app.adapters.base import FieldMapping, JurisdictionConfig
from app.adapters.normalizer import compute_area_sqft

# Hays County interim config — update feature_server_url once Hub URL is verified
HAYS_CONFIG = JurisdictionConfig(
    jurisdiction_name="Hays County, TX (interim)",
    feature_server_url=(
        "https://gis.urbaneng.com/arcgis/rest/services/HaysCountyParcels/FeatureServer/0"
    ),
    field_mapping=FieldMapping(apn="PROP_ID"),
)

MIN_PLAUSIBLE_SQFT = 1_000
MAX_PLAUSIBLE_SQFT = 5_000_000


def validate_apn(adapter: ArcGISParcelAdapter, apn: str) -> dict:
    try:
        record = adapter.fetch_by_apn(apn)
    except Exception as exc:
        return {
            "apn": apn,
            "status": f"ERROR: {exc}",
            "area_sqft": None,
            "geometry": False,
            "zoning_code_raw": None,
        }

    if record is None:
        return {
            "apn": apn,
            "status": "NOT FOUND",
            "area_sqft": None,
            "geometry": False,
            "zoning_code_raw": None,
        }

    try:
        area = compute_area_sqft(record.geometry_geojson)
    except Exception as exc:
        return {
            "apn": apn,
            "status": f"AREA ERROR: {exc}",
            "area_sqft": None,
            "geometry": True,
            "zoning_code_raw": record.zoning_code_raw,
        }

    if area < MIN_PLAUSIBLE_SQFT:
        status = f"WARN: area too small ({area:.0f} sqft)"
    elif area > MAX_PLAUSIBLE_SQFT:
        status = f"WARN: area too large ({area:.0f} sqft)"
    else:
        status = "OK"

    return {
        "apn": apn,
        "geometry": True,
        "area_sqft": area,
        "zoning_code_raw": record.zoning_code_raw,
        "status": status,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate real Hays County parcels via GIS API")
    parser.add_argument("--apns", required=True, help="Comma-separated list of APNs")
    args = parser.parse_args()

    apns = [a.strip() for a in args.apns.split(",") if a.strip()]
    adapter = ArcGISParcelAdapter(HAYS_CONFIG)

    header = f"{'APN':<15} {'Geometry':>8} {'Area (sqft)':>12} {'Zoning':>8}  Status"
    print(header)
    print("-" * len(header))

    ok_count = 0
    for apn in apns:
        r = validate_apn(adapter, apn)
        geometry_str = "YES" if r["geometry"] else "NO"
        area_str = f"{r['area_sqft']:>12,.0f}" if r["area_sqft"] else f"{'N/A':>12}"
        zoning_str = (r["zoning_code_raw"] or "N/A")[:8]
        print(f"{r['apn']:<15} {geometry_str:>8} {area_str} {zoning_str:>8}  {r['status']}")
        if r["status"] == "OK":
            ok_count += 1

    print(f"\n{ok_count}/{len(apns)} parcels OK")
    if ok_count < len(apns) * 0.8:
        print("WARNING: fewer than 80% of parcels passed validation.")
        sys.exit(1)


if __name__ == "__main__":
    main()
