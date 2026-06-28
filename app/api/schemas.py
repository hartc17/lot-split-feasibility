from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ZoningRulesRequest(BaseModel):
    district_code: str = ""
    min_lot_area_sqft: float = Field(..., gt=0)
    min_lot_width_ft: float = Field(..., gt=0)
    setback_front_ft: float = Field(..., gt=0)
    setback_side_ft: float = Field(..., gt=0)
    setback_rear_ft: float = Field(..., gt=0)
    requires_public_road_frontage: bool = True
    allows_flag_lots: bool = False
    flag_lot_min_access_strip_ft: float = Field(default=20.0, gt=0)
    minor_subdivision_threshold: int = Field(default=4, gt=0)


class FeasibilityRequest(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Polygon (EPSG:4326)")
    frontage_edge_index: int = Field(..., ge=0, description="0-based index of the road-facing edge")
    zoning: ZoningRulesRequest

    @model_validator(mode="after")
    def geometry_must_be_polygon(self) -> FeasibilityRequest:
        t = self.geometry.get("type")
        if t not in ("Polygon", "MultiPolygon", "Feature", "FeatureCollection"):
            raise ValueError(f"geometry.type must be a GeoJSON Polygon type, got {t!r}")
        return self


class EdgeInfo(BaseModel):
    index: int
    length_ft: float


class ParseResponse(BaseModel):
    polygon: dict
    edges: list[EdgeInfo]
    area_sqft: float
    area_acres: float


class ScenarioSummary(BaseModel):
    num_resulting_lots: int
    lot_layout_type: str
    requires_variance: bool
    requires_rezone: bool
    requires_flag_lot_provision: bool
    subdivision_review_tier: str
    risk_flag_count: int


class FeasibilityResponse(BaseModel):
    report_id: str | None = None
    status: str
    max_theoretical_lots: int | None
    scenarios: list[ScenarioSummary]
    disqualifying_flags: list[str]
    data_gap: bool
