"""Tests for app/scoring/scoring.py — pure scoring logic, no DB or I/O."""

from __future__ import annotations

from app.engine.types import (
    ConstraintSeverity,
    LotLayoutType,
    RiskCategory,
    RiskFlag,
    ScenarioResult,
    SubdivisionFeasibilityResult,
    SubdivisionReviewTier,
)
from app.scoring.scoring import (
    FeasibilityScore,
    Recommendation,
    SubScore,
    _access_score,
    _buildability_score,
    _financial_score,
    _process_score,
    _recommend,
    _zoning_score,
    score_result,
)

# ── Factories ──────────────────────────────────────────────────────────────────


def _flag(category: RiskCategory) -> RiskFlag:
    return RiskFlag(category=category, severity=ConstraintSeverity.BLOCKING, message="test")


def _scenario(
    *,
    requires_variance: bool = False,
    requires_rezone: bool = False,
    requires_flag_lot_provision: bool = False,
    tier: SubdivisionReviewTier = SubdivisionReviewTier.ADMINISTRATIVE_MINOR,
    risk_flags: list[RiskFlag] | None = None,
) -> ScenarioResult:
    return ScenarioResult(
        lot_layout_type=LotLayoutType.SIMPLE_HALVE,
        resulting_lots=[],
        num_resulting_lots=2,
        requires_variance=requires_variance,
        requires_rezone=requires_rezone,
        requires_flag_lot_provision=requires_flag_lot_provision,
        subdivision_review_tier=tier,
        risk_flags=risk_flags or [],
    )


def _result(
    *,
    scenarios: list[ScenarioResult] | None = None,
    disqualifying_flags: list[RiskFlag] | None = None,
    data_gap: bool = False,
    max_theoretical_lots: int = 2,
) -> SubdivisionFeasibilityResult:
    return SubdivisionFeasibilityResult(
        max_theoretical_lots=max_theoretical_lots,
        scenarios=scenarios if scenarios is not None else [_scenario()],
        disqualifying_flags=disqualifying_flags or [],
        data_gap=data_gap,
    )


# ── score_result() ─────────────────────────────────────────────────────────────


def test_score_result_returns_feasibility_score():
    result = score_result(_result())
    assert isinstance(result, FeasibilityScore)
    assert 0 <= result.overall <= 100
    assert isinstance(result.recommendation, Recommendation)


def test_score_result_has_all_five_sub_scores():
    result = score_result(_result())
    keys = set(result.sub_scores.keys())
    assert keys == {
        "zoning_compliance",
        "physical_buildability",
        "access_utility",
        "process_complexity",
        "financial_upside",
    }


def test_score_result_sub_scores_are_sub_score_instances():
    result = score_result(_result())
    for sub in result.sub_scores.values():
        assert isinstance(sub, SubScore)
        assert 0 <= sub.score <= 100
        assert 0 < sub.weight <= 1
        assert isinstance(sub.explanation, str)


def test_score_result_weights_sum_to_one():
    result = score_result(_result())
    total = sum(s.weight for s in result.sub_scores.values())
    assert abs(total - 1.0) < 1e-9


# ── _zoning_score ──────────────────────────────────────────────────────────────


def test_zoning_data_gap_returns_zero():
    score, _ = _zoning_score(_result(data_gap=True))
    assert score == 0


def test_zoning_area_shortfall_returns_five():
    score, _ = _zoning_score(
        _result(
            disqualifying_flags=[_flag(RiskCategory.ZONING_AREA_SHORTFALL)],
        )
    )
    assert score == 5


def test_zoning_no_scenarios_returns_ten():
    score, _ = _zoning_score(_result(scenarios=[]))
    assert score == 10


def test_zoning_clean_scenario_returns_100():
    score, exp = _zoning_score(_result(scenarios=[_scenario()]))
    assert score == 100
    assert "as-of-right" in exp


def test_zoning_variance_deducts_30():
    score, _ = _zoning_score(_result(scenarios=[_scenario(requires_variance=True)]))
    assert score == 70


def test_zoning_rezone_deducts_50():
    score, _ = _zoning_score(_result(scenarios=[_scenario(requires_rezone=True)]))
    assert score == 50


def test_zoning_rezone_and_variance_floors_at_zero():
    # -50 rezone + -30 variance + -15 flag = -95, floor 0
    score, _ = _zoning_score(
        _result(
            scenarios=[
                _scenario(
                    requires_rezone=True, requires_variance=True, requires_flag_lot_provision=True
                )
            ]
        )
    )
    assert score == max(0, 100 - 50 - 30 - 15)
    assert score == 5


def test_zoning_flag_lot_deducts_15():
    score, _ = _zoning_score(_result(scenarios=[_scenario(requires_flag_lot_provision=True)]))
    assert score == 85


# ── _buildability_score ────────────────────────────────────────────────────────


def test_buildability_data_gap_returns_50():
    score, exp = _buildability_score(_result(data_gap=True))
    assert score == 50
    assert "neutral" in exp


def test_buildability_no_flags_returns_100():
    score, _ = _buildability_score(_result())
    assert score == 100


def test_buildability_flood_zone_deducts_40():
    r = _result(scenarios=[_scenario(risk_flags=[_flag(RiskCategory.FLOOD_ZONE_EXPOSURE)])])
    score, _ = _buildability_score(r)
    assert score == 60


def test_buildability_wetland_deducts_30():
    r = _result(scenarios=[_scenario(risk_flags=[_flag(RiskCategory.WETLAND_EXPOSURE)])])
    score, _ = _buildability_score(r)
    assert score == 70


def test_buildability_structure_conflict_deducts_30():
    r = _result(scenarios=[_scenario(risk_flags=[_flag(RiskCategory.EXISTING_STRUCTURE_CONFLICT)])])
    score, _ = _buildability_score(r)
    assert score == 70


def test_buildability_multiple_flags_floor_at_zero():
    flags = [
        _flag(RiskCategory.FLOOD_ZONE_EXPOSURE),
        _flag(RiskCategory.WETLAND_EXPOSURE),
        _flag(RiskCategory.STEEP_SLOPE),
        _flag(RiskCategory.EXISTING_STRUCTURE_CONFLICT),
    ]
    r = _result(scenarios=[_scenario(risk_flags=flags)])
    score, _ = _buildability_score(r)
    assert score == 0


# ── _access_score ──────────────────────────────────────────────────────────────


def test_access_no_flags_returns_100():
    score, _ = _access_score(_result())
    assert score == 100


def test_access_insufficient_road_deducts_50():
    r = _result(scenarios=[_scenario(risk_flags=[_flag(RiskCategory.INSUFFICIENT_ROAD_ACCESS)])])
    score, _ = _access_score(r)
    assert score == 50


def test_access_no_sewer_deducts_20():
    r = _result(scenarios=[_scenario(risk_flags=[_flag(RiskCategory.NO_PUBLIC_SEWER_ACCESS)])])
    score, _ = _access_score(r)
    assert score == 80


def test_access_flag_lot_only_deducts_10():
    # all scenarios require flag lot provision → -10
    r = _result(scenarios=[_scenario(requires_flag_lot_provision=True)])
    score, _ = _access_score(r)
    assert score == 90


# ── _process_score ─────────────────────────────────────────────────────────────


def test_process_no_scenarios_returns_zero():
    score, _ = _process_score(_result(scenarios=[]))
    assert score == 0


def test_process_admin_minor_returns_100():
    r = _result(scenarios=[_scenario(tier=SubdivisionReviewTier.ADMINISTRATIVE_MINOR)])
    score, _ = _process_score(r)
    assert score == 100


def test_process_planning_commission_returns_50():
    r = _result(scenarios=[_scenario(tier=SubdivisionReviewTier.PLANNING_COMMISSION_MAJOR)])
    score, _ = _process_score(r)
    assert score == 50


# ── _financial_score ───────────────────────────────────────────────────────────


def test_financial_returns_50_placeholder():
    score, exp = _financial_score()
    assert score == 50
    assert "pending" in exp.lower()


# ── _recommend ─────────────────────────────────────────────────────────────────


def test_recommend_data_gap_is_unlikely():
    assert _recommend(_result(data_gap=True), 80) == Recommendation.UNLIKELY


def test_recommend_disqualifying_flags_is_not_feasible():
    r = _result(disqualifying_flags=[_flag(RiskCategory.ZONING_AREA_SHORTFALL)])
    assert _recommend(r, 80) == Recommendation.NOT_FEASIBLE


def test_recommend_no_scenarios_is_not_feasible():
    assert _recommend(_result(scenarios=[]), 20) == Recommendation.NOT_FEASIBLE


def test_recommend_overall_below_30_is_not_feasible():
    assert _recommend(_result(), 29) == Recommendation.NOT_FEASIBLE


def test_recommend_overall_70_or_above_is_pursue():
    assert _recommend(_result(), 70) == Recommendation.PURSUE
    assert _recommend(_result(), 100) == Recommendation.PURSUE


def test_recommend_overall_50_to_69_is_pursue_with_caution():
    assert _recommend(_result(), 50) == Recommendation.PURSUE_WITH_CAUTION
    assert _recommend(_result(), 69) == Recommendation.PURSUE_WITH_CAUTION


def test_recommend_overall_30_to_49_is_unlikely():
    assert _recommend(_result(), 30) == Recommendation.UNLIKELY
    assert _recommend(_result(), 49) == Recommendation.UNLIKELY


# ── Integration: score maps to recommendation ──────────────────────────────────


def test_high_quality_parcel_gets_pursue():
    # clean parcel: no flags, admin minor, no variance/rezone
    result = score_result(
        _result(scenarios=[_scenario(tier=SubdivisionReviewTier.ADMINISTRATIVE_MINOR)])
    )
    assert result.recommendation == Recommendation.PURSUE
    assert result.overall >= 70


def test_disqualified_parcel_gets_not_feasible():
    result = score_result(
        _result(
            scenarios=[],
            disqualifying_flags=[_flag(RiskCategory.ZONING_AREA_SHORTFALL)],
        )
    )
    assert result.recommendation == Recommendation.NOT_FEASIBLE
