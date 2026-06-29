import io

from shapely.geometry import Polygon
from shapely.geometry import mapping as shapely_mapping
from shapely.geometry import shape as shapely_shape


def parse_kml(kml_bytes: bytes) -> Polygon:
    """Parse KML bytes (Google Maps/Earth export).
    Returns the first Placemark polygon found."""
    try:
        from fastkml import KML
    except ImportError as exc:
        raise ImportError("fastkml is required for KML parsing") from exc

    if not kml_bytes:
        raise ValueError("KML input is empty")

    try:
        k = KML.parse(io.BytesIO(kml_bytes))
    except Exception as exc:
        raise ValueError(f"Could not parse KML: {exc}") from exc

    polygon = _find_polygon(k.features)
    if polygon is None:
        raise ValueError("No polygon geometry found in KML document")
    return polygon


def _find_polygon(features):
    for feature in features:
        # Placemark: geometry is on kml_geometry.geometry
        kml_geom = getattr(feature, "kml_geometry", None)
        if kml_geom is not None:
            raw_geom = getattr(kml_geom, "geometry", None)
            if raw_geom is not None:
                # fastkml returns pygeoif geometry; convert to Shapely via GeoJSON round-trip
                geom = shapely_shape(shapely_mapping(raw_geom))
                # Drop Z coordinate so projection works cleanly
                if geom.has_z:
                    from shapely.ops import transform as shp_transform

                    geom = shp_transform(lambda x, y, z=None: (x, y), geom)
                if geom.geom_type == "Polygon":
                    return geom
                if geom.geom_type == "MultiPolygon":
                    return max(geom.geoms, key=lambda g: g.area)
        # Document / Folder: recurse into nested features
        sub = getattr(feature, "features", [])
        if sub:
            result = _find_polygon(sub)
            if result is not None:
                return result
    return None
