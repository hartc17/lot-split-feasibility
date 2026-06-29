from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.schemas import (
    FeasibilityRequest,
    FeasibilityResponse,
    FeasibilityScore,
    ScenarioSummary,
    SubScoreDetail,
)
from app.engine.calculator import calculate_subdivision_scenarios
from app.engine.inputs import build_parcel_geometry_input, build_zoning_rules_input
from app.parsers.geojson import parse_geojson
from app.scoring.scoring import score_result

router = APIRouter(tags=["feasibility"])


@router.post("", response_model=FeasibilityResponse)
async def run_feasibility(body: FeasibilityRequest) -> FeasibilityResponse:
    try:
        polygon_4326 = parse_geojson(body.geometry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid geometry: {exc}")

    try:
        parcel_input = build_parcel_geometry_input(
            polygon_4326,
            body.frontage_edge_index,
            zoning_district_code=body.zoning.district_code or None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    zoning_dict = body.zoning.model_dump()
    try:
        zoning_input = build_zoning_rules_input(zoning_dict)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    result = calculate_subdivision_scenarios(
        parcel=parcel_input,
        zoning=zoning_input,
        constraints=[],
        existing_structures=[],
    )

    fscore = score_result(result)

    scenarios = [
        ScenarioSummary(
            num_resulting_lots=s.num_resulting_lots,
            lot_layout_type=s.lot_layout_type.value,
            requires_variance=s.requires_variance,
            requires_rezone=s.requires_rezone,
            requires_flag_lot_provision=s.requires_flag_lot_provision,
            subdivision_review_tier=s.subdivision_review_tier.value,
            risk_flag_count=len(s.risk_flags),
        )
        for s in result.scenarios
    ]

    return FeasibilityResponse(
        report_id=None,
        status="complete",
        max_theoretical_lots=result.max_theoretical_lots,
        scenarios=scenarios,
        disqualifying_flags=[f.category.value for f in result.disqualifying_flags],
        data_gap=result.data_gap,
        score=FeasibilityScore(
            overall=fscore.overall,
            recommendation=fscore.recommendation.value,
            sub_scores={
                k: SubScoreDetail(
                    score=v.score,
                    weight=v.weight,
                    explanation=v.explanation,
                )
                for k, v in fscore.sub_scores.items()
            },
        ),
    )
