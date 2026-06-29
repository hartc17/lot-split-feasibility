from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.engine.types import (
    RiskCategory,
    SubdivisionFeasibilityResult,
    SubdivisionReviewTier,
)


class Recommendation(StrEnum):
    PURSUE = "PURSUE"
    PURSUE_WITH_CAUTION = "PURSUE_WITH_CAUTION"
    UNLIKELY = "UNLIKELY"
    NOT_FEASIBLE = "NOT_FEASIBLE"


@dataclass
class SubScore:
    score: int  # 0–100
    weight: float  # contribution weight (sums to 1.0 across all sub-scores)
    explanation: str  # one sentence shown in the report


@dataclass
class FeasibilityScore:
    overall: int
    recommendation: Recommendation
    sub_scores: dict[str, SubScore]


# ── Weights ────────────────────────────────────────────────────────────────────
_W_ZONING = 0.35
_W_BUILDABILITY = 0.25
_W_ACCESS = 0.15
_W_PROCESS = 0.10
_W_FINANCIAL = 0.15  # deferred until comps data is available


def score_result(result: SubdivisionFeasibilityResult) -> FeasibilityScore:
    zoning_s, zoning_exp = _zoning_score(result)
    buildability_s, build_exp = _buildability_score(result)
    access_s, access_exp = _access_score(result)
    process_s, process_exp = _process_score(result)
    financial_s, financial_exp = _financial_score()

    overall = round(
        zoning_s * _W_ZONING
        + buildability_s * _W_BUILDABILITY
        + access_s * _W_ACCESS
        + process_s * _W_PROCESS
        + financial_s * _W_FINANCIAL,
    )

    recommendation = _recommend(result, overall)

    return FeasibilityScore(
        overall=overall,
        recommendation=recommendation,
        sub_scores={
            "zoning_compliance": SubScore(zoning_s, _W_ZONING, zoning_exp),
            "physical_buildability": SubScore(buildability_s, _W_BUILDABILITY, build_exp),
            "access_utility": SubScore(access_s, _W_ACCESS, access_exp),
            "process_complexity": SubScore(process_s, _W_PROCESS, process_exp),
            "financial_upside": SubScore(financial_s, _W_FINANCIAL, financial_exp),
        },
    )


# ── Sub-score functions ────────────────────────────────────────────────────────


def _zoning_score(result: SubdivisionFeasibilityResult) -> tuple[int, str]:
    if result.data_gap:
        return 0, "Zoning district not identified — cannot evaluate dimensional compliance."

    disq = _flag_categories(result.disqualifying_flags)

    if RiskCategory.ZONING_AREA_SHORTFALL in disq:
        return 5, "Parcel area is too small to split without a variance — disqualifying shortfall."

    if not result.scenarios:
        return 10, "No viable split configurations found under current zoning rules."

    primary = result.scenarios[0]
    score = 100
    reasons: list[str] = []

    if primary.requires_rezone:
        score -= 50
        reasons.append("rezone required")
    if primary.requires_variance:
        score -= 30
        reasons.append("variance required")
    if primary.requires_flag_lot_provision:
        score -= 15
        reasons.append("flag lot provision needed")

    score = max(0, score)
    if reasons:
        return score, f"Primary scenario requires: {', '.join(reasons)}."
    return score, "Primary scenario meets all dimensional standards as-of-right."


def _buildability_score(result: SubdivisionFeasibilityResult) -> tuple[int, str]:
    if result.data_gap:
        return 50, "Environmental constraint data unavailable — score is neutral pending review."

    all_flags = list(result.disqualifying_flags)
    for s in result.scenarios:
        all_flags.extend(s.risk_flags)
    cats = _flag_categories(all_flags)

    score = 100
    reasons: list[str] = []

    if RiskCategory.FLOOD_ZONE_EXPOSURE in cats:
        score -= 40
        reasons.append("flood zone exposure")
    if RiskCategory.WETLAND_EXPOSURE in cats:
        score -= 30
        reasons.append("wetland exposure")
    if RiskCategory.STEEP_SLOPE in cats:
        score -= 20
        reasons.append("steep slope")
    if RiskCategory.EXISTING_STRUCTURE_CONFLICT in cats:
        score -= 30
        reasons.append("existing structure conflict")

    score = max(0, score)
    if reasons:
        return score, f"Physical flags: {', '.join(reasons)}."
    return score, "No physical buildability constraints detected."


def _access_score(result: SubdivisionFeasibilityResult) -> tuple[int, str]:
    all_flags = list(result.disqualifying_flags)
    for s in result.scenarios:
        all_flags.extend(s.risk_flags)
    cats = _flag_categories(all_flags)

    score = 100
    reasons: list[str] = []

    if RiskCategory.INSUFFICIENT_ROAD_ACCESS in cats:
        score -= 50
        reasons.append("insufficient road access")
    if RiskCategory.NO_PUBLIC_SEWER_ACCESS in cats:
        score -= 20
        reasons.append("no public sewer access")
    if RiskCategory.SEPTIC_SUITABILITY_UNKNOWN_OR_POOR in cats:
        score -= 15
        reasons.append("septic suitability unknown or poor")

    # Flag-lot-only path is a mild access concern
    if result.scenarios and all(s.requires_flag_lot_provision for s in result.scenarios):
        score -= 10
        reasons.append("flag lot access only")

    score = max(0, score)
    if reasons:
        return score, f"Access concerns: {', '.join(reasons)}."
    return score, "Public road access confirmed for all resulting lots."


def _process_score(result: SubdivisionFeasibilityResult) -> tuple[int, str]:
    if not result.scenarios:
        return 0, "No viable scenarios — process tier cannot be determined."

    primary = result.scenarios[0]
    if primary.subdivision_review_tier == SubdivisionReviewTier.ADMINISTRATIVE_MINOR:
        return (
            100,
            "Qualifies for administrative minor subdivision — no planning commission or public hearing required.",
        )
    return 50, "Requires planning commission review — public hearing and longer approval timeline."


def _financial_score() -> tuple[int, str]:
    # Deferred until Phase 8 comps/valuation data is available.
    return 50, "Financial analysis pending — comparable sales data not yet integrated."


# ── Recommendation ─────────────────────────────────────────────────────────────


def _recommend(result: SubdivisionFeasibilityResult, overall: int) -> Recommendation:
    if result.data_gap:
        return Recommendation.UNLIKELY

    has_disqualifying = bool(result.disqualifying_flags)

    if has_disqualifying or not result.scenarios or overall < 30:
        return Recommendation.NOT_FEASIBLE
    if overall >= 70:
        return Recommendation.PURSUE
    if overall >= 50:
        return Recommendation.PURSUE_WITH_CAUTION
    return Recommendation.UNLIKELY


# ── Helpers ────────────────────────────────────────────────────────────────────


def _flag_categories(flags) -> set[RiskCategory]:
    return {f.category for f in flags}
