from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from shapely.geometry import LineString, Polygon


class LotLayoutType(str, Enum):
    SIMPLE_HALVE = "SIMPLE_HALVE"
    FRONTAGE_STRIP = "FRONTAGE_STRIP"
    FLAG_LOT = "FLAG_LOT"
    UNEVEN_SPLIT = "UNEVEN_SPLIT"


class ConstraintType(str, Enum):
    FLOOD_ZONE = "FLOOD_ZONE"
    WETLAND = "WETLAND"
    STEEP_SLOPE = "STEEP_SLOPE"
    SOIL_LIMITATION = "SOIL_LIMITATION"
    EASEMENT = "EASEMENT"
    HISTORIC_OVERLAY = "HISTORIC_OVERLAY"
    OTHER_OVERLAY = "OTHER_OVERLAY"


class ConstraintSeverity(str, Enum):
    BLOCKING = "BLOCKING"
    SIGNIFICANT = "SIGNIFICANT"
    MINOR = "MINOR"
    INFORMATIONAL = "INFORMATIONAL"


class SubdivisionReviewTier(str, Enum):
    ADMINISTRATIVE_MINOR = "ADMINISTRATIVE_MINOR"
    PLANNING_COMMISSION_MAJOR = "PLANNING_COMMISSION_MAJOR"


class RiskCategory(str, Enum):
    ZONING_AREA_SHORTFALL = "ZONING_AREA_SHORTFALL"
    ZONING_FRONTAGE_SHORTFALL = "ZONING_FRONTAGE_SHORTFALL"
    REQUIRES_VARIANCE = "REQUIRES_VARIANCE"
    REQUIRES_REZONE = "REQUIRES_REZONE"
    REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED = "REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED"
    EXISTING_STRUCTURE_CONFLICT = "EXISTING_STRUCTURE_CONFLICT"
    FLOOD_ZONE_EXPOSURE = "FLOOD_ZONE_EXPOSURE"
    WETLAND_EXPOSURE = "WETLAND_EXPOSURE"
    STEEP_SLOPE = "STEEP_SLOPE"
    SEPTIC_SUITABILITY_UNKNOWN_OR_POOR = "SEPTIC_SUITABILITY_UNKNOWN_OR_POOR"
    NO_PUBLIC_SEWER_ACCESS = "NO_PUBLIC_SEWER_ACCESS"
    INSUFFICIENT_ROAD_ACCESS = "INSUFFICIENT_ROAD_ACCESS"
    MULTI_DISTRICT_PARCEL = "MULTI_DISTRICT_PARCEL"
    STALE_ZONING_DATA = "STALE_ZONING_DATA"
    DATA_GAP = "DATA_GAP"


@dataclass
class RiskFlag:
    category: RiskCategory
    severity: ConstraintSeverity
    message: str
    source_citation: Optional[str] = None


@dataclass
class ParcelGeometryInput:
    """
    Parcel boundary and frontage information.
    All coordinates must be in a projected CRS with units in US survey feet.
    The caller (adapter layer) is responsible for projecting from lat/lon.
    """
    boundary: Polygon
    frontage_edge: LineString      # the road-facing edge of the parcel
    zoning_district_code: Optional[str]  # None triggers DATA_GAP
    multi_district: bool = False   # parcel straddles two zoning boundaries


@dataclass
class ZoningRulesInput:
    """Dimensional standards for the parcel's zoning district. All distances in feet."""
    min_lot_area_sqft: int
    min_lot_width_ft: int
    setback_front_ft: int
    setback_side_ft: int
    setback_rear_ft: int
    requires_public_road_frontage: bool
    allows_flag_lots: bool
    minor_subdivision_threshold: int   # lots <= this = ADMINISTRATIVE_MINOR
    min_lot_depth_ft: Optional[int] = None
    max_density_units_per_acre: Optional[float] = None
    min_road_frontage_ft: Optional[int] = None  # if None, defaults to min_lot_width_ft
    flag_lot_min_access_strip_ft: Optional[int] = None


@dataclass
class StructureInput:
    """Existing structure footprint. Coordinates in same projected CRS (feet) as parcel."""
    footprint: Polygon


@dataclass
class ConstraintInput:
    """
    One environmental/physical constraint intersecting the parcel.
    geometry is the portion of the constraint layer that overlaps the parcel.
    """
    constraint_type: ConstraintType
    severity: ConstraintSeverity
    geometry: Polygon


@dataclass
class LotResult:
    geometry: Polygon
    area_sqft: float
    frontage_ft: float          # width along road; for flag lot = access strip width
    buildable_width_ft: float   # width of the buildable portion (full width for flag lot body)
    buildable_depth_ft: float
    has_direct_frontage: bool   # False for flag lot rear portion
    meets_min_lot_size: bool
    meets_min_frontage: bool
    has_buildable_envelope: bool


@dataclass
class ScenarioResult:
    lot_layout_type: LotLayoutType
    resulting_lots: list[LotResult]
    num_resulting_lots: int
    requires_variance: bool
    requires_rezone: bool
    requires_flag_lot_provision: bool
    subdivision_review_tier: SubdivisionReviewTier
    risk_flags: list[RiskFlag] = field(default_factory=list)


@dataclass
class SubdivisionFeasibilityResult:
    max_theoretical_lots: int
    scenarios: list[ScenarioResult]          # ranked best-first
    disqualifying_flags: list[RiskFlag]      # reasons no scenarios could be generated
    data_gap: bool                           # True if engine couldn't run due to missing data
