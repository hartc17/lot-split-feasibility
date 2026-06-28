from __future__ import annotations

from app.engine.constraints import apply_constraints
from app.engine.eligibility import check_eligibility
from app.engine.strategies.flag_lot import run_flag_lot
from app.engine.strategies.simple_halve import run_frontage_strip
from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ParcelGeometryInput,
    RiskCategory,
    RiskFlag,
    ScenarioResult,
    StructureInput,
    SubdivisionFeasibilityResult,
    ZoningRulesInput,
)


def _max_theoretical_lots(parcel: ParcelGeometryInput, zoning: ZoningRulesInput) -> int:
    area = parcel.boundary.area
    by_area = int(area // zoning.min_lot_area_sqft)
    if zoning.max_density_units_per_acre:
        acres = area / 43_560.0
        by_density = int(acres * zoning.max_density_units_per_acre)
        return min(by_area, by_density)
    return by_area


def _rank_scenarios(scenarios: list[ScenarioResult]) -> list[ScenarioResult]:
    """Rank: fewer variances first, simpler process first, fewer risk flags first."""
    return sorted(
        scenarios,
        key=lambda s: (
            s.requires_variance,
            s.requires_rezone,
            s.requires_flag_lot_provision,
            len(s.risk_flags),
            s.num_resulting_lots,
        ),
    )


def _check_flag_lot_would_help(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    flags: list[RiskFlag],
) -> None:
    """
    If a flag lot split would be geometrically plausible but flag lots aren't allowed,
    append a REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED flag. Mutates flags in place.
    """
    frontage = parcel.frontage_edge.length
    if frontage < 2 * zoning.min_lot_width_ft:
        flags.append(RiskFlag(
            category=RiskCategory.REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED,
            severity=ConstraintSeverity.BLOCKING,
            message=(
                f"This parcel's frontage ({frontage:.0f} ft) is too narrow for a "
                f"side-by-side split (requires {2 * zoning.min_lot_width_ft:.0f} ft). "
                "A flag lot arrangement could provide access to a rear lot, but flag "
                "lots are not permitted in this zoning district as-of-right."
            ),
        ))


def calculate_subdivision_scenarios(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    constraints: list[ConstraintInput],
    existing_structures: list[StructureInput],
) -> SubdivisionFeasibilityResult:
    """
    Core feasibility engine. Pure function — no I/O, no DB access.
    All inputs must be pre-populated by the calling adapter/orchestration layer.
    """
    # Step 1: Eligibility gate
    disqualifying_flags = check_eligibility(parcel, zoning, existing_structures)

    # DATA_GAP or MULTI_DISTRICT: can't proceed
    if any(
        f.category in (RiskCategory.DATA_GAP, RiskCategory.MULTI_DISTRICT_PARCEL)
        for f in disqualifying_flags
    ):
        return SubdivisionFeasibilityResult(
            max_theoretical_lots=0,
            scenarios=[],
            disqualifying_flags=disqualifying_flags,
            data_gap=any(f.category == RiskCategory.DATA_GAP for f in disqualifying_flags),
        )

    # Area shortfall or structure conflict: surface flags, no scenarios
    if disqualifying_flags:
        max_lots = _max_theoretical_lots(parcel, zoning)
        if not zoning.allows_flag_lots:
            _check_flag_lot_would_help(parcel, zoning, disqualifying_flags)
        return SubdivisionFeasibilityResult(
            max_theoretical_lots=max_lots,
            scenarios=[],
            disqualifying_flags=disqualifying_flags,
            data_gap=False,
        )

    # Step 2: Max theoretical lots
    max_lots = _max_theoretical_lots(parcel, zoning)

    # Step 3: Generate candidate scenarios
    scenarios: list[ScenarioResult] = []
    scenarios.extend(run_frontage_strip(parcel, zoning, existing_structures))
    if zoning.allows_flag_lots:
        scenarios.extend(run_flag_lot(parcel, zoning, existing_structures))

    # If nothing found and flag lots aren't allowed, check if they would have helped
    if not scenarios and not zoning.allows_flag_lots:
        extra_flags: list[RiskFlag] = []
        _check_flag_lot_would_help(parcel, zoning, extra_flags)
        disqualifying_flags.extend(extra_flags)

    # Step 4: Apply environmental constraints
    scenarios = apply_constraints(scenarios, constraints)

    # Step 6: Rank
    scenarios = _rank_scenarios(scenarios)

    return SubdivisionFeasibilityResult(
        max_theoretical_lots=max_lots,
        scenarios=scenarios,
        disqualifying_flags=disqualifying_flags,
        data_gap=False,
    )
