from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, Point, Polygon

from app.engine.types import StructureInput, ZoningRulesInput


def interior_normal(frontage_edge: LineString, parcel: Polygon) -> np.ndarray:
    """Unit vector perpendicular to frontage_edge pointing into the parcel interior."""
    coords = list(frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u = p2 - p1
    u_norm = u / np.linalg.norm(u)
    v = np.array([-u_norm[1], u_norm[0]])  # 90 deg CCW rotation

    # Verify v points into parcel; flip if not
    mid = (p1 + p2) / 2
    test_pt = Point(mid + v * 1.0)
    if not parcel.contains(test_pt):
        v = -v

    return v


def measure_frontage_width(lot: Polygon, frontage_direction: np.ndarray) -> float:
    """Lot extent in the direction of the frontage (i.e., width along the road)."""
    coords = np.array(lot.exterior.coords[:-1])  # drop closing point
    projections = coords @ frontage_direction
    return float(projections.max() - projections.min())


def has_buildable_envelope(
    lot: Polygon,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
    min_house_footprint_sqft: float = 400.0,
) -> bool:
    """
    Return True if the lot has a buildable area >= min_house_footprint_sqft after
    applying a conservative uniform setback and removing existing structure exclusion zones.
    """
    min_setback = min(zoning.setback_front_ft, zoning.setback_side_ft, zoning.setback_rear_ft)
    buildable = lot.buffer(-min_setback)

    for structure in existing_structures:
        if lot.intersects(structure.footprint):
            exclusion = structure.footprint.buffer(min_setback)
            buildable = buildable.difference(exclusion)

    if buildable.is_empty:
        return False
    return buildable.area >= min_house_footprint_sqft
