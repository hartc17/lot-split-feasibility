"""
Fetch real Kyle, TX parcels from Hays County GIS and save as individual
GeoJSON files ready to upload to the lot-split feasibility UI.

Usage:
    python scripts/fetch_kyle_parcels.py [--count 20] [--out data/kyle_parcels]

Each parcel is saved as <PROP_ID>.geojson — a bare GeoJSON Polygon (the
format the UI's /v1/parse/geojson endpoint accepts directly).

Area filter: 10,000–60,000 sqft.  This range targets parcels large enough
to split under R-1-2/R-1-3 rules (min 6,825 / 5,540 sqft per resulting
lot) while small enough to be realistic single-family candidates.
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from shapely.geometry import shape
from shapely.ops import transform
import pyproj

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

FEATURE_SERVER = (
    "https://gis.urbaneng.com/arcgis/rest/services/HaysCountyParcels/FeatureServer/0"
)

# Approximate bounding box for the City of Kyle, TX (WGS84)
KYLE_BBOX = {
    "xmin": -97.925,
    "ymin": 29.970,
    "xmax": -97.840,
    "ymax": 30.045,
    "spatialReference": {"wkid": 4326},
}

MIN_SQFT = 10_000
MAX_SQFT = 60_000


def area_sqft(geojson_geom: dict) -> float:
    geom = shape(geojson_geom)
    wgs84 = pyproj.CRS("EPSG:4326")
    # Auto-UTM projection centered on Kyle (zone 14N)
    utm = pyproj.CRS("EPSG:32614")
    project = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
    projected = transform(project, geom)
    return projected.area * 10.7639  # m² → sqft


def fetch_parcels(count: int) -> list[dict]:
    params = {
        "where": "1=1",
        "geometry": json.dumps(KYLE_BBOX),
        "geometryType": "esriGeometryEnvelope",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "*",
        "returnGeometry": "true",
        "f": "geojson",
        "resultRecordCount": min(count * 5, 200),  # over-fetch; filter by area below
    }
    resp = requests.get(f"{FEATURE_SERVER}/query", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features", [])
    if not features:
        print("No features returned. The endpoint may have changed — check the URL.")
        sys.exit(1)
    return features


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Kyle, TX parcels for manual UI testing")
    parser.add_argument("--count", type=int, default=20, help="Number of parcels to save")
    parser.add_argument("--out", default="data/kyle_parcels", help="Output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"Querying Hays County GIS (Kyle bbox)…")
    features = fetch_parcels(args.count)
    print(f"  {len(features)} raw features returned")

    saved = 0
    skipped_area = 0
    skipped_geom = 0

    print(f"\n{'PROP_ID':<16} {'Area (sqft)':>12}  {'Class':<12}  File")
    print("-" * 60)

    for feat in features:
        if saved >= args.count:
            break

        props = feat.get("properties") or feat.get("attributes") or {}
        geom = feat.get("geometry")
        if not geom:
            skipped_geom += 1
            continue

        prop_id = str(props.get("PROP_ID") or props.get("OBJECTID") or "unknown")
        klass = str(props.get("Class") or "")

        try:
            sqft = area_sqft(geom)
        except Exception:
            skipped_geom += 1
            continue

        if not (MIN_SQFT <= sqft <= MAX_SQFT):
            skipped_area += 1
            continue

        # Save as a bare Polygon GeoJSON (what the UI accepts)
        out = {
            "type": "Feature",
            "properties": {"PROP_ID": prop_id, "Class": klass, "area_sqft": round(sqft)},
            "geometry": geom,
        }
        filename = out_dir / f"{prop_id}.geojson"
        filename.write_text(json.dumps(out, indent=2))

        print(f"{prop_id:<16} {sqft:>12,.0f}  {klass:<12}  {filename.name}")
        saved += 1

    print(f"\nSaved {saved} parcels to {out_dir}/")
    print(f"Skipped {skipped_area} (outside area range) + {skipped_geom} (bad geometry)")
    if saved == 0:
        print("\nNo parcels matched the area filter. Try widening MIN_SQFT/MAX_SQFT or the bbox.")


if __name__ == "__main__":
    main()
