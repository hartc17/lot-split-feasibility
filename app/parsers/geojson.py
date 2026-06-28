from shapely.geometry import Polygon, shape


def parse_geojson(data: dict) -> Polygon:
    """Accept a GeoJSON FeatureCollection, Feature, or bare Polygon geometry.
    Returns the first polygon found."""
    geom_dict = _extract_geometry(data)
    if geom_dict.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError(f"Expected Polygon geometry, got {geom_dict.get('type')!r}")
    geom = shape(geom_dict)
    if geom.geom_type == "MultiPolygon":
        # take the largest polygon from a multipolygon
        geom = max(geom.geoms, key=lambda g: g.area)
    if not isinstance(geom, Polygon):
        raise ValueError("Could not extract a Polygon from the provided GeoJSON")
    return geom


def _extract_geometry(data: dict) -> dict:
    t = data.get("type")
    if t == "FeatureCollection":
        features = data.get("features") or []
        if not features:
            raise ValueError("FeatureCollection contains no features")
        return _extract_geometry(features[0])
    if t == "Feature":
        geom = data.get("geometry")
        if not geom:
            raise ValueError("Feature has no geometry")
        return geom
    if t in ("Polygon", "MultiPolygon"):
        return data
    raise ValueError(f"Unrecognised GeoJSON type {t!r}")
