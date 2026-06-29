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

## Code quality

- **No comments that describe what the code does** — only add a comment when the WHY is non-obvious (hidden constraint, workaround for a specific bug, subtle invariant). Well-named identifiers document themselves.
- **No dead code** — remove unused functions, imports, and variables rather than commenting them out. If something might be needed later, that's what git history is for.
- **No speculative abstractions** — don't generalise until there are at least three concrete cases. Three similar lines is better than a premature helper.
- **No error handling for impossible cases** — trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs, file uploads).
- **Type annotations on all function signatures** — use Python 3.12 union syntax (`X | None`) not `Optional[X]`.
- **Pydantic for all API boundaries** — never accept or return raw `dict` from an endpoint without a schema.
- **Geometry is always in feet inside the engine** — anything in WGS84 / meters must be projected before being passed to `calculate_subdivision_scenarios()`. Assert this at the boundary in `app/engine/inputs.py`, not inside the engine.

## Testing

- **Every new module gets a test file** — no untested public functions.
- **Tests must not hit the network or a real DB** — mock HTTP with `pytest-mock`; use in-memory SQLite or mock the session for DB-touching code.
- **Test the behaviour, not the implementation** — assert on return values and side effects, not on internal calls unless the call itself is the contract (e.g. an adapter's HTTP request shape).
- **Fixture files live in `tests/fixtures/`** — synthetic parcel polygons and zoning inputs used across multiple test files go there, not duplicated per file.
- **Name tests as `test_<thing>_<condition>_<expected>`** — e.g. `test_extract_edge_out_of_range_raises`.

## Git

- **Never commit with `--no-verify`** — if a hook fails, fix the underlying issue.
- **Never force-push `main`**.
- **One logical change per commit** — don't bundle unrelated fixes. If docs updates accompany a feature, include them in the same commit.
- **Always run `pytest` immediately before committing** — not just "it worked when I tested it."

## FastAPI patterns

- **Routers, not monolithic `app.py`** — each resource group gets its own file under `app/api/routes/`.
- **`HTTPException` for client errors, unhandled exceptions for server errors** — don't catch and swallow unexpected exceptions; let FastAPI return a 500 so it's visible.
- **Response models declared on every endpoint** — never rely on FastAPI's implicit serialisation of arbitrary dicts.
- **Static files mounted last** — API routers must be registered before the `StaticFiles` mount so `/v1/*` routes are never shadowed.

## Dependencies

- Pin new dependencies in `pyproject.toml` with a minimum version (`>=`) before using them.
- Install into the venv (`source .venv/bin/activate && pip install -e ".[dev]"`) and verify the import works before writing code that depends on it.
- Don't add a dependency for something that's in the standard library or already available via an existing dep.

## Architecture in one paragraph

User uploads a parcel (GeoJSON/KML/SHP) or draws it on the OpenLayers map at `GET /`. The `/v1/parse/*` endpoints return the polygon and a labeled edge list. The user clicks the road-facing edge, fills in zoning rules, and submits to `POST /v1/feasibility`. `app/engine/inputs.py` projects the polygon from WGS84 to local feet (auto-UTM), extracts the selected edge as the frontage LineString, and passes both to `calculate_subdivision_scenarios()` — a pure function with zero I/O. The API returns scenarios, flags, max lot count, and a 0–100 score with recommendation. Postgres/PostGIS is needed only for report persistence (Phase 4, pending).

## Frontend (React + MUI)

The UI lives in `frontend/` — a Vite + React 18 + MUI v5 app with OpenLayers 9.x for the map. Build outputs to `app/static/` so FastAPI continues to serve it unchanged.

- **Dev**: `cd frontend && npm run dev` (proxies `/v1` to `localhost:8000`)
- **Build**: `cd frontend && npm run build` (outputs to `app/static/`, required before committing UI changes)
- **`base: '/static/'`** in `vite.config.js` ensures built asset paths match FastAPI's `/static/*` mount
- Never edit `app/static/` by hand — it is generated by the build

### Display config (`src/config.js`)

`config.js` is the single source of truth for how API enum values map to UI labels and colors. When the backend adds a new recommendation tier, review tier, or sub-score key, add the display entry **here** — components pick it up automatically.

| Export | What it maps |
|---|---|
| `VERDICT_CONFIG` | `recommendation` string → `{label, bg, border, color}` |
| `SUBSCORE_LABELS` | sub-score key → display name |
| `REVIEW_TIER_CONFIG` | `subdivision_review_tier` → `{label, chipColor}` |
| `scoreColor(n)` | 0–100 integer → traffic-light hex color |
| `snakeToTitle(s)` | `SNAKE_CASE` / `snake_case` → `Title case` |

**Rule**: never hardcode an API enum value's label or color inside a component — put it in `config.js` and reference it by key.

### Shared layout primitives (`src/components/shared.jsx`)

Four reusable components that encode the repeated visual patterns across all sidebar panels. If you find yourself repeating an `sx` pattern more than twice, it belongs here.

| Component | Pattern it encodes | Key props |
|---|---|---|
| `SectionLabel` | Uppercase overline heading | `sx` for spacing overrides |
| `StatRow` | Label / value pair in a horizontal layout | `label`, `value`, optional `children` (for trailing chips) |
| `StatusChip` | Small categorical badge | `label`, `color` (`'green' \| 'yellow' \| 'red' \| 'gray'`) |
| `StepBox` | Panel wrapper with disabled overlay | `disabled`, `sx` |

`StatusChip` color tokens map to `CHIP_COLORS` inside `shared.jsx`. Add new semantic colors there — not inline `sx` hex values.

### Form field schemas (e.g., `FIELDS` in ZoningPanel)

When a form has more than ~3 fields, define them as a schema array rather than inline JSX. Each entry is a plain object that drives rendering, validation, and submission parsing from a single source of truth:

```js
{ key, label, type, xs, required, default, min, integer, show }
```

- `DEFAULTS` and `REQUIRED` are derived from the schema — never maintained separately.
- `show: (form) => bool` handles conditional visibility without inline `&&` expressions in JSX.
- `parseValue(field, raw)` converts form strings to typed API values based on `type`/`integer`; field components never contain parsing logic.
- Hidden fields (`show` returns false) are still submitted at their current value — the predicate controls UI only.

Adding a new field is one object in the array. No JSX changes required.

### Custom hooks (`src/hooks/`)

Extract logic into a hook when a component's `useEffect` block is long enough that its intent is not immediately obvious, or when the same lifecycle pattern would be repeated across two components.

**Naming**: `use<Subject>` — e.g., `useMapLayers`, `useFeasibilityResult`.

**OL / external object initialization**: use lazy ref initialization, not `useMemo`. React may discard memoized values, which would orphan OL objects. The null-check pattern is safe under StrictMode's double-invoke because refs persist across it:
```js
if (myRef.current === null) {
  myRef.current = new SomeExpensiveExternalObject();
}
```

**Separate builders from the hook**: write pure builder functions (`buildParcelLayer`, `buildEdgeLayer`) for the OL objects the hook creates. Pure functions are independently readable and testable without React machinery.

**No business logic in hooks**: a hook that manages a map layer belongs here; one that decides whether a parcel is viable does not — that belongs in `app/engine/`.

### MUI theme (`src/theme.js`)

The theme is the right place for font sizes, spacing, and component defaults that apply globally — not inline `sx` props on individual instances. Current overrides:

- `MuiButton`: `textTransform: none`, `fontWeight: 500` globally
- `MuiTextField`: `size: small`, `fontSize: 12` on inputs and labels globally

**Rule**: if you are adding the same `sx` prop to every instance of a MUI component, move it to the theme's `styleOverrides` instead.

## Phase status

| Phase | Status |
|---|---|
| 0 | ✅ Kyle TX zoning research |
| 1 | ✅ Feasibility engine + models (88 tests) |
| 2 | ✅ Generic ArcGIS adapter (optional APN-lookup path) |
| 3 | ✅ Geometry parsers + FastAPI (171 tests) |
| 4 | ⏳ Report persistence (needs Postgres) |
| 5 | ⏳ Report rendering (HTML/PDF) |
| 6 | ✅ Web UI (OpenLayers, file upload, edge selection, results) |
| 7 | ✅ Scoring + rule-based 0–100 score, verdict card in UI |
| 8 | ⏳ Pilot validation |
| 9 | ⏳ Batch multi-parcel analysis (FeatureCollection upload, auto edge detection, results table, CSV export) |
