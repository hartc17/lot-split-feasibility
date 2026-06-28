from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.ops import split as shapely_split

from app.engine.geometry import (
    has_buildable_envelope,
    interior_normal,
    measure_frontage_width,
)
from app.engine.types import (
    LotLayoutType,
    LotResult,
    ParcelGeometryInput,
    ScenarioResult,
    StructureInput,
    SubdivisionReviewTier,
    ZoningRulesInput,
)


def _make_perpendicular_cut(
    frontage_edge: LineString,
    offset_along_frontage: float,
    extent: float = 50_000.0,
) -> LineString:
    """Cut line perpendicular to frontage at offset_along_frontage from the start."""
    split_pt = frontage_edge.interpolate(offset_along_frontage)
    coords = list(frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u = p2 - p1
    u_norm = u / np.linalg.norm(u)
    perp = np.array([-u_norm[1], u_norm[0]])

    start = (split_pt.x - perp[0] * extent, split_pt.y - perp[1] * extent)
    end = (split_pt.x + perp[0] * extent, split_pt.y + perp[1] * extent)
    return LineString([start, end])


def _structure_blocks_split_at(
    t: float,
    existing_structures: list[StructureInput],
    side_setback: float,
    min_lot_width: float,
) -> bool:
    """Return True if any structure prevents a clean split at x=t (after setback check)."""
    for structure in existing_structures:
        coords = np.array(structure.footprint.exterior.coords)
        struct_left = coords[:, 0].min()
        struct_right = coords[:, 0].max()
        # Structure must be entirely left (right edge + setback <= t)
        # or entirely right (left edge - setback >= t)
        in_left = struct_right + side_setback <= t
        in_right = struct_left - side_setback >= t
        if not (in_left or in_right):
            return True
    return False


def _build_lot_result(
    lot: Polygon,
    frontage_edge: LineString,
    parcel: Polygon,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> LotResult:
    coords = list(frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u_norm = (p2 - p1) / np.linalg.norm(p2 - p1)
    v = interior_normal(frontage_edge, parcel)

    area = lot.area
    frontage_w = measure_frontage_width(lot, u_norm)
    depth = measure_frontage_width(lot, v)

    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft

    return LotResult(
        geometry=lot,
        area_sqft=area,
        frontage_ft=frontage_w,
        buildable_width_ft=frontage_w,
        buildable_depth_ft=depth,
        has_direct_frontage=True,
        meets_min_lot_size=area >= zoning.min_lot_area_sqft,
        meets_min_frontage=frontage_w >= min_road_frontage,
        has_buildable_envelope=has_buildable_envelope(lot, zoning, existing_structures),
    )


def _classify_tier(num_lots: int, zoning: ZoningRulesInput) -> SubdivisionReviewTier:
    if num_lots <= zoning.minor_subdivision_threshold:
        return SubdivisionReviewTier.ADMINISTRATIVE_MINOR
    return SubdivisionReviewTier.PLANNING_COMMISSION_MAJOR


def _try_n_strip_split(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
    n_lots: int,
    layout_type: LotLayoutType,
) -> ScenarioResult | None:
    """
    Try splitting the parcel into n_lots equal-width strips perpendicular to frontage.
    Returns None if no valid configuration exists.
    """
    frontage_length = parcel.frontage_edge.length
    strip_width = frontage_length / n_lots
    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft

    if strip_width < min_road_frontage or strip_width < zoning.min_lot_width_ft:
        return None

    cut_positions = [strip_width * i for i in range(1, n_lots)]
    remaining = parcel.boundary
    lot_polys: list[Polygon] = []

    for cut_pos in cut_positions:
        if remaining.is_empty:
            break
        if _structure_blocks_split_at(
            cut_pos, existing_structures, zoning.setback_side_ft, zoning.min_lot_width_ft
        ):
            return None
        cut_line = _make_perpendicular_cut(parcel.frontage_edge, cut_pos)
        try:
            result = shapely_split(remaining, cut_line)
        except Exception:
            return None

        geoms = list(result.geoms) if hasattr(result, "geoms") else [result]
        if len(geoms) < 2:
            return None

        geoms.sort(key=lambda g: g.centroid.x)
        lot_polys.append(geoms[0])
        remaining = geoms[-1]

    lot_polys.append(remaining)

    if len(lot_polys) != n_lots:
        return None

    lot_results = [
        _build_lot_result(lot, parcel.frontage_edge, parcel.boundary, zoning, existing_structures)
        for lot in lot_polys
    ]

    if not all(
        lr.meets_min_lot_size and lr.meets_min_frontage and lr.has_buildable_envelope
        for lr in lot_results
    ):
        return None

    return ScenarioResult(
        lot_layout_type=layout_type,
        resulting_lots=lot_results,
        num_resulting_lots=n_lots,
        requires_variance=False,
        requires_rezone=False,
        requires_flag_lot_provision=False,
        subdivision_review_tier=_classify_tier(n_lots, zoning),
    )


def run_simple_halve(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> list[ScenarioResult]:
    """Try a 2-lot side-by-side split. Returns 0 or 1 ScenarioResult."""
    result = _try_n_strip_split(parcel, zoning, existing_structures, 2, LotLayoutType.SIMPLE_HALVE)
    return [result] if result else []


def run_frontage_strip(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
    max_lots: int = 6,
) -> list[ScenarioResult]:
    """Try 2, 3, 4, ... N-lot equal-width strip splits. Returns all valid scenarios."""
    results = []
    for n in range(2, max_lots + 1):
        scenario = _try_n_strip_split(
            parcel, zoning, existing_structures, n,
            LotLayoutType.SIMPLE_HALVE if n == 2 else LotLayoutType.FRONTAGE_STRIP,
        )
        if scenario:
            results.append(scenario)
        else:
            break  # If N lots fails, N+1 will also fail (strips get narrower)
    return results
