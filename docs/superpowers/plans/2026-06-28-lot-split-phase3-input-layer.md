# Phase 3: Geometry Input Layer (Pivot)

**Supersedes:** `2026-06-28-lot-split-phase3-engine-wiring.md`

**Pivot rationale:** Dropped jurisdiction-specific infrastructure (TIGER road centerlines, ZoningDistrict DB population, CRS-per-county). Tool is now general-purpose: user brings their own parcel geometry and zoning rules. Works for any parcel in any jurisdiction on day one.

---

## What this phase builds

A geometry input layer that accepts a parcel from multiple sources, lets the user identify which edge faces the road, projects the polygon to local feet, and wires it into the existing engine. Plus the FastAPI skeleton and a simplified report storage model.

---

## Decisions locked in

| Decision | Choice |
|---|---|
| Frontage edge selection | User selects on map — no heuristics, no road data |
| Supported upload formats | GeoJSON, KML, Shapefile (zip) |
| Skipped formats | DXF, DWG (not common for parcel data) |
| Projection strategy | Auto-detect UTM zone from centroid → meters → convert to feet |
| Optional convenience path | Address/APN lookup via ArcGIS adapter (keep existing code) |
| Zoning rules source | User-entered form fields — no ZoningDistrict DB lookup required |
| Report storage | Single `reports` table (JSONB inputs + JSONB result) |

---

## Scope

### Task 1 — `app/parsers/` module

New module. Three parsers + one projection utility. Each parser returns a Shapely `Polygon` in EPSG:4326 (WGS84 degrees).

**`app/parsers/geojson.py`**
```python
def parse_geojson(data: dict) -> Polygon:
    """Accept a GeoJSON FeatureCollection, Feature, or raw Polygon geometry.
    Returns the first polygon found."""
```

**`app/parsers/kml.py`**
```python
def parse_kml(kml_bytes: bytes) -> Polygon:
    """Parse KML bytes (Google Maps/Earth export). Uses fastkml.
    Returns the first Placemark polygon."""
```

**`app/parsers/shapefile.py`**
```python
def parse_shapefile_zip(zip_bytes: bytes) -> Polygon:
    """Accept a zip containing .shp/.shx/.dbf/.prj. Uses fiona.
    Returns the first feature's polygon geometry."""
```

**`app/parsers/projection.py`**
```python
def project_to_feet(polygon_4326: Polygon) -> Polygon:
    """Auto-detect UTM zone from centroid, project polygon to that CRS (meters),
    then scale coordinates by 3.28084 to produce a polygon in US feet.
    Returns a Shapely Polygon suitable for passing to the engine."""

def get_utm_epsg(lon: float, lat: float) -> str:
    """Return EPSG string for the UTM zone covering this point."""
```

---

### Task 2 — `app/engine/inputs.py`

New module that bridges parsed geometry → engine input types. Engine stays untouched.

```python
def extract_edge(polygon: Polygon, edge_index: int) -> LineString:
    """Return the nth exterior edge of the polygon as a LineString.
    Raises ValueError if edge_index is out of range."""

def build_parcel_geometry_input(
    polygon_4326: Polygon,
    frontage_edge_index: int,
) -> ParcelGeometryInput:
    """Project polygon to feet, extract the selected edge as frontage_edge,
    return a ParcelGeometryInput ready for calculate_subdivision_scenarios()."""

def build_zoning_rules_input(data: dict) -> ZoningRulesInput:
    """Construct ZoningRulesInput from user-submitted form dict.
    Validates required fields are present and positive."""
```

---

### Task 3 — Simplified report model

Replace the 6-table schema with a single `reports` table for this flow. The existing models stay in place (they still apply to the optional APN-lookup path and future multi-jurisdiction features), but the core API path does not require them.

New SQLAlchemy model: `app/models/report.py`

```python
class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    geometry_geojson: Mapped[dict] = mapped_column(JSONB)        # original WGS84 input
    frontage_edge_index: Mapped[int]
    zoning_rules: Mapped[dict] = mapped_column(JSONB)            # user-entered fields
    result: Mapped[dict | None] = mapped_column(JSONB)           # engine output, serialized
    status: Mapped[str] = mapped_column(default="pending")       # pending | complete | error
    error_message: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    completed_at: Mapped[datetime | None]
```

New Alembic migration: `migrations/versions/b2_add_reports_table.py` (manual, same approach as Phase 2).

---

### Task 4 — FastAPI app skeleton

**`app/api/__init__.py`** — empty

**`app/api/app.py`**
```python
app = FastAPI(title="Lot Split Feasibility API", version="0.3.0")
app.include_router(feasibility_router, prefix="/v1")
app.include_router(parse_router, prefix="/v1/parse")
```

**`app/api/routes/feasibility.py`**

```
POST /v1/feasibility
    Body: { geometry (GeoJSON), frontage_edge_index (int), zoning (dict) }
    → build_parcel_geometry_input()
    → build_zoning_rules_input()
    → calculate_subdivision_scenarios()
    → store Report row
    → return FeasibilityResponse

GET /v1/feasibility/{report_id}
    → fetch Report row
    → return FeasibilityResponse
```

**`app/api/routes/parse.py`** — parse-and-preview endpoints (no DB write):

```
POST /v1/parse/geojson     (JSON body)
POST /v1/parse/kml         (multipart file upload)
POST /v1/parse/shapefile   (multipart file upload, zip)

All return:
{
  "polygon": { ...GeoJSON Polygon... },
  "edges": [ { "index": 0, "length_ft": 82.3 }, ... ],
  "area_sqft": 9840.0,
  "area_acres": 0.226
}
```

The `edges` array is what the frontend uses to render edge lengths and let the user pick the frontage edge before submitting to `POST /v1/feasibility`.

---

### Task 5 — Response schema

**`app/api/schemas.py`** — Pydantic models for request/response validation:

```python
class ZoningRulesRequest(BaseModel):
    district_code: str
    min_lot_area_sqft: float
    min_lot_width_ft: float
    setback_front_ft: float
    setback_side_ft: float
    setback_rear_ft: float
    requires_public_road_frontage: bool = True
    allows_flag_lots: bool = False
    flag_lot_min_access_strip_ft: float = 20.0
    minor_subdivision_threshold: int = 4

class FeasibilityRequest(BaseModel):
    geometry: dict               # GeoJSON Polygon
    frontage_edge_index: int
    zoning: ZoningRulesRequest

class ParseResponse(BaseModel):
    polygon: dict                # GeoJSON Polygon
    edges: list[dict]            # [{index, length_ft}]
    area_sqft: float
    area_acres: float

class FeasibilityResponse(BaseModel):
    report_id: str
    status: str
    max_theoretical_lots: int | None
    scenarios: list[dict]
    disqualifying_flags: list[str]
    data_gap: bool
    created_at: str
```

---

### Task 6 — `pyproject.toml` additions

```toml
[project.dependencies]
fastapi >= 0.111
uvicorn[standard] >= 0.29
python-multipart >= 0.0.9    # file uploads
fastkml >= 1.0               # KML parsing
fiona >= 1.9                 # Shapefile parsing
```

---

### Task 7 — Tests

**`tests/parsers/`** — 12 tests, no network/DB:

- `test_geojson.py` — FeatureCollection, bare Feature, bare Polygon geometry, invalid type raises
- `test_kml.py` — valid KML bytes → polygon; KML with no placemark raises
- `test_shapefile.py` — valid zip → polygon; zip missing .shp raises
- `test_projection.py` — UTM zone detection (US locations); projected polygon is in feet (area ≈ sqft within 2%); `extract_edge()` returns correct LineString; out-of-range index raises

**`tests/api/`** — 8 tests, DB mocked or SQLite in-memory:

- `test_feasibility_endpoint.py` — valid request returns 200 + FeasibilityResponse; missing field returns 422; invalid edge_index returns 400
- `test_parse_endpoint.py` — GeoJSON parse returns polygon + edges; KML upload returns polygon + edges; shapefile zip returns polygon + edges; malformed input returns 400

**`tests/engine/test_inputs.py`** — 6 tests:

- `build_parcel_geometry_input()` returns correct types; edge extraction matches polygon exterior; invalid index raises; projected area within 2% of geodetic area

---

### Task 8 — Run and validate

```bash
# Install new deps
pip install -e ".[dev]"

# Start API
uvicorn app.api.app:app --reload

# Smoke test: parse a GeoJSON, then run feasibility
curl -X POST http://localhost:8000/v1/parse/geojson \
  -H "Content-Type: application/json" \
  -d '{"type":"Polygon","coordinates":[...]}'

curl -X POST http://localhost:8000/v1/feasibility \
  -H "Content-Type: application/json" \
  -d '{"geometry":{...},"frontage_edge_index":0,"zoning":{...}}'
```

---

## Files created / modified

| File | Action |
|---|---|
| `app/parsers/__init__.py` | Create |
| `app/parsers/geojson.py` | Create |
| `app/parsers/kml.py` | Create |
| `app/parsers/shapefile.py` | Create |
| `app/parsers/projection.py` | Create |
| `app/engine/inputs.py` | Create |
| `app/models/report.py` | Create |
| `app/api/__init__.py` | Create |
| `app/api/app.py` | Create |
| `app/api/schemas.py` | Create |
| `app/api/routes/__init__.py` | Create |
| `app/api/routes/feasibility.py` | Create |
| `app/api/routes/parse.py` | Create |
| `migrations/versions/b2_add_reports_table.py` | Create |
| `pyproject.toml` | Modify — add fastapi, uvicorn, python-multipart, fastkml, fiona |
| `tests/parsers/` | Create (3 files) |
| `tests/api/` | Create (2 files) |
| `tests/engine/test_inputs.py` | Create |

**Unchanged:** all of `app/engine/`, `app/adapters/`, existing ORM models, existing tests.

---

## What comes next (Phase 4+)

| Phase | Description |
|---|---|
| 4 | Web UI — OpenLayers map, file upload, edge selection, zoning form |
| 5 | Report rendering — HTML summary + PDF export |
| 6 | Optional: address/APN lookup (geocode → ArcGIS fetch → pre-fill geometry) |
| 7 | Scoring + financial quick-screen (cost-to-split vs. lot value delta) |
