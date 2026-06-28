# Lot Split Feasibility Engine

Automated screening tool that determines whether a residential parcel can be legally subdivided, how many lots it could yield, what each would look like, and whether doing so is financially worth pursuing — without a surveyor or land-use attorney involved up front.

**Status:** Phase 2 complete. Engine + data models + parcel adapter built. Pilot jurisdiction: City of Kyle, TX.

---

## What it does

Given a parcel (by APN or address), the system:

1. Fetches parcel geometry and assessor data from the county GIS
2. Looks up the applicable zoning district's dimensional standards
3. Runs a pure-function feasibility engine that tests geometric split strategies (side-by-side strips, flag lots) against minimum lot size, frontage, and setback requirements
4. Applies environmental constraints (flood zone, wetlands, slope) per resulting lot
5. Returns ranked subdivision scenarios with risk flags and a review tier (administrative minor vs. planning commission)

Output is a `SubdivisionFeasibilityResult` — structured data suitable for rendering into a report (Phase 6).

---

## Local setup

**Prerequisites:** Python 3.12+, Docker (for PostgreSQL+PostGIS)

```bash
# Clone and create venv
git clone https://github.com/hartc17/lot-split-feasibility
cd lot-split-feasibility
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Start database
docker compose up -d

# Run migrations
alembic upgrade head

# Seed pilot jurisdiction (City of Kyle, TX)
python scripts/seed_hays_county.py

# Run tests
pytest
```

---

## Project structure

```
lot-split-feasibility/
├── app/
│   ├── engine/              # Pure feasibility calculation — zero I/O, zero DB
│   │   ├── types.py         # Input/output dataclasses (ParcelGeometryInput, etc.)
│   │   ├── geometry.py      # Shapely helpers
│   │   ├── eligibility.py   # Fast-fail checks (area, structure conflicts)
│   │   ├── strategies/      # Split strategies: strip, flag lot
│   │   ├── constraints.py   # Per-lot environmental constraint filtering
│   │   └── calculator.py    # Main entry point
│   ├── adapters/            # Data fetching layer — DB-facing, jurisdiction-generic
│   │   ├── base.py          # ParcelRecord, JurisdictionConfig, FieldMapping
│   │   ├── arcgis.py        # Generic ArcGIS REST FeatureServer adapter
│   │   ├── normalizer.py    # GeoJSON → Parcel fields, geodetic area calculation
│   │   ├── zoning_mapper.py # Raw GIS zoning string → ZoningDistrict.id
│   │   └── ingestion.py     # Orchestrates fetch + normalize + DB upsert
│   └── models/              # SQLAlchemy ORM models (PostgreSQL + PostGIS)
│       ├── jurisdiction.py  # Includes GIS adapter config (gis_field_map, etc.)
│       ├── zoning_district.py
│       ├── parcel.py
│       ├── environmental_constraint.py
│       ├── subdivision_scenario.py
│       └── feasibility_report.py
├── migrations/              # Alembic migrations
│   └── versions/
│       └── a1f1873cc084_initial_schema.py
├── tests/
│   ├── engine/              # Unit tests — no DB, no network (88 total, all passing)
│   ├── adapters/            # Adapter tests — HTTP mocked, no DB
│   ├── models/              # Model structure tests via sqlalchemy.inspect
│   └── fixtures/            # Synthetic parcel/zoning fixtures (spec §6.3)
├── scripts/
│   ├── seed_hays_county.py  # One-time DB seed for Kyle TX jurisdiction row
│   └── validate_parcels.py  # CLI spot-check of real APNs against county GIS
├── docs/
│   ├── architecture.md      # System + engine + ER diagrams (Mermaid)
│   ├── pilot-jurisdiction.md # Kyle TX GIS sources, zoning districts, open items
│   └── superpowers/plans/   # Phase plan documents
├── docker-compose.yml       # PostgreSQL 16 + PostGIS 3.4
├── pyproject.toml
└── alembic.ini
```

---

## Architecture

See [docs/architecture.md](docs/architecture.md) for full Mermaid diagrams.

### Key design decisions

**Engine isolation.** `app/engine/` is a pure function — it has zero imports from `app/models`, `app/adapters`, SQLAlchemy, or any I/O module. This is enforced at test time by an AST scanner (`tests/engine/test_engine_isolation.py`). The engine takes plain Python dataclasses in, returns plain Python dataclasses out. It can be unit-tested without a database or network connection.

**DB-driven jurisdiction config.** The `Jurisdiction` table stores all county-specific GIS adapter configuration (`gis_feature_server_url`, `gis_field_map`, `gis_zoning_code_map`). Adding a new jurisdiction means inserting a DB row via a seed script — zero new Python files in `app/adapters/`.

**Generic ArcGIS adapter.** A single `ArcGISParcelAdapter` class works for any county running Esri ArcGIS Server. ~3,100 US counties use ArcGIS; the adapter is parameterized by a `JurisdictionConfig` built from the `Jurisdiction` DB record at runtime.

**Hand-encoded zoning rules.** Per the spec, zoning dimensional standards are manually entered into `ZoningDistrict` rows — not scraped or inferred. Every row requires a `source_ordinance_section` citation and `last_verified_date` before it can be used in production.

---

## Pilot jurisdiction: City of Kyle, TX

Kyle is within Hays County, TX. Texas counties cannot exercise general zoning authority — only incorporated cities can. Kyle has a complete zoning ordinance (Chapter 53) with 5 residential districts (R-1-1, R-1-2, R-1-3, UE, A) and a 4-lot minor subdivision threshold (Texas LGC §212.0065).

See [docs/pilot-jurisdiction.md](docs/pilot-jurisdiction.md) for GIS sources, dimensional standards, and open items before Phase 3.

---

## Build phases

| Phase | Status | Description |
|---|---|---|
| 0 | ✅ Complete | Jurisdiction selection + zoning data research |
| 1 | ✅ Complete | Core feasibility engine + SQLAlchemy models, 88 tests passing |
| 2 | ✅ Complete | Generic ArcGIS parcel adapter, Alembic migrations, DB seed |
| 3 | Pending | Wire real parcels through the engine |
| 4 | Pending | Environmental constraint adapters (FEMA, NWI, SSURGO) |
| 5 | Pending | Scoring & risk model |
| 6 | Pending | Report generation (HTML + PDF) |
| 7 | Pending | FastAPI endpoints + async job queue |
| 8 | Pending | Comps/valuation layer |
| 9 | Pending | Pilot validation (50–100 real parcels) |

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
print(result.max_theoretical_lots)   # → 1 (10,000 sqft parcel / 6,825 min = 1)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 |
| Geometry | Shapely 2.x + pyproj (geodetic area via Geod) |
| ORM | SQLAlchemy 2.x + GeoAlchemy2 |
| Database | PostgreSQL 16 + PostGIS 3.4 |
| Migrations | Alembic |
| HTTP client | requests |
| Testing | pytest + pytest-mock |
| Future: API | FastAPI |
| Future: Queue | Celery + Redis |
| Future: Reports | Jinja2 + Playwright |
