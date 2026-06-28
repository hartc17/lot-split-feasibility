from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

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


def _classify_tier(num_lots: int, zoning: ZoningRulesInput) -> SubdivisionReviewTier:
    if num_lots <= zoning.minor_subdivision_threshold:
        return SubdivisionReviewTier.ADMINISTRATIVE_MINOR
    return SubdivisionReviewTier.PLANNING_COMMISSION_MAJOR


def run_flag_lot(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> list[ScenarioResult]:
    """
    Try a 2-lot flag lot split:
    - Front lot: W ft wide, D ft deep, road frontage W ft
    - Rear lot: L-shaped (access strip alongside front lot + full-width body behind)

    Geometry:
        parcel width: P_W = frontage_edge.length
        front lot width: W = P_W - flag_lot_min_access_strip_ft
        access strip width: S = flag_lot_min_access_strip_ft
        split depth: D = min_lot_area / W  (minimum viable front lot depth)

    Returns [] if:
        - allows_flag_lots is False
        - W < min_lot_width_ft
        - No valid D satisfies both lot area requirements
    """
    if not zoning.allows_flag_lots or zoning.flag_lot_min_access_strip_ft is None:
        return []

    parcel_width = parcel.frontage_edge.length
    access_strip_width = float(zoning.flag_lot_min_access_strip_ft)
    front_lot_width = parcel_width - access_strip_width

    if front_lot_width < zoning.min_lot_width_ft:
        return []

    coords = list(parcel.frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u_norm = (p2 - p1) / np.linalg.norm(p2 - p1)  # along frontage
    v = interior_normal(parcel.frontage_edge, parcel.boundary)  # into parcel

    parcel_depth = measure_frontage_width(parcel.boundary, v)

    # Minimum depth for the front lot to meet area requirement
    min_d = zoning.min_lot_area_sqft / front_lot_width
    # Maximum split depth: rear lot body (full-width) must also meet area requirement
    max_d = parcel_depth - (zoning.min_lot_area_sqft / parcel_width)

    if min_d > max_d or min_d >= parcel_depth:
        return []

    split_depth = min_d  # use minimum viable depth to maximise rear lot area

    # Build front lot polygon
    origin = np.array(coords[0])
    front_corners = [
        tuple(origin),
        tuple(origin + u_norm * front_lot_width),
        tuple(origin + u_norm * front_lot_width + v * split_depth),
        tuple(origin + v * split_depth),
    ]
    front_lot_approx = Polygon(front_corners)
    front_lot = parcel.boundary.intersection(front_lot_approx)
    rear_lot = parcel.boundary.difference(front_lot)

    if front_lot.is_empty or rear_lot.is_empty:
        return []

    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft
    rear_buildable_width = measure_frontage_width(rear_lot, u_norm)

    front_result = LotResult(
        geometry=front_lot,
        area_sqft=front_lot.area,
        frontage_ft=front_lot_width,
        buildable_width_ft=front_lot_width,
        buildable_depth_ft=split_depth,
        has_direct_frontage=True,
        meets_min_lot_size=front_lot.area >= zoning.min_lot_area_sqft,
        meets_min_frontage=front_lot_width >= min_road_frontage,
        has_buildable_envelope=has_buildable_envelope(front_lot, zoning, existing_structures),
    )

    rear_result = LotResult(
        geometry=rear_lot,
        area_sqft=rear_lot.area,
        frontage_ft=access_strip_width,
        buildable_width_ft=rear_buildable_width,
        buildable_depth_ft=parcel_depth - split_depth,
        has_direct_frontage=False,
        meets_min_lot_size=rear_lot.area >= zoning.min_lot_area_sqft,
        meets_min_frontage=access_strip_width >= zoning.flag_lot_min_access_strip_ft,
        has_buildable_envelope=has_buildable_envelope(rear_lot, zoning, existing_structures),
    )

    if not (front_result.meets_min_lot_size and front_result.meets_min_frontage
            and front_result.has_buildable_envelope):
        return []
    if not (rear_result.meets_min_lot_size and rear_result.meets_min_frontage
            and rear_result.has_buildable_envelope):
        return []

    scenario = ScenarioResult(
        lot_layout_type=LotLayoutType.FLAG_LOT,
        resulting_lots=[front_result, rear_result],
        num_resulting_lots=2,
        requires_variance=False,
        requires_rezone=False,
        requires_flag_lot_provision=True,
        subdivision_review_tier=_classify_tier(2, zoning),
    )
    return [scenario]
