from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class SectionInfo(BaseModel):
    geometry: dict  # GeoJSON Polygon, EPSG:4326 - for map rendering
    area_sqft: float
    area_acres: float
    frontage_ft: float
    buildable_width_ft: float
    buildable_depth_ft: float
    has_direct_frontage: bool
    meets_min_lot_size: bool
    meets_min_frontage: bool
    has_buildable_envelope: bool


class ManualSplitEvaluation(BaseModel):
    sections: list[SectionInfo]
    all_sections_viable: bool
    flags: list[str]  # RiskCategory values


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


class ComputeSplitRequest(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Polygon (EPSG:4326)")
    split_lines: list[dict] = Field(..., min_length=1, description="GeoJSON LineStrings to split along")
    frontage_edge_indices: list[int] = Field(default_factory=list)
    zoning: ZoningRulesRequest

    @model_validator(mode="after")
    def geometry_must_be_polygon(self) -> ComputeSplitRequest:
        t = self.geometry.get("type")
        if t not in ("Polygon", "MultiPolygon", "Feature", "FeatureCollection"):
            raise ValueError(f"geometry.type must be a GeoJSON Polygon type, got {t!r}")
        return self


class FeasibilityRequest(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Polygon (EPSG:4326)")
    frontage_edge_indices: list[int] = Field(
        ..., min_length=1, description="0-based indices of contiguous road-facing edges"
    )
    zoning: ZoningRulesRequest
    split_lines: list[dict] | None = Field(
        default=None, description="Optional GeoJSON LineStrings for manual split evaluation"
    )

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


class SubScoreDetail(BaseModel):
    score: int
    weight: float
    explanation: str


class FeasibilityScore(BaseModel):
    overall: int
    recommendation: str
    sub_scores: dict[str, SubScoreDetail]


class FeasibilityResponse(BaseModel):
    report_id: str | None = None
    status: str
    max_theoretical_lots: int | None
    scenarios: list[ScenarioSummary]
    disqualifying_flags: list[str]
    data_gap: bool
    score: FeasibilityScore
    manual_split: ManualSplitEvaluation | None = None
