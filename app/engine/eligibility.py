from __future__ import annotations

import numpy as np

from app.engine.types import (
    ConstraintSeverity,
    ParcelGeometryInput,
    RiskCategory,
    RiskFlag,
    StructureInput,
    ZoningRulesInput,
)


def _structure_requires_lot_line_setback(
    structure: StructureInput,
    parcel_width: float,
    side_setback_ft: float,
    min_lot_width_ft: float,
) -> bool:
    """
    Return True if no valid SIMPLE_HALVE split position satisfies both the side-setback
    requirement for the existing structure AND the minimum lot width for both resulting lots.

    A split at x=t is constrained to [min_lot_width, parcel_width - min_lot_width].
    Within that range, t must be either:
      >= struct_right + side_setback  (structure stays in left lot with clearance), OR
      <= struct_left  - side_setback  (structure stays in right lot with clearance).
    If neither condition can be satisfied in the valid t range, it's a blocking conflict.
    """
    coords = np.array(structure.footprint.exterior.coords)
    struct_left = float(coords[:, 0].min())
    struct_right = float(coords[:, 0].max())

    # Valid range of split positions (both lots must meet min width)
    min_t = min_lot_width_ft
    max_t = parcel_width - min_lot_width_ft

    if min_t > max_t:
        return True  # parcel too narrow for any split regardless

    t_for_left = struct_right + side_setback_ft  # split must be >= this for house in left lot
    t_for_right = struct_left - side_setback_ft  # split must be <= this for house in right lot

    can_put_house_in_left = t_for_left <= max_t  # some t >= t_for_left exists in [min_t, max_t]
    can_put_house_in_right = t_for_right >= min_t  # some t <= t_for_right exists in [min_t, max_t]

    return not (can_put_house_in_left or can_put_house_in_right)


def check_eligibility(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> list[RiskFlag]:
    """
    Run fast-fail eligibility checks. Returns a list of disqualifying RiskFlags.
    An empty list means the parcel passed all checks.
    """
    flags: list[RiskFlag] = []

    # 1. Parcel straddles two zoning districts
    if parcel.multi_district:
        flags.append(
            RiskFlag(
                category=RiskCategory.MULTI_DISTRICT_PARCEL,
                severity=ConstraintSeverity.BLOCKING,
                message=(
                    "This parcel appears to straddle two zoning districts. "
                    "Automated analysis cannot determine which district's rules apply. "
                    "Manual review by a land-use professional is required."
                ),
            )
        )
        return flags

    # 3. Area too small for any 2-lot split
    parcel_area = parcel.boundary.area
    required_area = 2 * zoning.min_lot_area_sqft
    if parcel_area < required_area:
        flags.append(
            RiskFlag(
                category=RiskCategory.ZONING_AREA_SHORTFALL,
                severity=ConstraintSeverity.BLOCKING,
                message=(
                    f"A 2-lot split requires at least {required_area:,.0f} sqft "
                    f"(2 × {zoning.min_lot_area_sqft:,.0f} sqft minimum lot size). "
                    f"This parcel is {parcel_area:,.0f} sqft — "
                    f"{required_area - parcel_area:,.0f} sqft short. "
                    "A variance would be required for any subdivision."
                ),
            )
        )

    # 4. Existing structure positioned to block any valid split along the frontage axis
    parcel_width = parcel.frontage_edge.length
    for structure in existing_structures:
        if parcel.boundary.intersects(structure.footprint):
            if _structure_requires_lot_line_setback(
                structure, parcel_width, zoning.setback_side_ft, zoning.min_lot_width_ft
            ):
                flags.append(
                    RiskFlag(
                        category=RiskCategory.EXISTING_STRUCTURE_CONFLICT,
                        severity=ConstraintSeverity.BLOCKING,
                        message=(
                            "An existing structure is positioned such that no lot split line "
                            "can satisfy the required side setback on both resulting lots without "
                            "requiring removal or relocation of the structure."
                        ),
                    )
                )

    return flags
