from __future__ import annotations

import io

from fastapi import APIRouter, File, HTTPException, UploadFile
from shapely.geometry import Polygon, mapping

from app.api.schemas import EdgeInfo, ParseResponse
from app.parsers.geojson import parse_geojson
from app.parsers.kml import parse_kml
from app.parsers.projection import get_utm_epsg, project_to_feet
from app.parsers.shapefile import parse_shapefile_zip

router = APIRouter(tags=["parse"])


@router.post("/geojson", response_model=ParseResponse)
async def parse_geojson_endpoint(body: dict) -> ParseResponse:
    try:
        polygon_4326 = parse_geojson(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _build_parse_response(polygon_4326)


@router.post("/kml", response_model=ParseResponse)
async def parse_kml_endpoint(file: UploadFile = File(...)) -> ParseResponse:
    kml_bytes = await file.read()
    try:
        polygon_4326 = parse_kml(kml_bytes)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _build_parse_response(polygon_4326)


@router.post("/shapefile", response_model=ParseResponse)
async def parse_shapefile_endpoint(file: UploadFile = File(...)) -> ParseResponse:
    zip_bytes = await file.read()
    try:
        polygon_4326 = parse_shapefile_zip(zip_bytes)
    except (ValueError, Exception) as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return _build_parse_response(polygon_4326)


def _build_parse_response(polygon_4326: Polygon) -> ParseResponse:
    poly_ft = project_to_feet(polygon_4326)
    edges = _edge_list(poly_ft)
    area_sqft = poly_ft.area
    return ParseResponse(
        polygon=mapping(polygon_4326),
        edges=edges,
        area_sqft=round(area_sqft, 1),
        area_acres=round(area_sqft / 43_560.0, 4),
    )


def _edge_list(poly_ft: Polygon) -> list[EdgeInfo]:
    coords = list(poly_ft.exterior.coords)
    edges = []
    for i in range(len(coords) - 1):
        x0, y0 = coords[i]
        x1, y1 = coords[i + 1]
        length = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        edges.append(EdgeInfo(index=i, length_ft=round(length, 1)))
    return edges
