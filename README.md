# Lot Split Feasibility Engine

Automated screening tool that determines whether a residential parcel can be legally subdivided, how many lots it could yield, what each would look like, and whether doing so is financially worth pursuing — without a surveyor or land-use attorney involved up front.

**Status:** Phase 3 complete. Engine + geometry parsers + FastAPI endpoints built and tested. Works for any parcel in any US jurisdiction.

---

## What it does

The user provides a parcel and zoning rules. The system:

1. Accepts parcel geometry from a file upload (GeoJSON, KML, Shapefile), a map draw, or an optional APN lookup
2. Projects the geometry from WGS84 to local feet (auto-UTM)
3. Lets the user identify which edge faces the road
4. Runs a pure-function feasibility engine that tests geometric split strategies (side-by-side strips, flag lots) against the user-entered zoning rules (minimum lot size, frontage, setbacks)
5. Returns ranked subdivision scenarios with risk flags and a review tier (administrative minor vs. planning commission)

Output is a `FeasibilityResponse` — structured data ready for report rendering (Phase 5).

---

## Local setup

**Prerequisites:** Python 3.12+

```bash
git clone https://github.com/hartc17/lot-split-feasibility
cd lot-split-feasibility
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Run tests
pytest

# Start API
uvicorn app.api.app:app --reload
```

PostgreSQL + Docker are only needed once the report persistence feature is activated (Phase 4+):

```bash
docker compose up -d
alembic upgrade head
```

---

## Project structure

```
lot-split-feasibility/
├── app/
│   ├── engine/              # Pure feasibility calculation — zero I/O, zero DB
│   │   ├── types.py         # Input/output dataclasses
│   │   ├── geometry.py      # Shapely helpers
│   │   ├── eligibility.py   # Fast-fail checks (area, structure conflicts)
│   │   ├── strategies/      # Split strategies: strip, flag lot
│   │   ├── constraints.py   # Per-lot environmental constraint filtering
│   │   ├── inputs.py        # Bridge: parsed geometry + user form → engine types
│   │   └── calculator.py    # Main entry point
│   ├── parsers/             # File format parsers — WGS84 Polygon out, no DB
│   │   ├── geojson.py       # GeoJSON (FeatureCollection, Feature, bare Polygon)
│   │   ├── kml.py           # KML (Google Maps/Earth export)
│   │   ├── shapefile.py     # Shapefile zip (.shp + sidecar files)
│   │   └── projection.py    # WGS84 → local feet (auto-UTM zone detection)
│   ├── api/                 # FastAPI app
│   │   ├── app.py           # App + router registration
│   │   ├── schemas.py       # Pydantic request/response models
│   │   └── routes/
│   │       ├── parse.py     # POST /v1/parse/{geojson,kml,shapefile}
│   │       └── feasibility.py  # POST /v1/feasibility, GET /v1/feasibility/{id}
│   ├── adapters/            # Optional: ArcGIS parcel fetch (convenience path)
│   │   ├── base.py          # ParcelRecord, JurisdictionConfig
│   │   ├── arcgis.py        # Generic ArcGIS REST adapter (any county)
│   │   ├── normalizer.py    # GeoJSON → Parcel fields, geodetic area
│   │   ├── zoning_mapper.py # Raw GIS code → ZoningDistrict (DB-backed)
│   │   └── ingestion.py     # Orchestrates fetch + normalize + DB upsert
│   └── models/              # SQLAlchemy ORM models (PostgreSQL + PostGIS)
│       ├── report.py        # Primary model: stores geometry + rules + result
│       ├── jurisdiction.py  # Optional: multi-jurisdiction config
│       ├── zoning_district.py
│       ├── parcel.py
│       ├── environmental_constraint.py
│       ├── subdivision_scenario.py
│       └── feasibility_report.py
├── migrations/              # Alembic migrations
├── tests/
│   ├── engine/              # Unit tests — no DB, no network (100+ tests, all passing)
│   ├── parsers/             # Parser + projection tests — no DB, no network
│   ├── api/                 # Endpoint tests — DB mocked
│   ├── adapters/            # Adapter tests — HTTP mocked, no DB
│   ├── models/              # Model structure tests
│   └── fixtures/            # Synthetic parcel/zoning fixtures (spec §6.3)
├── scripts/
│   ├── seed_hays_county.py  # Optional: seed Kyle TX jurisdiction for APN-lookup path
│   └── validate_parcels.py  # Optional: CLI spot-check of real APNs
├── docs/
│   ├── architecture.md      # System + engine diagrams (Mermaid)
│   ├── pilot-jurisdiction.md # Kyle TX zoning reference data
│   └── superpowers/plans/   # Phase plan documents
├── docker-compose.yml       # PostgreSQL 16 + PostGIS 3.4 (for persistence)
├── pyproject.toml
└── alembic.ini
```

---

## API

Start the server: `uvicorn app.api.app:app --reload`

### Parse endpoints — return polygon + labeled edges, no DB write

```
POST /v1/parse/geojson     JSON body: GeoJSON Polygon/Feature/FeatureCollection
POST /v1/parse/kml         Multipart file upload (.kml)
POST /v1/parse/shapefile   Multipart file upload (.zip containing .shp + sidecars)

Response:
{
  "polygon": { ...GeoJSON Polygon... },
  "edges": [ { "index": 0, "length_ft": 82.3 }, ... ],
  "area_sqft": 9840.0,
  "area_acres": 0.226
}
```

The frontend uses the `edges` list to render each edge with its length, letting the user click the road-facing side before submitting.

### Feasibility endpoint

```
POST /v1/feasibility
{
  "geometry": { ...GeoJSON Polygon... },
  "frontage_edge_index": 0,
  "zoning": {
    "district_code": "R-1-2",
    "min_lot_area_sqft": 6825,
    "min_lot_width_ft": 65,
    "setback_front_ft": 25,
    "setback_side_ft": 8,
    "setback_rear_ft": 15,
    "minor_subdivision_threshold": 4,
    "allows_flag_lots": false
  }
}

Response:
{
  "report_id": null,
  "status": "complete",
  "max_theoretical_lots": 2,
  "scenarios": [ ... ],
  "disqualifying_flags": [],
  "data_gap": false
}
```

---

## Running the engine directly

```python
from shapely.geometry import Polygon, LineString
from app.engine.calculator import calculate_subdivision_scenarios
from app.engine.types import ParcelGeometryInput, ZoningRulesInput

parcel = ParcelGeometryInput(
    boundary=Polygon([(0,0),(80,0),(80,125),(0,125),(0,0)]),
    frontage_edge=LineString([(0,0),(80,0)]),
    zoning_district_code="R-1-2",
)
zoning = ZoningRulesInput(
    min_lot_area_sqft=6825,
    min_lot_width_ft=65,
    setback_front_ft=25,
    setback_side_ft=8,
    setback_rear_ft=15,
    requires_public_road_frontage=True,
    allows_flag_lots=False,
    minor_subdivision_threshold=4,
)
result = calculate_subdivision_scenarios(parcel, zoning, constraints=[], existing_structures=[])
print(result.max_theoretical_lots)
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for full Mermaid diagrams.

### Key design decisions

**Engine isolation.** `app/engine/` is a pure function — zero imports from `app/models`, `app/adapters`, SQLAlchemy, or any I/O module. Enforced at test time by an AST scanner (`tests/engine/test_engine_isolation.py`). Takes plain Python dataclasses in, returns plain Python dataclasses out. Unit-testable without a database or network connection.

**User-provided geometry and rules.** The primary flow does not require county GIS integration or a jurisdiction database. The user supplies parcel geometry (upload or draw) and zoning rules (web form). This makes the tool work for any parcel in any US jurisdiction on day one.

**Auto-UTM projection.** Uploaded geometry arrives in WGS84. `app/parsers/projection.py` auto-detects the UTM zone from the parcel centroid, projects to meters, and scales to US feet — no per-jurisdiction CRS configuration required.

**User-selected frontage edge.** After parsing, the API returns each polygon edge with its length in feet. The frontend displays these so the user can click the road-facing side. No road centerline dataset or spatial join required.

**Optional APN-lookup path.** The Phase 2 ArcGIS adapter (`app/adapters/`) remains available as a convenience path: given an APN, it fetches geometry from a county GIS and returns it in the same format as a file upload. Adding a new county that runs ArcGIS requires only a DB row, not new Python code.

---

## Build phases

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Jurisdiction research + zoning data (Kyle TX reference) |
| 1 | ✅ Complete | Core feasibility engine + SQLAlchemy models, 88 tests passing |
| 2 | ✅ Complete | Generic ArcGIS parcel adapter (optional path), Alembic migrations |
| 3 | ✅ Complete | Geometry parsers (GeoJSON/KML/SHP), projection, FastAPI endpoints, 132 tests |
| 4 | Pending | Report persistence (reports table → Postgres) |
| 5 | Pending | Report rendering (HTML + PDF) |
| 6 | Pending | Web UI — map, file upload, edge selection, zoning form |
| 7 | Pending | Scoring + financial quick-screen |
| 8 | Pending | Pilot validation (50–100 real parcels) |

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Geometry | Shapely 2.x + pyproj (geodetic area + UTM projection) |
| File parsing | fastkml (KML), fiona (Shapefile), built-in json (GeoJSON) |
| API | FastAPI + uvicorn |
| Request validation | Pydantic v2 |
| ORM | SQLAlchemy 2.x + GeoAlchemy2 |
| Database | PostgreSQL 16 + PostGIS 3.4 (persistence, pending) |
| Migrations | Alembic |
| HTTP client | requests (APN-lookup path only) |
| Testing | pytest + pytest-mock + httpx2 (TestClient) |
| Future: Reports | Jinja2 + Playwright |
| Future: UI | OpenLayers (map + edge selection) |
