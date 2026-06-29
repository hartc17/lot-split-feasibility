# Phase 9: Multi-Parcel Workspace

**Goal:** Support multiple parcels in a single session. Any number of parcels can be added to the map — via individual file uploads (including multi-file), by drawing — in any combination. Clicking a parcel on the map makes it active; the sidebar then operates on that parcel's edge selection, zoning rules, feasibility result, and shape.

---

## Decisions locked in

| Decision | Choice | Rationale |
|---|---|---|
| Parcel identity | Client-generated UUID per parcel | Stable across re-renders; no server round-trip |
| Active parcel | One active at a time; clicking the map selects | Sidebar is already a single-parcel workflow — no redesign needed |
| Per-parcel state | Each parcel carries its own edges, selected edge indices, zoning form, and results | Switching parcels restores that parcel's exact state |
| Multi-file upload | `<input multiple>` — each file becomes one parcel | Natural OS behaviour; each file parsed independently |
| Multi-draw | After a draw completes the draw interaction stays active | User keeps drawing until they explicitly cancel |
| Shape editing | OL Modify interaction on the active drawn parcel | Upload-derived shapes are read-only (GIS authority) |
| Zoning defaults | New parcels inherit the last-used zoning form values | Avoids re-entering the same district's rules for every parcel |
| Delete parcel | Trash icon per parcel in the parcel list panel | Removes from map and state |
| No batch submit | Feasibility runs one parcel at a time on demand | User controls when to run each parcel |

---

## State model

Replace the current single-parcel flat state in `App.jsx` with a parcel collection:

```js
// One entry per parcel on the map
{
  id: string,                  // uuid
  source: 'upload' | 'draw',
  label: string,               // filename or "Drawn parcel N"
  polygon4326: object,         // GeoJSON Polygon
  edges: EdgeInfo[],
  selectedEdgeIndices: int[],
  zoningForm: object,          // current form values for this parcel
  results: object | null,      // last feasibility response
  loading: boolean,
}

// App-level
parcels: Parcel[]
activeParcellId: string | null
```

All sidebar panels (`EdgePanel`, `ZoningPanel`, `ResultsPanel`) read/write via the active parcel. Switching active parcel restores that parcel's sidebar state instantly.

---

## Scope

### Task 1 — Parcel state management

**`frontend/src/hooks/useParcels.js`** — new hook:

```js
export function useParcels(defaultZoningForm) {
  // add(source, label, polygon4326, edges) → id
  // update(id, patch)
  // remove(id)
  // setActive(id)
  // activeParcel  (derived)
  return { parcels, activeParcellId, activeParcel, add, update, remove, setActive };
}
```

`add()` initialises `selectedEdgeIndices: []`, `zoningForm: {...defaultZoningForm}`, `results: null`.

No business logic in this hook — it manages a list and delegates everything else to the sidebar.

---

### Task 2 — Map: multi-parcel layers

**`frontend/src/hooks/useMapLayers.js`** — refactor from single parcel/edge source pair to a dynamic layer registry:

```js
// Instead of one parcelSource + one edgeSource,
// maintain a Map keyed by parcel id:
//   layerRegistry: Map<id, { parcelLayer, edgeLayer, parcelSource, edgeSource }>
// addParcelToMap(id, polygon4326, edges)
// removeParcelFromMap(id)
// setActiveParcel(id)   ← moves the "selected" highlight
```

Parcel layers: inactive parcels render with a faded stroke; active parcel renders with the current blue fill. Edge labels only shown for the active parcel.

Map click handler resolves which parcel was hit first and calls `setActive(id)` before delegating to edge selection.

---

### Task 3 — Multi-file upload

**`frontend/src/components/UploadPanel.jsx`**:
- `<input multiple>` on the file input
- On change, iterate `e.target.files` — call `parseFile` for each, call `add()` for each success
- Errors per-file shown inline (not a global alert) so one bad file doesn't block the rest

---

### Task 4 — Multi-draw

**`frontend/src/components/UploadPanel.jsx`** + **`MapView.jsx`**:
- "Draw" button starts draw mode as today
- On `drawend`: add the new parcel, call `setActive(newId)`, but **leave draw mode on** so the next polygon can be drawn immediately
- "Stop Drawing" button (replaces "Cancel Draw") exits draw mode
- Each completed polygon becomes its own parcel entry

---

### Task 5 — Shape editing for drawn parcels

**`MapView.jsx`** — add an OL `Modify` interaction on the active parcel's layer when `activeParcel.source === 'draw'`:

- `modifyend` re-parses the modified geometry via `/v1/parse/geojson`, updates parcel state (`polygon4326`, `edges`), clears `selectedEdgeIndices` and `results`
- Upload-derived parcels: no Modify interaction; edit button is hidden in the sidebar

---

### Task 6 — Parcel list panel

**`frontend/src/components/ParcelListPanel.jsx`** — new component above `EdgePanel` in the sidebar:

```
┌─────────────────────────────────┐
│ PARCELS                         │
│ ● R21450.geojson   92 ✓  🗑    │  ← active (has result)
│ ○ R14820.geojson   —           │  ← inactive (no result yet)
│ ○ Drawn parcel 1   —           │  ← drawn, no result
└─────────────────────────────────│
```

- Bullet filled = active parcel
- Score shown if results exist
- Trash icon removes the parcel
- Clicking a row calls `setActive(id)` and flies the map to that parcel's extent

---

### Task 7 — Sidebar wiring

`App.jsx` passes `activeParcel.*` down to `EdgePanel`, `ZoningPanel`, `ResultsPanel`. On zoning form change or edge toggle, call `update(activeParcellId, patch)` to persist state per parcel.

`ZoningPanel` receives `initialValues` (the active parcel's `zoningForm`) and an `onChange` handler instead of managing its own isolated state — so form values survive parcel switching.

---

### Task 8 — Tests

**`tests/` (frontend — Vitest if added, else manual)**: Not required in this phase. The backend is unchanged; existing 171 pytest tests continue to cover it.

No new backend code in this phase.

---

## Out of scope for this phase

- Batch submit of all parcels at once
- Per-parcel different API endpoints (all still use `/v1/parse/*` + `/v1/feasibility`)
- Saving the session / sharing a multi-parcel workspace (Phase 4 persistence)
- Shape editing for upload-derived parcels
