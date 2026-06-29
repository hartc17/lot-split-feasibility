# Phase 9: Batch Multi-Parcel Analysis

**Goal:** Allow a user to submit multiple parcels in a single request, apply one set of zoning rules to all of them, and receive a ranked results table — enabling portfolio screening of a neighborhood or a list of addresses without repeating the single-parcel flow N times.

---

## Decisions locked in

| Decision | Choice | Rationale |
|---|---|---|
| Input format | GeoJSON FeatureCollection (multiple features in one file) | Single upload, standard format; works with county GIS exports |
| Road edge selection | Auto-detect longest exterior edge per parcel | Manual selection per parcel is not viable at scale |
| Zoning rules | One set of rules applied to all parcels | Batch mode implies a neighborhood sweep sharing a zoning district |
| API design | New endpoint `POST /v1/batch-feasibility` | Keeps single-parcel flow unchanged; batch is a distinct call |
| Processing | Synchronous, sequential, up to 50 parcels per request | Avoids async job queue complexity; 50 parcels runs in < 2s |
| UI layout | New "Batch" mode toggle in UploadPanel; results render as a sortable table below the map | Reuses existing sidebar + map layout; table replaces ResultsPanel |
| Export | CSV download of the results table | Minimal; no PDF/HTML per-parcel report in this phase |
| Parcel identity | Use GeoJSON feature `properties.PROP_ID` or `properties.id` if present; otherwise `parcel_N` | Hays County GIS exports include PROP_ID |

---

## Scope

### Task 1 — Auto edge detection utility

**`app/engine/inputs.py`** — new function:

```python
def detect_road_edge_index(polygon: Polygon) -> int:
    """Return the index of the longest exterior edge as the road-facing heuristic.
    Used when the user has not manually selected a frontage edge."""
    coords = list(polygon.exterior.coords)
    num_edges = len(coords) - 1
    return max(range(num_edges), key=lambda i: LineString([coords[i], coords[i+1]]).length)
```

No new tests beyond the existing `extract_edges` suite — behaviour is trivially a `max()` over a list.

---

### Task 2 — Batch API endpoint

**`app/api/schemas.py`** — new schemas:

```python
class BatchParcelInput(BaseModel):
    geometry: dict = Field(..., description="GeoJSON Polygon (EPSG:4326)")
    id: str = ""  # PROP_ID or caller-supplied label; auto-assigned if blank

class BatchFeasibilityRequest(BaseModel):
    parcels: list[BatchParcelInput] = Field(..., min_length=1, max_length=50)
    zoning: ZoningRulesRequest

class BatchParcelResult(BaseModel):
    id: str
    index: int                        # 0-based position in input list
    score: int | None
    recommendation: str | None
    max_theoretical_lots: int | None
    scenario_count: int
    disqualifying_flags: list[str]
    data_gap: bool
    road_edge_index: int              # auto-detected edge used

class BatchFeasibilityResponse(BaseModel):
    total: int
    results: list[BatchParcelResult]
```

**`app/api/routes/batch.py`** — new route `POST /v1/batch-feasibility`:

- Iterate parcels; for each:
  - Parse geometry
  - Call `detect_road_edge_index` on the projected polygon
  - Call `build_parcel_geometry_input([road_edge_index])`
  - Call `calculate_subdivision_scenarios`
  - Call `score_result`
- Collect into `BatchFeasibilityResponse`
- Individual parse failures return `data_gap: true` with the error in `disqualifying_flags` rather than aborting the whole batch

Register router in `app/api/app.py` under `/v1`.

---

### Task 3 — Parse endpoint: accept FeatureCollection

**`app/parsers/geojson.py`** — extend `parse_geojson` (or add `parse_geojson_collection`) to handle a GeoJSON FeatureCollection input, returning `list[tuple[str, Polygon]]` (id + polygon pairs).

**`app/api/routes/parse.py`** — new endpoint `POST /v1/parse/geojson-collection`:

- Accepts a FeatureCollection
- Returns a `ParseCollectionResponse` with one `ParseResponse` per feature (polygon + edges + area), preserving feature `id`/`PROP_ID`
- This lets the UI preview all parcels on the map before submitting

---

### Task 4 — Frontend: batch mode

**`frontend/src/components/UploadPanel.jsx`** — add a "Batch mode" toggle (MUI `Switch`). When on, file input accepts a single `.geojson` and calls `POST /v1/parse/geojson-collection` instead of the single-parcel parse.

**`frontend/src/App.jsx`** — new state:
```js
const [batchMode, setBatchMode] = useState(false);
const [batchParcels, setBatchParcels] = useState([]);  // [{id, polygon, edges}]
const [batchResults, setBatchResults] = useState(null);
```

Batch submit path: collect `batchParcels` geometries + current zoning form → `POST /v1/batch-feasibility` → render `BatchResultsTable`.

**`frontend/src/components/BatchResultsTable.jsx`** — new component:

- MUI `Table` sorted by score descending by default
- Columns: ID · Score · Recommendation (colored chip) · Max lots · Scenarios · Flags
- Click a row → fly map to that parcel + highlight it
- "Download CSV" button

---

### Task 5 — Tests

**`tests/api/test_batch_endpoint.py`**:
- Valid 3-parcel request → 200, 3 results
- Parcel with unparseable geometry → result has `data_gap: true`, rest succeed
- Over-limit (51 parcels) → 422
- Empty parcels list → 422

**`tests/engine/test_inputs.py`** — add `test_detect_road_edge_index_returns_longest`.

---

## Out of scope for this phase

- Per-parcel zoning rules (all share one set)
- Manual edge override per parcel in batch mode
- Async/job-queue processing for > 50 parcels
- Map-drawn batch parcels (upload only)
- Per-parcel HTML/PDF report (Phase 5)
