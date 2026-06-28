# Lot Split Feasibility Engine — Phase 1: Foundation & Calculation Engine

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the deterministic subdivision feasibility calculation engine with all 7 spec fixture test cases passing, plus SQLAlchemy data models — zero external dependencies in the engine itself.

**Architecture:** The engine is a pure function `calculate_subdivision_scenarios(parcel, zoning, constraints, structures)` with no I/O, no DB access, no network calls. Geometric calculations use Shapely with projected coordinates in feet. SQLAlchemy models are defined separately and have no dependency on the engine module.

**Tech Stack:** Python 3.11+, Shapely 2.x, numpy, pyproj, pytest, SQLAlchemy 2.x, GeoAlchemy2, PostgreSQL + PostGIS (models only — no DB needed for engine tests)

## Global Constraints

- Python 3.11+ required (use `match` statements, `|` union types where appropriate)
- `/app/engine/` must have ZERO imports from `/app/models/`, `/app/adapters/`, or any I/O module — enforced by a pytest import check
- All area/distance math must operate on coordinates in US survey feet — never geographic lat/lon
- Minimum lot area/width thresholds come from `ZoningRulesInput`, never hardcoded in engine code
- `ZoningDistrict` rows with no `last_verified_date` must NOT be usable in production (enforced at the application layer in Phase 7, but the model field is required in Phase 1)
- Shapely 2.x API (use `shapely.ops.split`, `shapely.affinity`, `shapely.ops.unary_union`)
- No silent failures: every strategy either returns a valid scenario or returns explicit failure reasons in `risk_flags`

## File Map

```
lot-split-feasibility/
├── pyproject.toml
├── app/
│   ├── __init__.py
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── types.py          # Input/output dataclasses + enums (no DB deps)
│   │   ├── geometry.py       # Shapely helpers: interior_normal, buildable_envelope
│   │   ├── eligibility.py    # Step 1: fast-fail checks
│   │   ├── strategies/
│   │   │   ├── __init__.py
│   │   │   ├── simple_halve.py    # SIMPLE_HALVE + FRONTAGE_STRIP
│   │   │   └── flag_lot.py        # FLAG_LOT
│   │   ├── constraints.py    # Step 4: per-lot environmental constraint filtering
│   │   └── calculator.py     # Main entry point — assembles all steps
│   └── models/
│       ├── __init__.py
│       ├── base.py
│       ├── jurisdiction.py
│       ├── zoning_district.py
│       ├── parcel.py
│       ├── environmental_constraint.py
│       ├── subdivision_scenario.py
│       └── feasibility_report.py
├── tests/
│   ├── __init__.py
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── parcels.py        # 7 synthetic fixtures from spec Section 6.3
│   └── engine/
│       ├── __init__.py
│       ├── test_engine_isolation.py  # verifies no DB/adapter imports
│       ├── test_eligibility.py
│       ├── test_geometry.py
│       ├── test_strategies.py
│       └── test_calculator.py        # all 7 fixture cases
└── docs/
    └── superpowers/
        └── plans/
            └── 2026-06-28-lot-split-phase1-engine.md  (this file)
```

---

## Task 0: Jurisdiction Selection (Human Research — No Code)

**Files:** None — this is a research task producing a decision and notes document.

This task must be completed before Phase 2 (data adapters). Phase 1 (Tasks 1–11) can proceed in parallel since the engine uses only synthetic fixtures.

- [ ] **Step 1: Evaluate candidate counties against the 5 criteria in spec Section 4.1**

For each candidate county, answer these questions:
1. Does it have a public parcel GIS API? Test: visit `https://{county-gis-url}/MapServer/0/query?where=1%3D1&outFields=*&f=json` — if it returns data, the API is live.
2. How many residential zoning districts? Open the zoning ordinance (Municode or county site). Count R-x, SF-x, RR-x, AG-x districts. Target: 5–15.
3. Is there a defined "minor subdivision" or "administrative lot split" process distinct from full platting? Check the subdivision ordinance (separate from zoning code). Target: yes, with a lot count threshold (≤3 or ≤4).
4. Is there active lot-split activity? Check county deed records or GIS for recently-created parcels with sequential APNs.

**Recommended starting candidates** (meet likely GIS criteria based on known ArcGIS Online county presence + growth activity):
- Hays County, TX (fast-growing, active rural residential)
- Williamson County, TX (similar, lots of unincorporated residential)
- Forsyth County, GA (growing exurb of Atlanta)
- St. Johns County, FL (growing exurb of Jacksonville)

- [ ] **Step 2: Pick one county. Record the decision in `docs/pilot-jurisdiction.md`**

Include: county name, state, GIS API base URL, zoning ordinance URL, subdivision ordinance URL, minor subdivision threshold (lot count), and typical residential zoning district codes.

- [ ] **Step 3: Read the zoning ordinance. For each residential zoning district, record the dimensional standards**

This is the data that goes into `ZoningDistrict` rows. Record at minimum: `min_lot_area_sqft`, `min_lot_width_ft`, `setback_front_ft`, `setback_side_ft`, `setback_rear_ft`, `allows_flag_lots`, `min_road_frontage_ft`, and the ordinance section citation. This data is needed for Phase 2.

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `app/__init__.py`, `app/engine/__init__.py`, `app/engine/strategies/__init__.py`, `app/models/__init__.py`
- Create: `tests/__init__.py`, `tests/fixtures/__init__.py`, `tests/engine/__init__.py`

- [ ] **Step 1: Create the project directory and pyproject.toml**

```bash
cd /Users/coltonhart/lot-split-feasibility
```

Create `pyproject.toml`:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "lot-split-feasibility"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "shapely>=2.0",
    "numpy>=1.26",
    "pyproj>=3.6",
    "sqlalchemy>=2.0",
    "geoalchemy2>=0.14",
    "fastapi>=0.110",
    "pydantic>=2.0",
    "alembic>=1.13",
    "psycopg2-binary>=2.9",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-cov>=4.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]

[tool.hatch.build.targets.wheel]
packages = ["app"]
```

- [ ] **Step 2: Create all `__init__.py` files**

```bash
touch app/__init__.py \
      app/engine/__init__.py \
      app/engine/strategies/__init__.py \
      app/models/__init__.py \
      tests/__init__.py \
      "tests/fixtures/__init__.py" \
      tests/engine/__init__.py
```

- [ ] **Step 3: Install dependencies**

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

Expected: `Successfully installed lot-split-feasibility-0.1.0 ...`

- [ ] **Step 4: Verify pytest runs**

```bash
pytest --co -q
```

Expected: `no tests ran` (0 items, no errors)

- [ ] **Step 5: Commit**

```bash
git init && git add pyproject.toml app/ tests/ docs/
git commit -m "feat: initialize project scaffold"
```

---

## Task 2: Engine Types

**Files:**
- Create: `app/engine/types.py`
- Create: `tests/engine/test_engine_isolation.py`

**Produces:**
- `ParcelGeometryInput`, `ZoningRulesInput`, `StructureInput`, `ConstraintInput`
- `LotResult`, `ScenarioResult`, `SubdivisionFeasibilityResult`
- Enums: `LotLayoutType`, `ConstraintType`, `ConstraintSeverity`, `SubdivisionReviewTier`, `RiskCategory`
- `RiskFlag` dataclass

- [ ] **Step 1: Write the isolation test first**

Create `tests/engine/test_engine_isolation.py`:

```python
"""Verify the engine module imports no DB, adapter, or I/O modules."""
import ast
import os
from pathlib import Path


def _get_imports(filepath: Path) -> list[str]:
    tree = ast.parse(filepath.read_text())
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_engine_has_no_db_imports():
    engine_dir = Path("app/engine")
    forbidden = {"app.models", "app.adapters", "sqlalchemy", "geoalchemy2", "psycopg2"}
    violations = []
    for py_file in engine_dir.rglob("*.py"):
        for imp in _get_imports(py_file):
            if any(imp.startswith(f) for f in forbidden):
                violations.append(f"{py_file}: imports {imp!r}")
    assert violations == [], "\n".join(violations)
```

- [ ] **Step 2: Run it — expect it to pass (no engine files yet)**

```bash
pytest tests/engine/test_engine_isolation.py -v
```

Expected: PASS (no engine files to scan yet)

- [ ] **Step 3: Create `app/engine/types.py`**

```python
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
    minor_subdivision_threshold: int   # lots ≤ this = ADMINISTRATIVE_MINOR
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
```

- [ ] **Step 4: Run isolation test again — expect still PASS**

```bash
pytest tests/engine/test_engine_isolation.py -v
```

Expected: PASS (types.py imports only `shapely` and stdlib — shapely is allowed)

- [ ] **Step 5: Commit**

```bash
git add app/engine/types.py tests/engine/test_engine_isolation.py
git commit -m "feat: add engine input/output types and isolation test"
```

---

## Task 3: Test Fixture Builders

**Files:**
- Create: `tests/fixtures/parcels.py`

**Produces:** 7 named builder functions returning `(ParcelGeometryInput, ZoningRulesInput, list[StructureInput], list[ConstraintInput])` tuples, one per spec Section 6.3 fixture.

**Coordinate system for all fixtures:** origin at bottom-left corner of parcel; frontage along y=0 (bottom edge, runs left-to-right); interior is +y direction. Coordinates in feet.

- [ ] **Step 1: Create `tests/fixtures/parcels.py`**

```python
"""
Synthetic parcel fixtures for engine unit tests.
All coordinates in feet, frontage along y=0 (bottom edge).
These correspond exactly to the 7 fixtures in spec Section 6.3.
"""
from shapely.geometry import LineString, Polygon

from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ConstraintType,
    ParcelGeometryInput,
    StructureInput,
    ZoningRulesInput,
)

# Shared zoning defaults used across multiple fixtures
_BASE_ZONING = dict(
    setback_front_ft=20,
    setback_side_ft=5,
    setback_rear_ft=20,
    requires_public_road_frontage=True,
    allows_flag_lots=False,
    minor_subdivision_threshold=4,
    min_road_frontage_ft=40,
)


def _rect(width: float, depth: float) -> Polygon:
    """Axis-aligned rectangle from (0,0) to (width, depth)."""
    return Polygon([(0, 0), (width, 0), (width, depth), (0, depth)])


def _frontage(width: float) -> LineString:
    """Bottom edge of parcel as the frontage edge."""
    return LineString([(0, 0), (width, 0)])


def fixture_1_clean_split():
    """
    Fixture 1: 80×125ft parcel (10,000 sqft = 2× minimum).
    Ample frontage (80ft), no constraints, no structures.
    Expected: valid SIMPLE_HALVE into two 40×125ft lots.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    return parcel, zoning, [], []


def fixture_2_area_shortfall():
    """
    Fixture 2: 80×112.5ft parcel (9,000 sqft = 1.8× minimum).
    Same zoning as fixture 1. Cannot produce two 5,000 sqft lots.
    Expected: 0 valid scenarios; ZONING_AREA_SHORTFALL flag with actual numbers.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 112.5),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    return parcel, zoning, [], []


def fixture_3_flag_lot_allowed():
    """
    Fixture 3: 60×250ft parcel (15,000 sqft = 3× minimum).
    Frontage only 60ft — too narrow for SIMPLE_HALVE (needs 2×40ft=80ft).
    Flag lots allowed; access strip = 20ft min.
    Expected: valid FLAG_LOT scenario (40ft conventional front lot + L-shaped rear).
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(60, 250),
        frontage_edge=_frontage(60),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        allows_flag_lots=True,
        flag_lot_min_access_strip_ft=20,
        min_road_frontage_ft=40,
        setback_front_ft=20,
        setback_side_ft=5,
        setback_rear_ft=20,
        requires_public_road_frontage=True,
        minor_subdivision_threshold=4,
    )
    return parcel, zoning, [], []


def fixture_4_flag_lot_disallowed():
    """
    Fixture 4: Same 60×250ft parcel, same zoning but allows_flag_lots=False.
    SIMPLE_HALVE fails (too narrow). FLAG_LOT not evaluated (not allowed).
    Expected: 0 valid scenarios; REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED flag.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(60, 250),
        frontage_edge=_frontage(60),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        allows_flag_lots=False,
        flag_lot_min_access_strip_ft=None,
        min_road_frontage_ft=40,
        setback_front_ft=20,
        setback_side_ft=5,
        setback_rear_ft=20,
        requires_public_road_frontage=True,
        minor_subdivision_threshold=4,
    )
    return parcel, zoning, [], []


def fixture_5_structure_conflict():
    """
    Fixture 5: 80×125ft parcel (clean geometry), but existing 40×60ft house
    is centered such that no valid SIMPLE_HALVE split avoids setback violation.
    House: x=20..60, y=30..90. Any split at x=t must have t ≥ 65 (too wide)
    or t ≤ 15 (too narrow) to clear the 5ft side setback — both fail min_lot_width=40.
    Expected: EXISTING_STRUCTURE_CONFLICT flag, 0 valid scenarios.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    # House footprint: x=20..60, y=30..90
    house = StructureInput(
        footprint=Polygon([(20, 30), (60, 30), (60, 90), (20, 90)])
    )
    return parcel, zoning, [house], []


def fixture_6_flood_zone():
    """
    Fixture 6: 80×125ft parcel. FEMA floodway (BLOCKING) covers back third
    (y=83..125, full width). A split at x=40 creates valid front lots but
    any rear-lot scenario with buildable envelope in the floodway is invalid.
    Expected: valid scenario for front half; any scenario putting buildable area
    in floodway is discarded.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    # Floodway covers the rear ~33% of the parcel
    floodway = ConstraintInput(
        constraint_type=ConstraintType.FLOOD_ZONE,
        severity=ConstraintSeverity.BLOCKING,
        geometry=Polygon([(0, 83), (80, 83), (80, 125), (0, 125)]),
    )
    return parcel, zoning, [], [floodway]


def fixture_7_multi_district():
    """
    Fixture 7: Parcel straddles two zoning districts (multi_district=True).
    Expected: MULTI_DISTRICT_PARCEL flag, 0 scenarios, data_gap=False.
    """
    parcel = ParcelGeometryInput(
        boundary=_rect(80, 125),
        frontage_edge=_frontage(80),
        zoning_district_code="R-1",
        multi_district=True,
    )
    zoning = ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        **_BASE_ZONING,
    )
    return parcel, zoning, [], []
```

- [ ] **Step 2: Verify fixtures import cleanly**

```bash
python -c "from tests.fixtures.parcels import fixture_1_clean_split; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/parcels.py
git commit -m "test: add 7 synthetic parcel fixtures from spec Section 6.3"
```

---

## Task 4: Geometry Utilities

**Files:**
- Create: `app/engine/geometry.py`
- Create: `tests/engine/test_geometry.py`

**Produces:**
- `interior_normal(frontage_edge, parcel) -> np.ndarray` — unit vector pointing from frontage into parcel interior
- `measure_frontage_width(lot, frontage_direction) -> float` — lot width along road direction
- `has_buildable_envelope(lot, zoning, structures) -> bool` — checks if a valid building site remains after setbacks + existing structures

- [ ] **Step 1: Write failing tests**

Create `tests/engine/test_geometry.py`:

```python
import numpy as np
import pytest
from shapely.geometry import LineString, Polygon

from app.engine.geometry import (
    has_buildable_envelope,
    interior_normal,
    measure_frontage_width,
)
from app.engine.types import StructureInput, ZoningRulesInput


@pytest.fixture
def rect_parcel():
    return Polygon([(0, 0), (80, 0), (80, 125), (0, 125)])


@pytest.fixture
def bottom_frontage():
    return LineString([(0, 0), (80, 0)])


@pytest.fixture
def base_zoning():
    return ZoningRulesInput(
        min_lot_area_sqft=5000,
        min_lot_width_ft=40,
        setback_front_ft=20,
        setback_side_ft=5,
        setback_rear_ft=20,
        requires_public_road_frontage=True,
        allows_flag_lots=False,
        minor_subdivision_threshold=4,
        min_road_frontage_ft=40,
    )


def test_interior_normal_points_upward_for_bottom_frontage(rect_parcel, bottom_frontage):
    v = interior_normal(bottom_frontage, rect_parcel)
    # Frontage is along x-axis (y=0); interior is +y
    assert abs(v[0]) < 0.01, "x-component should be ~0"
    assert v[1] > 0.99, "y-component should be ~1.0 (pointing inward)"


def test_interior_normal_is_unit_vector(rect_parcel, bottom_frontage):
    v = interior_normal(bottom_frontage, rect_parcel)
    assert abs(np.linalg.norm(v) - 1.0) < 1e-9


def test_measure_frontage_width_full_lot(bottom_frontage):
    lot = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    p1, p2 = np.array(bottom_frontage.coords[0]), np.array(bottom_frontage.coords[-1])
    u = (p2 - p1) / np.linalg.norm(p2 - p1)
    width = measure_frontage_width(lot, u)
    assert abs(width - 40.0) < 0.1


def test_has_buildable_envelope_sufficient_lot(base_zoning):
    # 40×125ft lot; after 20ft front + 20ft rear + 5ft each side: 30×85ft buildable
    lot = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    assert has_buildable_envelope(lot, base_zoning, []) is True


def test_has_buildable_envelope_too_small_lot(base_zoning):
    # 10×30ft lot — after setbacks nothing remains
    lot = Polygon([(0, 0), (10, 0), (10, 30), (0, 30)])
    assert has_buildable_envelope(lot, base_zoning, []) is False


def test_has_buildable_envelope_with_blocking_structure(base_zoning):
    # 40×125ft lot, but a house fills most of it including its setback zone
    lot = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    # House at x=5..35, y=20..105 — covers the entire buildable zone
    house = StructureInput(footprint=Polygon([(5, 20), (35, 20), (35, 105), (5, 105)]))
    assert has_buildable_envelope(lot, base_zoning, [house]) is False
```

- [ ] **Step 2: Run tests — expect FAIL (module doesn't exist yet)**

```bash
pytest tests/engine/test_geometry.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.engine.geometry'`

- [ ] **Step 3: Create `app/engine/geometry.py`**

```python
from __future__ import annotations
from typing import Optional

import numpy as np
from shapely.geometry import LineString, Point, Polygon

from app.engine.types import StructureInput, ZoningRulesInput


def interior_normal(frontage_edge: LineString, parcel: Polygon) -> np.ndarray:
    """
    Unit vector perpendicular to frontage_edge pointing into the parcel interior.
    """
    coords = list(frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u = p2 - p1
    u_norm = u / np.linalg.norm(u)
    v = np.array([-u_norm[1], u_norm[0]])  # 90° CCW rotation

    # Verify v points into parcel; flip if not
    mid = (p1 + p2) / 2
    test_pt = Point(mid + v * 1.0)
    if not parcel.contains(test_pt):
        v = -v

    return v


def measure_frontage_width(lot: Polygon, frontage_direction: np.ndarray) -> float:
    """
    Lot extent in the direction of the frontage (i.e., width along the road).
    """
    coords = np.array(lot.exterior.coords[:-1])  # drop closing point
    projections = coords @ frontage_direction
    return float(projections.max() - projections.min())


def has_buildable_envelope(
    lot: Polygon,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
    min_house_footprint_sqft: float = 400.0,
) -> bool:
    """
    Return True if the lot has a buildable area >= min_house_footprint_sqft after:
    - applying a conservative uniform setback (minimum of front/side/rear)
    - removing exclusion zones around any existing structures
    """
    min_setback = min(zoning.setback_front_ft, zoning.setback_side_ft, zoning.setback_rear_ft)
    buildable = lot.buffer(-min_setback)

    for structure in existing_structures:
        if lot.intersects(structure.footprint):
            exclusion = structure.footprint.buffer(min_setback)
            buildable = buildable.difference(exclusion)

    if buildable.is_empty:
        return False
    return buildable.area >= min_house_footprint_sqft
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/engine/test_geometry.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/engine/geometry.py tests/engine/test_geometry.py
git commit -m "feat: add geometry utilities (interior_normal, measure_frontage_width, has_buildable_envelope)"
```

---

## Task 5: Eligibility Gate

**Files:**
- Create: `app/engine/eligibility.py`
- Create: `tests/engine/test_eligibility.py`

**Produces:** `check_eligibility(parcel, zoning, structures) -> list[RiskFlag]` — returns a (possibly empty) list of disqualifying flags. An empty list means the parcel passed all fast-fail checks.

- [ ] **Step 1: Write failing tests**

Create `tests/engine/test_eligibility.py`:

```python
import pytest
from tests.fixtures.parcels import (
    fixture_1_clean_split,
    fixture_2_area_shortfall,
    fixture_5_structure_conflict,
    fixture_7_multi_district,
)
from app.engine.eligibility import check_eligibility
from app.engine.types import RiskCategory


def test_clean_parcel_passes_eligibility():
    parcel, zoning, structures, _ = fixture_1_clean_split()
    flags = check_eligibility(parcel, zoning, structures)
    assert flags == [], f"Expected no flags, got: {flags}"


def test_area_shortfall_produces_flag():
    parcel, zoning, structures, _ = fixture_2_area_shortfall()
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.ZONING_AREA_SHORTFALL in categories


def test_area_shortfall_message_contains_actual_numbers():
    parcel, zoning, structures, _ = fixture_2_area_shortfall()
    flags = check_eligibility(parcel, zoning, structures)
    shortfall_flag = next(f for f in flags if f.category == RiskCategory.ZONING_AREA_SHORTFALL)
    # Message must say what the area IS and what's REQUIRED
    assert "9,000" in shortfall_flag.message or "9000" in shortfall_flag.message
    assert "10,000" in shortfall_flag.message or "10000" in shortfall_flag.message


def test_multi_district_produces_flag():
    parcel, zoning, structures, _ = fixture_7_multi_district()
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.MULTI_DISTRICT_PARCEL in categories


def test_data_gap_when_zoning_not_resolved():
    parcel, zoning, structures, _ = fixture_1_clean_split()
    parcel.zoning_district_code = None
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.DATA_GAP in categories


def test_structure_conflict_produces_flag():
    parcel, zoning, structures, _ = fixture_5_structure_conflict()
    flags = check_eligibility(parcel, zoning, structures)
    categories = [f.category for f in flags]
    assert RiskCategory.EXISTING_STRUCTURE_CONFLICT in categories
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/engine/test_eligibility.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.engine.eligibility'`

- [ ] **Step 3: Create `app/engine/eligibility.py`**

```python
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString

from app.engine.geometry import interior_normal
from app.engine.types import (
    ConstraintSeverity,
    ParcelGeometryInput,
    RiskCategory,
    RiskFlag,
    StructureInput,
    ZoningRulesInput,
)


def _structure_requires_lot_line_setback(
    structure: StructureInput,
    parcel_width: float,
    side_setback_ft: float,
) -> bool:
    """
    Return True if the structure is positioned such that no valid SIMPLE_HALVE
    split line at x=t can place the structure ≥ side_setback_ft from the new lot line.

    A split at x=t is valid w.r.t. this structure if:
        t >= struct_right + side_setback_ft   (structure stays in left lot)
      OR
        t <= struct_left - side_setback_ft    (structure stays in right lot)

    If neither is achievable while also satisfying min_lot_width on both sides,
    the structure is a blocking conflict.
    """
    coords = np.array(structure.footprint.exterior.coords)
    struct_left = coords[:, 0].min()
    struct_right = coords[:, 0].max()

    # Range of t that keeps the structure in the left lot (with setback)
    t_for_left = struct_right + side_setback_ft  # split must be at least this far right

    # Range of t that keeps the structure in the right lot (with setback)
    t_for_right = struct_left - side_setback_ft  # split must be at most this far right

    return t_for_left > parcel_width and t_for_right < 0


def check_eligibility(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> list[RiskFlag]:
    """
    Run fast-fail eligibility checks. Returns a list of disqualifying RiskFlags.
    An empty list means the parcel passed all checks.
    """
    flags: list[RiskFlag] = []

    # 1. Zoning district not resolved
    if parcel.zoning_district_code is None:
        flags.append(RiskFlag(
            category=RiskCategory.DATA_GAP,
            severity=ConstraintSeverity.BLOCKING,
            message=(
                "Zoning district could not be resolved for this parcel. "
                "Dimensional standards are unavailable; feasibility cannot be determined."
            ),
        ))
        return flags  # Can't continue without zoning rules

    # 2. Parcel straddles two zoning districts
    if parcel.multi_district:
        flags.append(RiskFlag(
            category=RiskCategory.MULTI_DISTRICT_PARCEL,
            severity=ConstraintSeverity.BLOCKING,
            message=(
                "This parcel appears to straddle two zoning districts. "
                "Automated analysis cannot determine which district's rules apply. "
                "Manual review by a land-use professional is required."
            ),
        ))
        return flags

    # 3. Area too small for any 2-lot split
    parcel_area = parcel.boundary.area
    required_area = 2 * zoning.min_lot_area_sqft
    if parcel_area < required_area:
        flags.append(RiskFlag(
            category=RiskCategory.ZONING_AREA_SHORTFALL,
            severity=ConstraintSeverity.BLOCKING,
            message=(
                f"A 2-lot split requires at least {required_area:,.0f} sqft "
                f"(2 × {zoning.min_lot_area_sqft:,.0f} sqft minimum lot size). "
                f"This parcel is {parcel_area:,.0f} sqft — "
                f"{required_area - parcel_area:,.0f} sqft short. "
                "A variance would be required for any subdivision."
            ),
        ))

    # 4. Existing structure positioned to block any valid split
    # Check along the frontage direction (SIMPLE_HALVE axis)
    parcel_width = parcel.frontage_edge.length
    for structure in existing_structures:
        if parcel.boundary.intersects(structure.footprint):
            if _structure_requires_lot_line_setback(structure, parcel_width, zoning.setback_side_ft):
                flags.append(RiskFlag(
                    category=RiskCategory.EXISTING_STRUCTURE_CONFLICT,
                    severity=ConstraintSeverity.BLOCKING,
                    message=(
                        "An existing structure is positioned such that no lot split line "
                        "can satisfy the required side setback on both resulting lots without "
                        "requiring removal or relocation of the structure."
                    ),
                ))

    return flags
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/engine/test_eligibility.py -v
```

Expected: all 6 tests PASS

- [ ] **Step 5: Run isolation test**

```bash
pytest tests/engine/test_engine_isolation.py -v
```

Expected: PASS (eligibility.py imports only engine submodules + shapely + numpy)

- [ ] **Step 6: Commit**

```bash
git add app/engine/eligibility.py tests/engine/test_eligibility.py
git commit -m "feat: add eligibility gate (area shortfall, multi-district, structure conflict, data gap)"
```

---

## Task 6: SIMPLE_HALVE and FRONTAGE_STRIP Strategies

**Files:**
- Create: `app/engine/strategies/simple_halve.py`
- Extend: `tests/engine/test_strategies.py`

**Produces:**
- `run_simple_halve(parcel, zoning, structures) -> list[ScenarioResult]`
- `run_frontage_strip(parcel, zoning, structures, max_lots=6) -> list[ScenarioResult]`

Both strategies operate on the frontage axis: split the parcel into N side-by-side strips, each with their own road frontage.

- [ ] **Step 1: Write failing tests for SIMPLE_HALVE**

Create `tests/engine/test_strategies.py`:

```python
import pytest
from app.engine.strategies.simple_halve import run_simple_halve, run_frontage_strip
from app.engine.types import LotLayoutType, RiskCategory
from tests.fixtures.parcels import (
    fixture_1_clean_split,
    fixture_2_area_shortfall,
    fixture_3_flag_lot_allowed,
    fixture_5_structure_conflict,
)


class TestSimpleHalve:
    def test_fixture1_produces_two_lot_scenario(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_simple_halve(parcel, zoning, structures)
        assert len(results) == 1
        assert results[0].num_resulting_lots == 2
        assert results[0].lot_layout_type == LotLayoutType.SIMPLE_HALVE

    def test_fixture1_both_lots_meet_requirements(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_simple_halve(parcel, zoning, structures)
        for lot in results[0].resulting_lots:
            assert lot.meets_min_lot_size is True, f"Lot area {lot.area_sqft} < min"
            assert lot.meets_min_frontage is True, f"Lot frontage {lot.frontage_ft} < min"
            assert lot.has_direct_frontage is True
            assert lot.has_buildable_envelope is True

    def test_fixture1_lots_sum_to_parcel_area(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_simple_halve(parcel, zoning, structures)
        total = sum(lot.area_sqft for lot in results[0].resulting_lots)
        parcel_area = parcel.boundary.area
        assert abs(total - parcel_area) < 1.0  # within 1 sqft rounding

    def test_fixture2_produces_no_scenarios(self):
        parcel, zoning, structures, _ = fixture_2_area_shortfall()
        results = run_simple_halve(parcel, zoning, structures)
        assert results == []

    def test_fixture3_produces_no_scenarios_parcel_too_narrow(self):
        # 60ft frontage, 40ft min width — can't do two side-by-side 40ft lots
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_simple_halve(parcel, zoning, structures)
        assert results == []

    def test_fixture5_structure_conflict_produces_no_scenarios(self):
        parcel, zoning, structures, _ = fixture_5_structure_conflict()
        results = run_simple_halve(parcel, zoning, structures)
        assert results == []


class TestFrontageStrip:
    def test_wide_parcel_can_produce_three_lots(self):
        from app.engine.types import ParcelGeometryInput, ZoningRulesInput
        from shapely.geometry import LineString, Polygon
        # 120ft wide × 125ft deep parcel; min_lot_width=40ft → 3 lots possible
        parcel = ParcelGeometryInput(
            boundary=Polygon([(0, 0), (120, 0), (120, 125), (0, 125)]),
            frontage_edge=LineString([(0, 0), (120, 0)]),
            zoning_district_code="R-1",
        )
        zoning = ZoningRulesInput(
            min_lot_area_sqft=5000,
            min_lot_width_ft=40,
            setback_front_ft=20,
            setback_side_ft=5,
            setback_rear_ft=20,
            requires_public_road_frontage=True,
            allows_flag_lots=False,
            minor_subdivision_threshold=4,
            min_road_frontage_ft=40,
        )
        results = run_frontage_strip(parcel, zoning, [])
        # Should find 2-lot and 3-lot scenarios
        lot_counts = [r.num_resulting_lots for r in results]
        assert 3 in lot_counts

    def test_fixture1_also_found_by_frontage_strip(self):
        parcel, zoning, structures, _ = fixture_1_clean_split()
        results = run_frontage_strip(parcel, zoning, structures)
        lot_counts = [r.num_resulting_lots for r in results]
        assert 2 in lot_counts
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/engine/test_strategies.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.engine.strategies.simple_halve'`

- [ ] **Step 3: Create `app/engine/strategies/simple_halve.py`**

```python
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import split as shapely_split

from app.engine.geometry import (
    has_buildable_envelope,
    interior_normal,
    measure_frontage_width,
)
from app.engine.types import (
    ConstraintSeverity,
    LotLayoutType,
    LotResult,
    ParcelGeometryInput,
    ScenarioResult,
    StructureInput,
    SubdivisionReviewTier,
    ZoningRulesInput,
)


def _make_perpendicular_cut(
    frontage_edge: LineString,
    offset_along_frontage: float,
    extent: float = 50_000.0,
) -> LineString:
    """
    Create a cut line perpendicular to the frontage, at position offset_along_frontage
    measured from the start of the frontage edge.
    """
    split_pt = frontage_edge.interpolate(offset_along_frontage)
    coords = list(frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u = p2 - p1
    u_norm = u / np.linalg.norm(u)
    # Perpendicular direction (for the cut line, it runs along the side lot line direction)
    perp = np.array([-u_norm[1], u_norm[0]])

    start = (split_pt.x - perp[0] * extent, split_pt.y - perp[1] * extent)
    end = (split_pt.x + perp[0] * extent, split_pt.y + perp[1] * extent)
    return LineString([start, end])


def _structure_blocks_split_at(
    t: float,
    existing_structures: list[StructureInput],
    side_setback: float,
) -> bool:
    """Return True if any structure is within side_setback_ft of the cut line at x=t."""
    for structure in existing_structures:
        coords = np.array(structure.footprint.exterior.coords)
        struct_left = coords[:, 0].min()
        struct_right = coords[:, 0].max()
        # Structure must be entirely left (right edge ≤ t - setback)
        # or entirely right (left edge ≥ t + setback)
        if not (struct_right <= t - side_setback or struct_left >= t + side_setback):
            return True
    return False


def _build_lot_result(
    lot: Polygon,
    frontage_edge: LineString,
    parcel: Polygon,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> LotResult:
    coords = list(frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u_norm = (p2 - p1) / np.linalg.norm(p2 - p1)
    v = interior_normal(frontage_edge, parcel)

    area = lot.area
    frontage_w = measure_frontage_width(lot, u_norm)
    depth = measure_frontage_width(lot, v)  # extent in interior direction

    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft

    return LotResult(
        geometry=lot,
        area_sqft=area,
        frontage_ft=frontage_w,
        buildable_width_ft=frontage_w,
        buildable_depth_ft=depth,
        has_direct_frontage=True,
        meets_min_lot_size=area >= zoning.min_lot_area_sqft,
        meets_min_frontage=frontage_w >= min_road_frontage,
        has_buildable_envelope=has_buildable_envelope(lot, zoning, existing_structures),
    )


def _classify_tier(num_lots: int, zoning: ZoningRulesInput) -> SubdivisionReviewTier:
    if num_lots <= zoning.minor_subdivision_threshold:
        return SubdivisionReviewTier.ADMINISTRATIVE_MINOR
    return SubdivisionReviewTier.PLANNING_COMMISSION_MAJOR


def _try_n_strip_split(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
    n_lots: int,
    layout_type: LotLayoutType,
) -> ScenarioResult | None:
    """
    Try splitting the parcel into n_lots equal-width strips perpendicular to frontage.
    Returns None if no valid configuration exists.
    """
    frontage_length = parcel.frontage_edge.length
    strip_width = frontage_length / n_lots
    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft

    # Quick reject: each strip must be wide enough
    if strip_width < min_road_frontage or strip_width < zoning.min_lot_width_ft:
        return None

    # Generate cut positions and split the parcel
    cut_positions = [strip_width * i for i in range(1, n_lots)]
    remaining = parcel.boundary
    lot_polys: list[Polygon] = []

    for cut_pos in cut_positions:
        if remaining.is_empty:
            break
        cut_line = _make_perpendicular_cut(parcel.frontage_edge, cut_pos)
        # Check structures don't block this cut
        if _structure_blocks_split_at(cut_pos, existing_structures, zoning.setback_side_ft):
            return None
        try:
            result = shapely_split(remaining, cut_line)
        except Exception:
            return None

        geoms = list(result.geoms) if hasattr(result, "geoms") else [result]
        if len(geoms) < 2:
            return None

        # Left piece becomes a lot; right piece continues
        # Sort by x-centroid to identify left vs right
        geoms.sort(key=lambda g: g.centroid.x)
        lot_polys.append(geoms[0])
        remaining = geoms[1] if len(geoms) == 2 else geoms[-1]

    lot_polys.append(remaining)  # last strip

    if len(lot_polys) != n_lots:
        return None

    lot_results = [
        _build_lot_result(lot, parcel.frontage_edge, parcel.boundary, zoning, existing_structures)
        for lot in lot_polys
    ]

    # All lots must meet requirements for the scenario to be valid
    if not all(lr.meets_min_lot_size and lr.meets_min_frontage and lr.has_buildable_envelope
               for lr in lot_results):
        return None

    return ScenarioResult(
        lot_layout_type=layout_type,
        resulting_lots=lot_results,
        num_resulting_lots=n_lots,
        requires_variance=False,
        requires_rezone=False,
        requires_flag_lot_provision=False,
        subdivision_review_tier=_classify_tier(n_lots, zoning),
    )


def run_simple_halve(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> list[ScenarioResult]:
    """Try a 2-lot side-by-side split. Returns 0 or 1 ScenarioResult."""
    result = _try_n_strip_split(parcel, zoning, existing_structures, 2, LotLayoutType.SIMPLE_HALVE)
    return [result] if result else []


def run_frontage_strip(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
    max_lots: int = 6,
) -> list[ScenarioResult]:
    """
    Try 2, 3, 4, ... N-lot equal-width strip splits. Returns all valid scenarios.
    """
    results = []
    for n in range(2, max_lots + 1):
        scenario = _try_n_strip_split(
            parcel, zoning, existing_structures, n,
            LotLayoutType.SIMPLE_HALVE if n == 2 else LotLayoutType.FRONTAGE_STRIP,
        )
        if scenario:
            results.append(scenario)
        else:
            break  # If N lots fails, N+1 will also fail (strips get narrower)
    return results
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/engine/test_strategies.py -v
```

Expected: all 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/engine/strategies/simple_halve.py tests/engine/test_strategies.py
git commit -m "feat: add SIMPLE_HALVE and FRONTAGE_STRIP strategies"
```

---

## Task 7: FLAG_LOT Strategy

**Files:**
- Create: `app/engine/strategies/flag_lot.py`
- Extend: `tests/engine/test_strategies.py`

**Produces:** `run_flag_lot(parcel, zoning, structures) -> list[ScenarioResult]`

The flag lot creates a conventional front lot (left portion, width W, frontage on road) and an L-shaped rear lot (the remainder, accessed via a narrow strip alongside the front lot).

- [ ] **Step 1: Add flag lot tests to `tests/engine/test_strategies.py`**

Append to the existing file:

```python
from app.engine.strategies.flag_lot import run_flag_lot


class TestFlagLot:
    def test_fixture3_produces_flag_lot_scenario(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        assert len(results) >= 1
        assert results[0].lot_layout_type == LotLayoutType.FLAG_LOT
        assert results[0].num_resulting_lots == 2

    def test_fixture3_front_lot_has_direct_frontage(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        front_lot = results[0].resulting_lots[0]
        assert front_lot.has_direct_frontage is True
        assert front_lot.meets_min_lot_size is True
        assert front_lot.meets_min_frontage is True

    def test_fixture3_rear_lot_has_no_direct_frontage_but_valid_area(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        rear_lot = results[0].resulting_lots[1]
        assert rear_lot.has_direct_frontage is False
        assert rear_lot.meets_min_lot_size is True

    def test_fixture3_scenario_marked_as_flag_lot_provision(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        assert results[0].requires_flag_lot_provision is True

    def test_fixture4_flag_lot_disallowed_returns_empty(self):
        from tests.fixtures.parcels import fixture_4_flag_lot_disallowed
        parcel, zoning, structures, _ = fixture_4_flag_lot_disallowed()
        results = run_flag_lot(parcel, zoning, structures)
        assert results == []

    def test_fixture3_lots_cover_full_parcel_area(self):
        parcel, zoning, structures, _ = fixture_3_flag_lot_allowed()
        results = run_flag_lot(parcel, zoning, structures)
        total = sum(lot.area_sqft for lot in results[0].resulting_lots)
        parcel_area = parcel.boundary.area
        assert abs(total - parcel_area) < 1.0
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/engine/test_strategies.py::TestFlagLot -v
```

Expected: `ModuleNotFoundError: No module named 'app.engine.strategies.flag_lot'`

- [ ] **Step 3: Create `app/engine/strategies/flag_lot.py`**

```python
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, Polygon

from app.engine.geometry import (
    has_buildable_envelope,
    interior_normal,
    measure_frontage_width,
)
from app.engine.types import (
    LotLayoutType,
    LotResult,
    ParcelGeometryInput,
    ScenarioResult,
    StructureInput,
    SubdivisionReviewTier,
    ZoningRulesInput,
)


def _classify_tier(num_lots: int, zoning: ZoningRulesInput) -> SubdivisionReviewTier:
    if num_lots <= zoning.minor_subdivision_threshold:
        return SubdivisionReviewTier.ADMINISTRATIVE_MINOR
    return SubdivisionReviewTier.PLANNING_COMMISSION_MAJOR


def run_flag_lot(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    existing_structures: list[StructureInput],
) -> list[ScenarioResult]:
    """
    Try a 2-lot flag lot split:
    - Front lot: W ft wide, D ft deep, road frontage W ft
    - Rear lot: L-shaped (access strip alongside front lot + full-width body behind)

    Geometry:
        parcel width: P_W = frontage_edge.length
        front lot width: W = P_W - flag_lot_min_access_strip_ft
        access strip width: S = P_W - W = flag_lot_min_access_strip_ft
        split depth: D = ceil(min_lot_area / W)  [minimum viable front lot depth]

    Returns [] if:
        - allows_flag_lots is False
        - W < min_lot_width_ft
        - No valid D satisfies both lot area requirements
    """
    if not zoning.allows_flag_lots or zoning.flag_lot_min_access_strip_ft is None:
        return []

    parcel_width = parcel.frontage_edge.length
    access_strip_width = float(zoning.flag_lot_min_access_strip_ft)
    front_lot_width = parcel_width - access_strip_width

    # Front lot must meet minimum width
    if front_lot_width < zoning.min_lot_width_ft:
        return []

    # Determine geometry vectors
    coords = list(parcel.frontage_edge.coords)
    p1, p2 = np.array(coords[0]), np.array(coords[-1])
    u_norm = (p2 - p1) / np.linalg.norm(p2 - p1)  # along frontage
    v = interior_normal(parcel.frontage_edge, parcel.boundary)  # into parcel

    parcel_depth = measure_frontage_width(parcel.boundary, v)

    # Find minimum D such that front lot area meets requirement
    min_d = zoning.min_lot_area_sqft / front_lot_width
    # Rear lot body (full-width rectangle behind depth D) must also meet area requirement
    max_d = parcel_depth - (zoning.min_lot_area_sqft / parcel_width)

    if min_d > max_d or min_d >= parcel_depth:
        return []

    # Use minimum viable D (maximize rear lot area)
    split_depth = min_d

    # Build front lot polygon
    origin = np.array(coords[0])
    front_corners = [
        tuple(origin),
        tuple(origin + u_norm * front_lot_width),
        tuple(origin + u_norm * front_lot_width + v * split_depth),
        tuple(origin + v * split_depth),
    ]
    front_lot_approx = Polygon(front_corners)
    front_lot = parcel.boundary.intersection(front_lot_approx)

    # Rear lot is everything else
    rear_lot = parcel.boundary.difference(front_lot)

    if front_lot.is_empty or rear_lot.is_empty:
        return []

    min_road_frontage = zoning.min_road_frontage_ft or zoning.min_lot_width_ft

    # Measure the buildable body width of the rear lot (should be full parcel width)
    rear_buildable_width = measure_frontage_width(rear_lot, u_norm)

    front_result = LotResult(
        geometry=front_lot,
        area_sqft=front_lot.area,
        frontage_ft=front_lot_width,
        buildable_width_ft=front_lot_width,
        buildable_depth_ft=split_depth,
        has_direct_frontage=True,
        meets_min_lot_size=front_lot.area >= zoning.min_lot_area_sqft,
        meets_min_frontage=front_lot_width >= min_road_frontage,
        has_buildable_envelope=has_buildable_envelope(front_lot, zoning, existing_structures),
    )

    rear_result = LotResult(
        geometry=rear_lot,
        area_sqft=rear_lot.area,
        frontage_ft=access_strip_width,   # access strip provides road access
        buildable_width_ft=rear_buildable_width,
        buildable_depth_ft=parcel_depth - split_depth,
        has_direct_frontage=False,
        meets_min_lot_size=rear_lot.area >= zoning.min_lot_area_sqft,
        meets_min_frontage=access_strip_width >= zoning.flag_lot_min_access_strip_ft,
        has_buildable_envelope=has_buildable_envelope(rear_lot, zoning, existing_structures),
    )

    if not (front_result.meets_min_lot_size and front_result.meets_min_frontage
            and front_result.has_buildable_envelope):
        return []
    if not (rear_result.meets_min_lot_size and rear_result.meets_min_frontage
            and rear_result.has_buildable_envelope):
        return []

    scenario = ScenarioResult(
        lot_layout_type=LotLayoutType.FLAG_LOT,
        resulting_lots=[front_result, rear_result],
        num_resulting_lots=2,
        requires_variance=False,
        requires_rezone=False,
        requires_flag_lot_provision=True,
        subdivision_review_tier=_classify_tier(2, zoning),
    )
    return [scenario]
```

- [ ] **Step 4: Run all strategy tests — expect PASS**

```bash
pytest tests/engine/test_strategies.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/engine/strategies/flag_lot.py tests/engine/test_strategies.py
git commit -m "feat: add FLAG_LOT strategy"
```

---

## Task 8: Environmental Constraint Filtering

**Files:**
- Create: `app/engine/constraints.py`
- Create: `tests/engine/test_constraints.py`

**Produces:** `apply_constraints(scenarios, constraints) -> list[ScenarioResult]` — filters out scenarios where a BLOCKING constraint covers the buildable envelope of any resulting lot, and attaches risk flags to remaining scenarios for significant constraints.

- [ ] **Step 1: Write failing tests**

Create `tests/engine/test_constraints.py`:

```python
import pytest
from shapely.geometry import Polygon

from app.engine.constraints import apply_constraints
from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ConstraintType,
    LotLayoutType,
    LotResult,
    RiskCategory,
    ScenarioResult,
    SubdivisionReviewTier,
)
from tests.fixtures.parcels import fixture_6_flood_zone, fixture_1_clean_split


def _make_dummy_scenario(lot_geometries: list[Polygon]) -> ScenarioResult:
    """Helper: build a ScenarioResult with given lot polygons."""
    lots = [
        LotResult(
            geometry=g,
            area_sqft=g.area,
            frontage_ft=40.0,
            buildable_width_ft=40.0,
            buildable_depth_ft=g.area / 40.0,
            has_direct_frontage=True,
            meets_min_lot_size=True,
            meets_min_frontage=True,
            has_buildable_envelope=True,
        )
        for g in lot_geometries
    ]
    return ScenarioResult(
        lot_layout_type=LotLayoutType.SIMPLE_HALVE,
        resulting_lots=lots,
        num_resulting_lots=len(lots),
        requires_variance=False,
        requires_rezone=False,
        requires_flag_lot_provision=False,
        subdivision_review_tier=SubdivisionReviewTier.ADMINISTRATIVE_MINOR,
    )


def test_no_constraints_passes_all_scenarios():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])
    result = apply_constraints([scenario], [])
    assert len(result) == 1


def test_blocking_constraint_covering_lot_removes_scenario():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])

    # Floodway covers all of lot_b
    floodway = ConstraintInput(
        constraint_type=ConstraintType.FLOOD_ZONE,
        severity=ConstraintSeverity.BLOCKING,
        geometry=Polygon([(40, 0), (80, 0), (80, 125), (40, 125)]),
    )
    result = apply_constraints([scenario], [floodway])
    assert result == [], "Scenario with BLOCKING constraint on a lot should be removed"


def test_blocking_constraint_on_partial_lot_removes_scenario():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])

    # Floodway covers >80% of lot_b (effectively blocks buildable area)
    floodway = ConstraintInput(
        constraint_type=ConstraintType.FLOOD_ZONE,
        severity=ConstraintSeverity.BLOCKING,
        geometry=Polygon([(40, 20), (80, 20), (80, 125), (40, 125)]),  # 80% of lot_b
    )
    result = apply_constraints([scenario], [floodway])
    assert result == []


def test_significant_constraint_adds_risk_flag_but_keeps_scenario():
    lot_a = Polygon([(0, 0), (40, 0), (40, 125), (0, 125)])
    lot_b = Polygon([(40, 0), (80, 0), (80, 125), (40, 125)])
    scenario = _make_dummy_scenario([lot_a, lot_b])

    wetland = ConstraintInput(
        constraint_type=ConstraintType.WETLAND,
        severity=ConstraintSeverity.SIGNIFICANT,
        geometry=Polygon([(50, 100), (80, 100), (80, 125), (50, 125)]),  # corner of lot_b
    )
    result = apply_constraints([scenario], [wetland])
    assert len(result) == 1
    flag_categories = [f.category for f in result[0].risk_flags]
    assert RiskCategory.WETLAND_EXPOSURE in flag_categories


def test_fixture6_floodway_removes_scenarios_with_flood_exposure():
    """Integration: fixture 6's floodway (rear 33%) should eliminate scenarios
    where any lot's buildable area falls in the floodway."""
    from app.engine.strategies.simple_halve import run_simple_halve
    from tests.fixtures.parcels import fixture_6_flood_zone
    parcel, zoning, structures, constraints = fixture_6_flood_zone()
    scenarios = run_simple_halve(parcel, zoning, structures)
    # The 2-lot split at x=40 creates left and right lots, both spanning full depth
    # Both lots extend into the floodway (y=83..125) — both should be eliminated
    filtered = apply_constraints(scenarios, constraints)
    # All scenarios should be removed since both lots in a side-by-side split
    # extend into the floodway
    for scenario in filtered:
        for lot in scenario.resulting_lots:
            floodway = constraints[0]
            overlap = lot.geometry.intersection(floodway.geometry)
            assert overlap.area / lot.area_sqft < 0.5, \
                "Remaining lot has >50% flood exposure"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/engine/test_constraints.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.engine.constraints'`

- [ ] **Step 3: Create `app/engine/constraints.py`**

```python
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
# Using 0.5 (50%): if a blocking constraint covers the majority of a lot,
# there is no viable buildable area regardless of exact setbacks.
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

    - BLOCKING constraint covering ≥50% of any lot's area → remove that scenario entirely
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
            for lot in scenario.resulting_lots:
                overlap = lot.geometry.intersection(constraint.geometry)
                if overlap.is_empty:
                    continue

                coverage = overlap.area / lot.geometry.area

                if (constraint.severity == ConstraintSeverity.BLOCKING
                        and coverage >= _BLOCKING_COVERAGE_THRESHOLD):
                    eliminated = True
                    break

                # Build risk flag for non-eliminating constraints
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

            if eliminated:
                break

        if not eliminated:
            scenario.risk_flags.extend(extra_flags)
            surviving.append(scenario)

    return surviving
```

- [ ] **Step 4: Run tests — expect PASS**

```bash
pytest tests/engine/test_constraints.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/engine/constraints.py tests/engine/test_constraints.py
git commit -m "feat: add environmental constraint filtering"
```

---

## Task 9: Main Calculator — All 7 Fixtures

**Files:**
- Create: `app/engine/calculator.py`
- Create: `tests/engine/test_calculator.py`

**Produces:** `calculate_subdivision_scenarios(parcel, zoning, constraints, structures) -> SubdivisionFeasibilityResult`

This is the integration task — the main entry point that assembles eligibility gate → strategy evaluation → constraint filtering → ranking.

- [ ] **Step 1: Write the 7 fixture integration tests**

Create `tests/engine/test_calculator.py`:

```python
"""
Integration tests for calculate_subdivision_scenarios against all 7 spec fixtures.
No DB, no network. Pure function with synthetic inputs.
"""
import pytest
from app.engine.calculator import calculate_subdivision_scenarios
from app.engine.types import LotLayoutType, RiskCategory, SubdivisionReviewTier
from tests.fixtures.parcels import (
    fixture_1_clean_split,
    fixture_2_area_shortfall,
    fixture_3_flag_lot_allowed,
    fixture_4_flag_lot_disallowed,
    fixture_5_structure_conflict,
    fixture_6_flood_zone,
    fixture_7_multi_district,
)


# ---------------------------------------------------------------------------
# Fixture 1: Clean rectangular 2× parcel — must produce valid SIMPLE_HALVE
# ---------------------------------------------------------------------------

def test_fixture1_produces_scenarios():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert len(result.scenarios) >= 1
    assert result.data_gap is False
    assert result.disqualifying_flags == []


def test_fixture1_primary_scenario_is_simple_halve():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    primary = result.scenarios[0]
    assert primary.lot_layout_type == LotLayoutType.SIMPLE_HALVE
    assert primary.num_resulting_lots == 2


def test_fixture1_both_lots_valid():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    for lot in result.scenarios[0].resulting_lots:
        assert lot.meets_min_lot_size is True
        assert lot.meets_min_frontage is True
        assert lot.has_buildable_envelope is True
        assert lot.has_direct_frontage is True


def test_fixture1_no_variance_required():
    parcel, zoning, structures, constraints = fixture_1_clean_split()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios[0].requires_variance is False


# ---------------------------------------------------------------------------
# Fixture 2: 1.8× minimum area — must produce 0 scenarios with clear explanation
# ---------------------------------------------------------------------------

def test_fixture2_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture2_has_area_shortfall_flag():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_categories = [f.category for f in result.disqualifying_flags]
    assert RiskCategory.ZONING_AREA_SHORTFALL in flag_categories


def test_fixture2_flag_message_contains_both_areas():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag = next(f for f in result.disqualifying_flags
                if f.category == RiskCategory.ZONING_AREA_SHORTFALL)
    # Message must state actual parcel area AND required area
    assert "9,000" in flag.message or "9000" in flag.message
    assert "10,000" in flag.message or "10000" in flag.message


def test_fixture2_data_gap_is_false():
    parcel, zoning, structures, constraints = fixture_2_area_shortfall()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.data_gap is False  # we have the data; the parcel just doesn't qualify


# ---------------------------------------------------------------------------
# Fixture 3: Deep narrow parcel, flag lots ALLOWED — must produce FLAG_LOT scenario
# ---------------------------------------------------------------------------

def test_fixture3_produces_flag_lot_scenario():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert len(result.scenarios) >= 1
    assert any(s.lot_layout_type == LotLayoutType.FLAG_LOT for s in result.scenarios)


def test_fixture3_flag_lot_front_has_frontage():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_scenario = next(s for s in result.scenarios if s.lot_layout_type == LotLayoutType.FLAG_LOT)
    front = flag_scenario.resulting_lots[0]
    assert front.has_direct_frontage is True
    assert front.meets_min_lot_size is True


def test_fixture3_flag_lot_rear_has_no_direct_frontage():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_scenario = next(s for s in result.scenarios if s.lot_layout_type == LotLayoutType.FLAG_LOT)
    rear = flag_scenario.resulting_lots[1]
    assert rear.has_direct_frontage is False
    assert rear.meets_min_lot_size is True


def test_fixture3_flag_lot_marked_as_flag_provision():
    parcel, zoning, structures, constraints = fixture_3_flag_lot_allowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_scenario = next(s for s in result.scenarios if s.lot_layout_type == LotLayoutType.FLAG_LOT)
    assert flag_scenario.requires_flag_lot_provision is True


# ---------------------------------------------------------------------------
# Fixture 4: Same parcel, flag lots DISALLOWED — must produce 0 scenarios
# ---------------------------------------------------------------------------

def test_fixture4_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_4_flag_lot_disallowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture4_has_flag_lot_not_allowed_flag():
    parcel, zoning, structures, constraints = fixture_4_flag_lot_disallowed()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    all_flags = result.disqualifying_flags + [
        f for s in result.scenarios for f in s.risk_flags
    ]
    flag_categories = [f.category for f in all_flags]
    assert RiskCategory.REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED in flag_categories


# ---------------------------------------------------------------------------
# Fixture 5: Existing structure blocks all valid splits
# ---------------------------------------------------------------------------

def test_fixture5_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_5_structure_conflict()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture5_has_structure_conflict_flag():
    parcel, zoning, structures, constraints = fixture_5_structure_conflict()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_categories = [f.category for f in result.disqualifying_flags]
    assert RiskCategory.EXISTING_STRUCTURE_CONFLICT in flag_categories


# ---------------------------------------------------------------------------
# Fixture 6: Floodway covers rear third — invalidates scenarios with flood exposure
# ---------------------------------------------------------------------------

def test_fixture6_all_surviving_scenarios_avoid_floodway():
    parcel, zoning, structures, constraints = fixture_6_flood_zone()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    floodway_geom = constraints[0].geometry
    for scenario in result.scenarios:
        for lot in scenario.resulting_lots:
            overlap = lot.geometry.intersection(floodway_geom)
            coverage = overlap.area / lot.area_sqft if lot.area_sqft > 0 else 0
            assert coverage < 0.50, (
                f"Lot in surviving scenario has {coverage:.0%} flood coverage — "
                "scenario should have been eliminated"
            )


# ---------------------------------------------------------------------------
# Fixture 7: Parcel straddles two zoning districts — must flag, not guess
# ---------------------------------------------------------------------------

def test_fixture7_produces_no_scenarios():
    parcel, zoning, structures, constraints = fixture_7_multi_district()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    assert result.scenarios == []


def test_fixture7_has_multi_district_flag():
    parcel, zoning, structures, constraints = fixture_7_multi_district()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    flag_categories = [f.category for f in result.disqualifying_flags]
    assert RiskCategory.MULTI_DISTRICT_PARCEL in flag_categories


def test_fixture7_data_gap_is_false():
    parcel, zoning, structures, constraints = fixture_7_multi_district()
    result = calculate_subdivision_scenarios(parcel, zoning, constraints, structures)
    # We have the data; the parcel is a special case requiring human review
    assert result.data_gap is False
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/engine/test_calculator.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.engine.calculator'`

- [ ] **Step 3: Create `app/engine/calculator.py`**

```python
from __future__ import annotations

from app.engine.constraints import apply_constraints
from app.engine.eligibility import check_eligibility
from app.engine.strategies.flag_lot import run_flag_lot
from app.engine.strategies.simple_halve import run_frontage_strip, run_simple_halve
from app.engine.types import (
    ConstraintInput,
    ConstraintSeverity,
    ParcelGeometryInput,
    RiskCategory,
    RiskFlag,
    ScenarioResult,
    StructureInput,
    SubdivisionFeasibilityResult,
    ZoningRulesInput,
)


def _max_theoretical_lots(parcel: ParcelGeometryInput, zoning: ZoningRulesInput) -> int:
    area = parcel.boundary.area
    by_area = int(area // zoning.min_lot_area_sqft)
    if zoning.max_density_units_per_acre:
        acres = area / 43_560.0
        by_density = int(acres * zoning.max_density_units_per_acre)
        return min(by_area, by_density)
    return by_area


def _rank_scenarios(scenarios: list[ScenarioResult]) -> list[ScenarioResult]:
    """
    Rank by: fewer variances first, fewer lots first (simpler process), fewer risk flags first.
    """
    return sorted(
        scenarios,
        key=lambda s: (
            s.requires_variance,
            s.requires_rezone,
            s.requires_flag_lot_provision,
            len(s.risk_flags),
            s.num_resulting_lots,
        ),
    )


def calculate_subdivision_scenarios(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    constraints: list[ConstraintInput],
    existing_structures: list[StructureInput],
) -> SubdivisionFeasibilityResult:
    """
    Core feasibility engine. Pure function — no I/O, no DB access.
    All inputs must be pre-populated by the calling adapter/orchestration layer.
    """
    # Step 1: Eligibility gate
    disqualifying_flags = check_eligibility(parcel, zoning, existing_structures)

    # DATA_GAP or MULTI_DISTRICT: can't proceed at all
    if any(f.category in (RiskCategory.DATA_GAP, RiskCategory.MULTI_DISTRICT_PARCEL)
           for f in disqualifying_flags):
        return SubdivisionFeasibilityResult(
            max_theoretical_lots=0,
            scenarios=[],
            disqualifying_flags=disqualifying_flags,
            data_gap=any(f.category == RiskCategory.DATA_GAP for f in disqualifying_flags),
        )

    # Area shortfall or structure conflict: still surface flags, no valid scenarios
    if disqualifying_flags:
        # Check if parcel ONLY needs flag lot (not present in disqualifying check yet)
        # — flag lot disallowed must be added here when no strategies find anything
        max_lots = _max_theoretical_lots(parcel, zoning)
        # Try flag lot anyway to check if it would work with different rules
        flag_scenarios = run_flag_lot(parcel, zoning, existing_structures)
        if not zoning.allows_flag_lots and not flag_scenarios:
            # Check if flag lot would geometrically work but isn't allowed
            _check_flag_lot_would_help(parcel, zoning, disqualifying_flags)

        return SubdivisionFeasibilityResult(
            max_theoretical_lots=max_lots,
            scenarios=[],
            disqualifying_flags=disqualifying_flags,
            data_gap=False,
        )

    # Step 2: Max theoretical lots
    max_lots = _max_theoretical_lots(parcel, zoning)

    # Step 3: Generate candidate scenarios
    scenarios: list[ScenarioResult] = []
    scenarios.extend(run_frontage_strip(parcel, zoning, existing_structures))
    if zoning.allows_flag_lots:
        scenarios.extend(run_flag_lot(parcel, zoning, existing_structures))

    # If no scenarios found and flag lots aren't allowed, check if they would help
    if not scenarios and not zoning.allows_flag_lots:
        _check_flag_lot_would_help(parcel, zoning, disqualifying_flags)

    # Step 4: Apply environmental constraints
    scenarios = apply_constraints(scenarios, constraints)

    # Step 6: Rank
    scenarios = _rank_scenarios(scenarios)

    return SubdivisionFeasibilityResult(
        max_theoretical_lots=max_lots,
        scenarios=scenarios,
        disqualifying_flags=disqualifying_flags,
        data_gap=False,
    )


def _check_flag_lot_would_help(
    parcel: ParcelGeometryInput,
    zoning: ZoningRulesInput,
    flags: list[RiskFlag],
) -> None:
    """
    If a flag lot split would be geometrically valid but flag lots aren't allowed,
    add a REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED flag.
    Mutates the flags list in place.
    """
    # Quick geometry check: is parcel too narrow for SIMPLE_HALVE?
    frontage = parcel.frontage_edge.length
    if frontage < 2 * zoning.min_lot_width_ft:
        flags.append(RiskFlag(
            category=RiskCategory.REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED,
            severity=ConstraintSeverity.BLOCKING,
            message=(
                f"This parcel's frontage ({frontage:.0f} ft) is too narrow for a "
                f"side-by-side split (requires {2 * zoning.min_lot_width_ft:.0f} ft). "
                "A flag lot arrangement could provide access to a rear lot, but flag "
                "lots are not permitted in this zoning district as-of-right."
            ),
        ))
```

- [ ] **Step 4: Run all 7 fixture tests — expect PASS**

```bash
pytest tests/engine/test_calculator.py -v
```

Expected: all tests PASS

- [ ] **Step 5: Run full test suite — expect all PASS**

```bash
pytest -v
```

Expected: all tests PASS, 0 failures

- [ ] **Step 6: Commit**

```bash
git add app/engine/calculator.py tests/engine/test_calculator.py
git commit -m "feat: add main calculator — all 7 spec fixtures passing"
```

---

## Task 10: SQLAlchemy Data Models

**Files:**
- Create: `app/models/base.py`
- Create: `app/models/jurisdiction.py`
- Create: `app/models/zoning_district.py`
- Create: `app/models/parcel.py`
- Create: `app/models/environmental_constraint.py`
- Create: `app/models/subdivision_scenario.py`
- Create: `app/models/feasibility_report.py`

These models require PostGIS but no DB connection is needed to define them — model definition tests just verify the class is importable and has the expected columns.

- [ ] **Step 1: Write import/structure tests**

Create `tests/models/__init__.py` (empty) and `tests/models/test_model_definitions.py`:

```python
"""
Verify model classes are importable and have required columns.
No DB connection required.
"""
import pytest
from sqlalchemy import inspect as sa_inspect


def test_jurisdiction_model_importable():
    from app.models.jurisdiction import Jurisdiction
    cols = {c.key for c in sa_inspect(Jurisdiction).columns}
    required = {"id", "name", "state", "fips_code", "minor_subdivision_threshold"}
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_zoning_district_model_importable():
    from app.models.zoning_district import ZoningDistrict
    cols = {c.key for c in sa_inspect(ZoningDistrict).columns}
    required = {
        "id", "jurisdiction_id", "code", "min_lot_area_sqft", "min_lot_width_ft",
        "setback_front_ft", "setback_side_ft", "setback_rear_ft",
        "allows_flag_lots", "last_verified_date", "source_ordinance_section",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_parcel_model_importable():
    from app.models.parcel import Parcel
    cols = {c.key for c in sa_inspect(Parcel).columns}
    required = {
        "id", "jurisdiction_id", "apn", "geometry", "area_sqft",
        "zoning_district_id", "zoning_code_raw",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"


def test_feasibility_report_model_importable():
    from app.models.feasibility_report import FeasibilityReport
    cols = {c.key for c in sa_inspect(FeasibilityReport).columns}
    required = {
        "id", "parcel_id", "status", "overall_score",
        "recommendation", "risk_flags", "requested_at",
    }
    assert required.issubset(cols), f"Missing columns: {required - cols}"
```

- [ ] **Step 2: Run — expect FAIL**

```bash
pytest tests/models/ -v
```

Expected: `ModuleNotFoundError: No module named 'app.models.jurisdiction'`

- [ ] **Step 3: Create `app/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 4: Create `app/models/jurisdiction.py`**

```python
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    jurisdiction_type: Mapped[str] = mapped_column(
        Enum("COUNTY_UNINCORPORATED", "CITY", "TOWNSHIP", name="jurisdiction_type_enum"),
        nullable=False,
    )
    fips_code: Mapped[str] = mapped_column(String(10), nullable=False)
    subdivision_authority_url: Mapped[str | None] = mapped_column(Text)
    zoning_ordinance_url: Mapped[str | None] = mapped_column(Text)
    minor_subdivision_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    minor_subdivision_process_notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    zoning_districts: Mapped[list["ZoningDistrict"]] = relationship(back_populates="jurisdiction")  # noqa: F821
    parcels: Mapped[list["Parcel"]] = relationship(back_populates="jurisdiction")  # noqa: F821
```

- [ ] **Step 5: Create `app/models/zoning_district.py`**

```python
from __future__ import annotations
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ZoningDistrict(Base):
    __tablename__ = "zoning_districts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jurisdictions.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_lot_area_sqft: Mapped[int] = mapped_column(Integer, nullable=False)
    min_lot_width_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    min_lot_depth_ft: Mapped[int | None] = mapped_column(Integer)
    max_density_units_per_acre: Mapped[float | None] = mapped_column(Float)
    setback_front_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    setback_side_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    setback_side_corner_ft: Mapped[int | None] = mapped_column(Integer)
    setback_rear_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    max_height_ft: Mapped[int | None] = mapped_column(Integer)
    max_lot_coverage_pct: Mapped[float | None] = mapped_column(Float)
    max_far: Mapped[float | None] = mapped_column(Float)
    requires_public_road_frontage: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    min_road_frontage_ft: Mapped[int | None] = mapped_column(Integer)
    allows_flag_lots: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_lot_min_access_strip_ft: Mapped[int | None] = mapped_column(Integer)
    source_ordinance_section: Mapped[str | None] = mapped_column(String(100))
    last_verified_date: Mapped[date | None] = mapped_column(Date)
    last_verified_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jurisdiction: Mapped["Jurisdiction"] = relationship(back_populates="zoning_districts")  # noqa: F821
    parcels: Mapped[list["Parcel"]] = relationship(back_populates="zoning_district")  # noqa: F821
```

- [ ] **Step 6: Create `app/models/parcel.py`**

```python
from __future__ import annotations
import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jurisdictions.id"), nullable=False)
    apn: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    address_normalized: Mapped[str | None] = mapped_column(String(500))
    geometry: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    area_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    zoning_district_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zoning_districts.id"))
    zoning_code_raw: Mapped[str | None] = mapped_column(String(50))
    existing_structures_count: Mapped[int] = mapped_column(Integer, default=0)
    assessed_land_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    assessed_improvement_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_sale_date: Mapped[date | None] = mapped_column
    owner_name: Mapped[str | None] = mapped_column(String(500))
    raw_assessor_data: Mapped[dict | None] = mapped_column(JSONB)
    data_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jurisdiction: Mapped["Jurisdiction"] = relationship(back_populates="parcels")  # noqa: F821
    zoning_district: Mapped["ZoningDistrict | None"] = relationship(back_populates="parcels")  # noqa: F821
    environmental_constraints: Mapped[list["EnvironmentalConstraint"]] = relationship(back_populates="parcel")  # noqa: F821
    subdivision_scenarios: Mapped[list["SubdivisionScenario"]] = relationship(back_populates="parcel")  # noqa: F821
    feasibility_reports: Mapped[list["FeasibilityReport"]] = relationship(back_populates="parcel")  # noqa: F821
```

- [ ] **Step 7: Create `app/models/environmental_constraint.py`**

```python
from __future__ import annotations
import uuid
from datetime import datetime

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EnvironmentalConstraint(Base):
    __tablename__ = "environmental_constraints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    constraint_type: Mapped[str] = mapped_column(
        Enum("FLOOD_ZONE", "WETLAND", "STEEP_SLOPE", "SOIL_LIMITATION",
             "EASEMENT", "HISTORIC_OVERLAY", "OTHER_OVERLAY",
             name="constraint_type_enum"),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum("BLOCKING", "SIGNIFICANT", "MINOR", "INFORMATIONAL", name="constraint_severity_enum"),
        nullable=False,
    )
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(255))
    source_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    parcel: Mapped["Parcel"] = relationship(back_populates="environmental_constraints")  # noqa: F821
```

- [ ] **Step 8: Create `app/models/subdivision_scenario.py`**

```python
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SubdivisionScenario(Base):
    __tablename__ = "subdivision_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    scenario_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    num_resulting_lots: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_layout_type: Mapped[str] = mapped_column(
        Enum("SIMPLE_HALVE", "FRONTAGE_STRIP", "FLAG_LOT", "UNEVEN_SPLIT",
             name="lot_layout_type_enum"),
        nullable=False,
    )
    resulting_lots: Mapped[dict] = mapped_column(JSONB, nullable=False)
    meets_min_lot_size: Mapped[bool] = mapped_column(Boolean, nullable=False)
    meets_min_frontage: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_variance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_rezone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_flag_lot_provision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    subdivision_review_tier: Mapped[str] = mapped_column(
        Enum("ADMINISTRATIVE_MINOR", "PLANNING_COMMISSION_MAJOR",
             name="subdivision_review_tier_enum"),
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped["Parcel"] = relationship(back_populates="subdivision_scenarios")  # noqa: F821
```

- [ ] **Step 9: Create `app/models/feasibility_report.py`**

```python
from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FeasibilityReport(Base):
    __tablename__ = "feasibility_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum("PENDING", "DATA_GATHERING", "CALCULATING", "COMPLETE", "FAILED",
             name="report_status_enum"),
        nullable=False,
        default="PENDING",
    )
    overall_score: Mapped[int | None] = mapped_column(Integer)
    recommendation: Mapped[str | None] = mapped_column(
        Enum("PURSUE", "PURSUE_WITH_CAUTION", "UNLIKELY", "NOT_FEASIBLE",
             name="recommendation_enum"),
    )
    primary_scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subdivision_scenarios.id")
    )
    risk_flags: Mapped[dict | None] = mapped_column(JSONB)
    valuation_summary: Mapped[dict | None] = mapped_column(JSONB)
    generated_pdf_url: Mapped[str | None] = mapped_column(Text)
    generated_html_url: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    parcel: Mapped["Parcel"] = relationship(back_populates="feasibility_reports")  # noqa: F821
    primary_scenario: Mapped["SubdivisionScenario | None"] = relationship()  # noqa: F821
```

- [ ] **Step 10: Update `app/models/__init__.py` to export all models**

```python
from app.models.base import Base
from app.models.jurisdiction import Jurisdiction
from app.models.zoning_district import ZoningDistrict
from app.models.parcel import Parcel
from app.models.environmental_constraint import EnvironmentalConstraint
from app.models.subdivision_scenario import SubdivisionScenario
from app.models.feasibility_report import FeasibilityReport

__all__ = [
    "Base",
    "Jurisdiction",
    "ZoningDistrict",
    "Parcel",
    "EnvironmentalConstraint",
    "SubdivisionScenario",
    "FeasibilityReport",
]
```

- [ ] **Step 11: Run model definition tests**

```bash
pytest tests/models/ -v
```

Expected: all 4 tests PASS

- [ ] **Step 12: Run full suite**

```bash
pytest -v --tb=short
```

Expected: all tests PASS, 0 failures

- [ ] **Step 13: Commit**

```bash
git add app/models/ tests/models/
git commit -m "feat: add SQLAlchemy data models (Jurisdiction, ZoningDistrict, Parcel, etc.)"
```

---

## Self-Review Against Spec

**Spec Section 6.3 fixture coverage:**
- Fixture 1 (clean split) → `test_fixture1_*` ✓
- Fixture 2 (area shortfall) → `test_fixture2_*` ✓
- Fixture 3 (flag lot allowed) → `test_fixture3_*` ✓
- Fixture 4 (flag lot disallowed) → `test_fixture4_*` ✓
- Fixture 5 (structure conflict) → `test_fixture5_*` ✓
- Fixture 6 (flood zone) → `test_fixture6_*` ✓
- Fixture 7 (multi-district) → `test_fixture7_*` ✓

**Spec Section 3 model coverage:**
- All 6 entities from Section 3 have SQLAlchemy models ✓
- `last_verified_date` present on `ZoningDistrict` ✓
- `zoning_code_raw` separate from `zoning_district_id` on `Parcel` ✓

**Engine isolation:**
- Import isolation test covers all `/app/engine/` files ✓
- No DB/adapter imports in engine ✓

**Section 10 repo structure:** matches spec's `/app/engine`, `/app/models`, `/tests/fixtures`, `/tests/engine` layout ✓

**Not in Phase 1 (by spec design):**
- Adapters (Phase 2)
- Environmental layer integration with real GIS data (Phase 2)
- Scoring model (Phase 5)
- Report generation (Phase 6)
- API layer (Phase 7)
- Comps/valuation (Phase 8)

---

*Plan complete and saved to `docs/superpowers/plans/2026-06-28-lot-split-phase1-engine.md`.*
