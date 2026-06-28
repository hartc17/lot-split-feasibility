from shapely.geometry import LineString, Polygon

from app.engine.types import ParcelGeometryInput, ZoningRulesInput
from app.parsers.projection import get_utm_epsg, project_to_feet


def extract_edge(polygon: Polygon, edge_index: int) -> LineString:
    """Return the nth exterior edge of the polygon as a LineString (0-indexed).
    Raises ValueError if edge_index is out of range."""
    coords = list(polygon.exterior.coords)
    num_edges = len(coords) - 1  # last coord == first coord (closed ring)
    if not (0 <= edge_index < num_edges):
        raise ValueError(
            f"edge_index {edge_index} is out of range for a polygon with {num_edges} edges"
        )
    return LineString([coords[edge_index], coords[edge_index + 1]])


def build_parcel_geometry_input(
    polygon_4326: Polygon,
    frontage_edge_index: int,
    zoning_district_code: str | None = None,
) -> ParcelGeometryInput:
    """Project WGS84 polygon to feet, extract the user-selected edge as frontage_edge,
    and return a ParcelGeometryInput ready for calculate_subdivision_scenarios()."""
    lon, lat = polygon_4326.centroid.x, polygon_4326.centroid.y
    utm_epsg = get_utm_epsg(lon, lat)

    poly_ft = project_to_feet(polygon_4326)
    frontage_edge = extract_edge(poly_ft, frontage_edge_index)

    return ParcelGeometryInput(
        boundary=poly_ft,
        frontage_edge=frontage_edge,
        zoning_district_code=zoning_district_code,
    )


def build_zoning_rules_input(data: dict) -> ZoningRulesInput:
    """Construct ZoningRulesInput from a user-submitted dict.
    Raises ValueError if required fields are missing or non-positive."""
    required = [
        "min_lot_area_sqft",
        "min_lot_width_ft",
        "setback_front_ft",
        "setback_side_ft",
        "setback_rear_ft",
        "minor_subdivision_threshold",
    ]
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"Missing required zoning fields: {missing}")

    non_positive = [k for k in required if data.get(k, 0) <= 0]
    if non_positive:
        raise ValueError(f"Zoning fields must be positive: {non_positive}")

    return ZoningRulesInput(
        min_lot_area_sqft=int(data["min_lot_area_sqft"]),
        min_lot_width_ft=int(data["min_lot_width_ft"]),
        setback_front_ft=int(data["setback_front_ft"]),
        setback_side_ft=int(data["setback_side_ft"]),
        setback_rear_ft=int(data["setback_rear_ft"]),
        requires_public_road_frontage=bool(data.get("requires_public_road_frontage", True)),
        allows_flag_lots=bool(data.get("allows_flag_lots", False)),
        minor_subdivision_threshold=int(data["minor_subdivision_threshold"]),
        flag_lot_min_access_strip_ft=data.get("flag_lot_min_access_strip_ft"),
    )
