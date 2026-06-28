# Claude Code Instructions — Lot Split Feasibility

## Documentation rule (mandatory)

After any phase completion or extensive code changes, **always update all relevant docs before committing**:

| Doc | Update when |
|---|---|
| `README.md` | Any new file, endpoint, dependency, setup step, or phase status change |
| `docs/architecture.md` | Any change to data flow, layers, modules, or DB schema |
| `docs/superpowers/plans/lot-split-feasibility-spec.md` | Any phase marked complete, any architectural decision reversed |
| The relevant phase plan under `docs/superpowers/plans/` | Tasks completed, decisions made, scope changes |

Check every doc for stale references (e.g. "Phase N — pending" after that phase ships, or "Frontend (future)" after the frontend ships). Do not leave forward-looking language in docs after the thing has been built.

## Project conventions

- **Python 3.12**, venv at `.venv/`. Always activate with `source .venv/bin/activate`.
- **Run tests** with `pytest` from the project root. All tests must pass before committing.
- **Engine isolation** (`app/engine/`) is enforced by `tests/engine/test_engine_isolation.py` — never import `app.models`, `app.adapters`, `sqlalchemy`, `geoalchemy2`, or `psycopg2` inside `app/engine/`.
- **No per-jurisdiction Python files** in `app/adapters/`. Jurisdiction config lives in the `Jurisdiction` DB row.
- **Commit style**: `Phase N: short description` matching the existing log.

## Architecture in one paragraph

User uploads a parcel (GeoJSON/KML/SHP) or draws it on the OpenLayers map at `GET /`. The `/v1/parse/*` endpoints return the polygon and a labeled edge list. The user clicks the road-facing edge, fills in zoning rules, and submits to `POST /v1/feasibility`. `app/engine/inputs.py` projects the polygon from WGS84 to local feet (auto-UTM), extracts the selected edge as the frontage LineString, and passes both to `calculate_subdivision_scenarios()` — a pure function with zero I/O. The API returns scenarios, flags, and max lot count. Postgres/PostGIS is needed only for report persistence (Phase 4, pending).

## Phase status

| Phase | Status |
|---|---|
| 0 | ✅ Kyle TX zoning research |
| 1 | ✅ Feasibility engine + models (88 tests) |
| 2 | ✅ Generic ArcGIS adapter (optional APN-lookup path) |
| 3 | ✅ Geometry parsers + FastAPI (132 tests) |
| 4 | ⏳ Report persistence (needs Postgres) |
| 5 | ⏳ Report rendering (HTML/PDF) |
| 6 | ✅ Web UI (OpenLayers, file upload, edge selection, results) |
| 7 | ⏳ Scoring + financial quick-screen |
| 8 | ⏳ Pilot validation |
