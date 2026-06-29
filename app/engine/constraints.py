from __future__ import annotations

from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ConstraintType,
    RiskCategory,
    RiskFlag,
    ScenarioResult,
)

# Fraction of a lot's area that a BLOCKING constraint must cover to invalidate the scenario.
_BLOCKING_COVERAGE_THRESHOLD = 0.50

_CONSTRAINT_TO_RISK_CATEGORY = {
    ConstraintType.FLOOD_ZONE: RiskCategory.FLOOD_ZONE_EXPOSURE,
    ConstraintType.WETLAND: RiskCategory.WETLAND_EXPOSURE,
    ConstraintType.STEEP_SLOPE: RiskCategory.STEEP_SLOPE,
    ConstraintType.SOIL_LIMITATION: RiskCategory.SEPTIC_SUITABILITY_UNKNOWN_OR_POOR,
}


def _lot_constraint_flags(
    lot_geometry,
    constraint: ConstraintInput,
) -> tuple[bool, RiskFlag | None]:
    """
    Evaluate one constraint against one lot.

    Returns (eliminated, flag_or_None). eliminated=True means the scenario
    should be discarded; flag_or_None is a non-blocking risk flag to attach.
    """
    overlap = lot_geometry.intersection(constraint.geometry)
    if overlap.is_empty:
        return False, None

    coverage = overlap.area / lot_geometry.area

    if (
        constraint.severity == ConstraintSeverity.BLOCKING
        and coverage >= _BLOCKING_COVERAGE_THRESHOLD
    ):
        return True, None

    risk_cat = _CONSTRAINT_TO_RISK_CATEGORY.get(constraint.constraint_type, RiskCategory.DATA_GAP)
    flag = RiskFlag(
        category=risk_cat,
        severity=constraint.severity,
        message=(f"{constraint.constraint_type.value} covers {coverage:.0%} of one resulting lot."),
    )
    return False, flag


def _evaluate_scenario(
    scenario: ScenarioResult,
    constraints: list[ConstraintInput],
) -> tuple[bool, list[RiskFlag]]:
    """
    Check all constraints against all lots in one scenario.

    Returns (eliminated, extra_flags). If eliminated, extra_flags is empty.
    """
    extra_flags: list[RiskFlag] = []
    for constraint in constraints:
        for lot in scenario.resulting_lots:
            eliminated, flag = _lot_constraint_flags(lot.geometry, constraint)
            if eliminated:
                return True, []
            if flag is not None:
                extra_flags.append(flag)
    return False, extra_flags


def apply_constraints(
    scenarios: list[ScenarioResult],
    constraints: list[ConstraintInput],
) -> list[ScenarioResult]:
    if not constraints:
        return scenarios

    surviving = []
    for scenario in scenarios:
        eliminated, extra_flags = _evaluate_scenario(scenario, constraints)
        if not eliminated:
            scenario.risk_flags.extend(extra_flags)
            surviving.append(scenario)
    return surviving
