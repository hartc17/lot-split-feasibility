from __future__ import annotations

from shapely.geometry import LineString, Polygon, mapping, shape

from fastapi import APIRouter, HTTPException

from app.api.schemas import ComputeSplitRequest, ManualSplitEvaluation, SectionInfo
from app.engine.inputs import build_parcel_geometry_input, build_zoning_rules_input
from app.engine.manual_split import evaluate_manual_split
from app.parsers.geojson import parse_geojson
from app.parsers.projection import get_utm_epsg, project_linestring_to_feet, unproject_polygon_from_feet

router = APIRouter(tags=["split"])


def build_manual_split_evaluation(
    polygon_4326: Polygon,
    frontage_edge_indices: list[int],
    zoning_data: dict,
    split_line_dicts: list[dict],
) -> ManualSplitEvaluation:
    """Project inputs, run evaluate_manual_split, and return serialisable results.

    Shared by the /v1/split/compute route and the /v1/feasibility route when
    split_lines are provided.
    """
    lon, lat = polygon_4326.centroid.x, polygon_4326.centroid.y
    utm_epsg = get_utm_epsg(lon, lat)

    edge_indices = frontage_edge_indices if frontage_edge_indices else [0]
    parcel_input = build_parcel_geometry_input(polygon_4326, edge_indices)
    zoning_input = build_zoning_rules_input(zoning_data)

    split_lines_ft: list[LineString] = [
        project_linestring_to_feet(shape(d), utm_epsg) for d in split_line_dicts
    ]

    result = evaluate_manual_split(parcel_input, split_lines_ft, zoning_input)

    sections = [
        SectionInfo(
            geometry=dict(mapping(unproject_polygon_from_feet(lot.geometry, utm_epsg))),
            area_sqft=round(lot.area_sqft, 1),
            area_acres=round(lot.area_acres, 4),
            frontage_ft=round(lot.frontage_ft, 1),
            buildable_width_ft=round(lot.buildable_width_ft, 1),
            buildable_depth_ft=round(lot.buildable_depth_ft, 1),
            has_direct_frontage=lot.has_direct_frontage,
            meets_min_lot_size=lot.meets_min_lot_size,
            meets_min_frontage=lot.meets_min_frontage,
            has_buildable_envelope=lot.has_buildable_envelope,
        )
        for lot in result.lots
    ]
    return ManualSplitEvaluation(
        sections=sections,
        all_sections_viable=result.all_lots_viable,
        flags=[f.category.value for f in result.flags],
    )


@router.post("/compute", response_model=ManualSplitEvaluation)
async def compute_split(body: ComputeSplitRequest) -> ManualSplitEvaluation:
    try:
        polygon_4326 = parse_geojson(body.geometry)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid geometry: {exc}") from exc

    try:
        return build_manual_split_evaluation(
            polygon_4326,
            body.frontage_edge_indices,
            body.zoning.model_dump(),
            body.split_lines,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
