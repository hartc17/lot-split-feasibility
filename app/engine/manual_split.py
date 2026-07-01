from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import split as shapely_split

from app.engine.geometry import (
    has_buildable_envelope,
    interior_normal,
    measure_frontage_width,
)
from app.engine.types import (
    ConstraintSeverity,
    ManualLotResult,
    ManualSplitResult,
    ParcelGeometryInput,
    RiskCategory,
    RiskFlag,
    ZoningRulesInput,
)

_SLIVER_SQFT = 10.0
_EXTEND_FT = 100_000.0  # extend split lines so they always cross the parcel boundary


def _extend_line(line: LineString) -> LineString:
    """Extend a LineString outward in both endpoint directions."""
    coords = list(line.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    direction = p2 - p1
    length = np.linalg.norm(direction)
    if length < 1e-10:
        return line
    u = direction / length
    return LineString([tuple(p1 - u * _EXTEND_FT), tuple(p2 + u * _EXTEND_FT)])


def _apply_split(polygons: list[Polygon], split_line: LineString) -> list[Polygon]:
    """Apply one split line to every polygon in the list; return all resulting pieces."""
    result: list[Polygon] = []
    extended = _extend_line(split_line)
    for poly in polygons:
        try:
            pieces = shapely_split(poly, extended)
        except Exception:
            result.append(poly)
            continue
        geoms = list(pieces.geoms) if hasattr(pieces, "geoms") else [pieces]
        for g in geoms:
            if isinstance(g, MultiPolygon):
                result.extend(p for p in g.geoms if p.area >= _SLIVER_SQFT)
            elif isinstance(g, Polygon) and g.area >= _SLIVER_SQFT:
                result.append(g)
    return result or polygons


def _frontage_length(lot: Polygon, frontage_edge: LineString) -> float:
    """Length of the lot boundary that coincides with the frontage edge (in feet)."""
    intersection = lot.exterior.intersection(frontage_edge.buffer(0.5))
    if intersection.is_empty:
        return 0.0
    if hasattr(intersection, "geoms"):
        return sum(float(g.length) for g in intersection.geoms)
    return float(intersection.length)


def evaluate_manual_split(
    parcel: ParcelGeometryInput,
    split_lines: list[LineString],
    zoning: ZoningRulesInput,
) -> ManualSplitResult:
    """Evaluate user-defined split lines against zoning rules.

    split_lines must be in the same projected CRS as parcel.boundary (US survey feet).
    Returns per-lot compliance data and overall viability flags.
    """
    polygons: list[Polygon] = [parcel.boundary]
    for line in split_lines:
        polygons = _apply_split(polygons, line)

    coords = list(parcel.frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u_norm = (p2 - p1) / np.linalg.norm(p2 - p1)
    depth_dir = interior_normal(parcel.frontage_edge, parcel.boundary)

    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft

    lots: list[ManualLotResult] = []
    for poly in polygons:
        area = poly.area
        frontage_ft = _frontage_length(poly, parcel.frontage_edge)
        width = float(measure_frontage_width(poly, u_norm))
        depth = float(measure_frontage_width(poly, depth_dir))
        has_frontage = frontage_ft > 0.5
        meets_frontage = (
            not zoning.requires_public_road_frontage
            or frontage_ft >= min_road_frontage
        )
        lots.append(
            ManualLotResult(
                geometry=poly,
                area_sqft=area,
                area_acres=area / 43560.0,
                frontage_ft=frontage_ft,
                buildable_width_ft=width,
                buildable_depth_ft=depth,
                has_direct_frontage=has_frontage,
                meets_min_lot_size=area >= zoning.min_lot_area_sqft,
                meets_min_frontage=meets_frontage,
                has_buildable_envelope=has_buildable_envelope(poly, zoning, []),
            )
        )

    flags: list[RiskFlag] = []
    if any(not lot.meets_min_lot_size for lot in lots):
        flags.append(
            RiskFlag(
                category=RiskCategory.ZONING_AREA_SHORTFALL,
                severity=ConstraintSeverity.SIGNIFICANT,
                message="One or more sections fall below the minimum lot area.",
            )
        )
    if any(lot.has_direct_frontage and not lot.meets_min_frontage for lot in lots):
        flags.append(
            RiskFlag(
                category=RiskCategory.ZONING_FRONTAGE_SHORTFALL,
                severity=ConstraintSeverity.SIGNIFICANT,
                message="One or more sections have insufficient road frontage.",
            )
        )
    if any(not lot.has_direct_frontage for lot in lots):
        flags.append(
            RiskFlag(
                category=RiskCategory.INSUFFICIENT_ROAD_ACCESS,
                severity=ConstraintSeverity.SIGNIFICANT,
                message="One or more sections have no direct road frontage.",
            )
        )

    all_viable = all(
        lot.meets_min_lot_size and lot.meets_min_frontage and lot.has_buildable_envelope
        for lot in lots
    )
    return ManualSplitResult(lots=lots, all_lots_viable=all_viable, flags=flags)
