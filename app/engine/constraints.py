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


def apply_constraints(
    scenarios: list[ScenarioResult],
    constraints: list[ConstraintInput],
) -> list[ScenarioResult]:
    """
    Filter and annotate scenarios based on environmental constraints.

    - BLOCKING constraint covering >= 50% of any lot's area → remove that scenario entirely
    - SIGNIFICANT constraint intersecting any lot → keep scenario, add risk flag
    - MINOR/INFORMATIONAL → add risk flag only (lower severity)
    """
    if not constraints:
        return scenarios

    surviving = []
    for scenario in scenarios:
        eliminated = False
        extra_flags: list[RiskFlag] = []

        for constraint in constraints:
            if eliminated:
                break
            for lot in scenario.resulting_lots:
                overlap = lot.geometry.intersection(constraint.geometry)
                if overlap.is_empty:
                    continue

                coverage = overlap.area / lot.geometry.area

                if (constraint.severity == ConstraintSeverity.BLOCKING
                        and coverage >= _BLOCKING_COVERAGE_THRESHOLD):
                    eliminated = True
                    break

                risk_cat = _CONSTRAINT_TO_RISK_CATEGORY.get(
                    constraint.constraint_type, RiskCategory.DATA_GAP
                )
                extra_flags.append(RiskFlag(
                    category=risk_cat,
                    severity=constraint.severity,
                    message=(
                        f"{constraint.constraint_type.value} covers "
                        f"{coverage:.0%} of one resulting lot."
                    ),
                ))

        if not eliminated:
            scenario.risk_flags.extend(extra_flags)
            surviving.append(scenario)

    return surviving
