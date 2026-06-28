# Lot Split Feasibility Engine — Technical Specification

**Status:** Draft v1 for initial implementation
**Audience:** Claude Code (autonomous build agent) and the engineer directing it
**Purpose:** This document specifies a system that takes a single property (address or parcel ID) and determines whether that parcel can likely be legally subdivided into multiple lots, how many lots, what each would look like, and whether doing so is probably worth the cost — without a human pulling zoning code or ordering a survey first.

> **How to use this document:** Read the whole spec before writing code. Section 12 (Build Sequence) defines the intended order of work — start there for "what do I do first." Section 4 (Pilot Jurisdiction Selection) and Section 5.2 (zoning rule encoding) require a human decision/research step before Phase 1 can really be validated; if no jurisdiction has been chosen yet, surface that as the first question rather than picking one arbitrarily. Section 6.3's fixtures are the acceptance criteria for the most important component in the system — treat them as required, not optional, before moving to later phases.

---

## 1. Problem Statement & Scope

### 1.1 The core question this system answers

> "Given this parcel, can it probably be split into 2+ lots, what would the resulting lots look like, what's likely to block it, and is it financially worth pursuing?"

This is currently answered by: a land surveyor or land-use attorney manually pulling the zoning ordinance, checking dimensional standards (minimum lot size, frontage, setbacks), checking site constraints (flood, slope, wetlands, septic suitability), and sanity-checking against comps — a process that takes days and costs $1,500–$5,000 in professional fees per parcel. This system automates a *screening-grade* version of that analysis, which is intentionally less authoritative than a final survey/plat but good enough to make a go/no-go decision before spending real money.

### 1.2 Explicit non-goals for v1

- This is **not** a CAD/survey tool. It does not produce a legally recordable plat. Output geometry is approximate, derived from public GIS layers, not a licensed survey.
- This is **not** a general zoning-compliance checker (that space is already commoditized — see note below). The differentiated product is specifically the **subdivision/lot-split feasibility question**: "how many lots, what configuration, is it worth it" — not "what can I build here."
- v1 covers **single-jurisdiction pilot** scope (one county or one city), not nationwide coverage. Nationwide zoning-rule ingestion is the single hardest and most time-consuming part of this problem; do not attempt it before the core engine works end-to-end for one place.
- v1 does not handle commercial/industrial subdivision, only residential (single-family / rural residential zoning districts). Commercial subdivision has different and more complex dimensional standards and is a v2+ concern.
- v1 does not attempt to model variance/rezoning probability with any sophistication — it flags "this requires a variance/rezone" as a risk factor and stops there. Predicting approval odds is a future enhancement, not a v1 requirement.

### 1.3 Why this niche specifically (context, not a design constraint)

General zoning-feasibility checking (e.g. "can I build an ADU here", "is this compliant") is being actively commoditized by multiple competitors and by municipal AI permitting tools as of 2026. Subdivision/lot-split feasibility screening is not — the existing tools in that space are either CAD/survey software for professionals after the decision is made, or enterprise GIS platforms priced for large developers. This spec targets the gap: a self-serve, automated, parcel-level pre-screening report for small land investors, infill builders, and individual property owners, priced as a single report rather than a platform subscription. This context shapes a few decisions below (e.g., why output is a discrete report object, not a persistent multi-user workspace) but does not otherwise change the technical design.

---

## 2. System Architecture

### 2.1 High-level component diagram (textual)

```
                              ┌─────────────────────────┐
                              │   Client (web form)     │
                              │  address/parcel input   │
                              └────────────┬─────────────┘
                                           │
                                           ▼
                              ┌─────────────────────────┐
                              │   API Gateway / BFF      │
                              │  (FastAPI or similar)    │
                              └────────────┬─────────────┘
                                           │
                  ┌────────────────────────┼────────────────────────┐
                  ▼                        ▼                        ▼
       ┌────────────────────┐  ┌─────────────────────┐  ┌──────────────────────┐
       │ Geocoding /         │  │ Parcel Resolution    │  │ Job Queue            │
       │ Address Resolution  │  │ Service               │  │ (async report jobs)  │
       └─────────┬───────────┘  └──────────┬────────────┘  └──────────┬────────────┘
                  │                         │                          │
                  └─────────────┬───────────┘                          │
                                ▼                                      │
                  ┌──────────────────────────────┐                     │
                  │  Data Aggregation Layer       │ ◄───────────────────┘
                  │  (pulls + normalizes raw data) │
                  └──────────────┬─────────────────┘
                                 │
        ┌────────────┬──────────┼──────────┬─────────────┐
        ▼            ▼          ▼          ▼             ▼
   ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────────┐ ┌────────────┐
   │ Parcel  │ │ Zoning   │ │ Environ-│ │ Comps/  │ │ Utility /  │
   │ Geometry│ │ Rules DB │ │ mental  │ │ Valuation│ │ Access     │
   │ Store   │ │          │ │ Layers  │ │ Data    │ │ Layers     │
   └─────────┘ └──────────┘ └─────────┘ └─────────┘ └────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  Subdivision Feasibility       │
                  │  Calculation Engine            │
                  │  (pure logic, no I/O)          │
                  └──────────────┬─────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  Scoring & Risk Engine         │
                  └──────────────┬─────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  Report Generator              │
                  │  (structured data → PDF/HTML)  │
                  └──────────────┬─────────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  Report Storage + Delivery     │
                  └──────────────────────────────┘
```

### 2.2 Component responsibilities

| Component | Responsibility | Notes |
|---|---|---|
| API Gateway / BFF | Accept report requests, auth, rate limiting, orchestrate job lifecycle | Thin layer; no business logic |
| Geocoding / Address Resolution | Turn free-text address into lat/lon + normalized address | Use a third-party geocoder; do not build this in-house |
| Parcel Resolution Service | Turn lat/lon (or direct parcel ID) into a specific parcel record with authoritative boundary geometry | County-specific; this is the first piece of jurisdiction-specific code |
| Data Aggregation Layer | Fan out to all data sources for a given parcel, normalize into internal schema, cache results | This is where most "per-jurisdiction adapter" complexity lives |
| Parcel Geometry Store | Persisted parcel boundary + attributes (cached from county GIS) | PostGIS table |
| Zoning Rules DB | Structured, queryable zoning dimensional standards per zoning district per jurisdiction | This is hand-curated/encoded data, NOT scraped/inferred for v1 — see Section 5 |
| Environmental Layers | Flood zone, wetlands, steep slope, soils | Mostly federal/state GIS layers, less jurisdiction-specific |
| Comps/Valuation Data | Recent sales of comparable vacant lots and comparable subdivided lots | Used for the financial feasibility piece |
| Utility/Access Layers | Water/sewer service area, road frontage, easements | Mix of county GIS and parcel attribute data |
| Subdivision Feasibility Calculation Engine | Pure deterministic logic: given normalized inputs, compute possible lot configurations | No network calls, fully unit-testable |
| Scoring & Risk Engine | Converts feasibility output + constraint flags into a 0–100 score and a risk list | Deterministic, rule-based for v1 (explicitly NOT an ML model for v1 — see Section 9) |
| Report Generator | Renders the structured report object into a polished output document | Template-based |
| Report Storage + Delivery | Persists generated reports, handles delivery (download link, email) | |

### 2.3 Why this shape

- **Separation of data aggregation from calculation logic** is the most important architectural decision in this spec. The calculation engine (Section 6) must be a pure function: `feasibility_result = calculate(parcel_input)` with zero I/O, zero API calls, zero database access inside it. This is what makes it testable against hand-built fixtures and what makes the system portable to new jurisdictions — you only ever have to rewrite the *adapters* that produce `parcel_input`, never the math.
- **Per-jurisdiction adapters, not a universal scraper.** Do not attempt to build a system that automatically parses arbitrary municipal zoning PDFs into rules in v1. That is an extremely hard NLP problem that several funded competitors are actively working on and still get wrong often enough to need human review. For v1 and the pilot jurisdiction, zoning dimensional standards should be **hand-encoded** into the Zoning Rules DB as structured data (see Section 5.2). This is the single most important scope-control decision in this document.
- **Async job model**, not synchronous request/response, because aggregating from 5+ external data sources for a single parcel will take anywhere from 3–30 seconds depending on source latency and caching. The client polls or receives a webhook/email when the report is ready.

---

## 3. Core Data Model

These are the central entities. Implement as ORM models (SQLAlchemy recommended, see Section 10) backed by PostgreSQL + PostGIS.

### 3.1 `Jurisdiction`

Represents a single governing zoning authority (typically a county or a city — note that within a county, incorporated cities usually have their *own* zoning code distinct from the county's, so "jurisdiction" must resolve to the correct one based on parcel location, not just county).

```
Jurisdiction
- id: UUID (PK)
- name: string                      # e.g. "Travis County, TX (unincorporated)"
- state: string (2-letter)
- jurisdiction_type: enum           # COUNTY_UNINCORPORATED | CITY | TOWNSHIP
- fips_code: string
- subdivision_authority_url: string # link to subdivision ordinance, for human reference
- zoning_ordinance_url: string
- minor_subdivision_threshold: int  # e.g. "4" -- max lots that qualify as a "minor" (administrative) subdivision before requiring full platting/planning-commission review
- minor_subdivision_process_notes: text
- created_at, updated_at
```

### 3.2 `ZoningDistrict`

The structured, hand-encoded rule set for one zoning district within one jurisdiction. **This table is the core hand-curated dataset for the pilot jurisdiction** — see Section 5.2 for the encoding methodology.

```
ZoningDistrict
- id: UUID (PK)
- jurisdiction_id: FK -> Jurisdiction
- code: string                      # e.g. "R-1", "SF-3", "RR"
- name: string                      # e.g. "Single Family Residential"
- min_lot_area_sqft: int            # minimum legal lot size
- min_lot_width_ft: int             # minimum frontage/width
- min_lot_depth_ft: int (nullable)
- max_density_units_per_acre: float (nullable)  # for districts that regulate by density rather than min lot size
- setback_front_ft: int
- setback_side_ft: int
- setback_side_corner_ft: int (nullable)
- setback_rear_ft: int
- max_height_ft: int (nullable)     # not critical for subdivision but useful context
- max_lot_coverage_pct: float (nullable)
- max_far: float (nullable)
- requires_public_road_frontage: bool
- min_road_frontage_ft: int (nullable)   # may differ from min_lot_width_ft (flag lots, cul-de-sacs)
- allows_flag_lots: bool
- flag_lot_min_access_strip_ft: int (nullable)
- source_ordinance_section: string  # e.g. "Sec. 25-2-481" — citation for human audit
- last_verified_date: date          # when a human last confirmed this against the actual ordinance
- last_verified_by: string
- notes: text
- created_at, updated_at
```

### 3.3 `Parcel`

A single real-world property/tax parcel, cached from county GIS + assessor data.

```
Parcel
- id: UUID (PK)
- jurisdiction_id: FK -> Jurisdiction
- apn: string                       # Assessor's Parcel Number — the canonical county identifier
- address_normalized: string
- geometry: Geometry(POLYGON, 4326) # PostGIS geometry, parcel boundary
- centroid: Geometry(POINT, 4326)
- area_sqft: float                  # computed from geometry, authoritative source of truth for area
- area_acres: float
- zoning_district_id: FK -> ZoningDistrict (nullable until resolved)
- zoning_code_raw: string           # raw string as reported by county GIS, before mapping to ZoningDistrict
- existing_structures_count: int    # from assessor data; relevant because existing structures constrain where new lot lines can go
- assessed_land_value: numeric (nullable)
- assessed_improvement_value: numeric (nullable)
- last_sale_price: numeric (nullable)
- last_sale_date: date (nullable)
- owner_name: string (nullable)     # for context, not for outreach — see compliance note in Section 11
- raw_assessor_data: JSONB          # full raw payload retained for audit/debug
- data_fetched_at: timestamp
- created_at, updated_at
```

### 3.4 `EnvironmentalConstraint`

One row per constraint layer intersection for a parcel. Modeled as a separate table (not flattened fields on Parcel) because a parcel can have zero or many overlapping constraints, and new layers will be added over time.

```
EnvironmentalConstraint
- id: UUID (PK)
- parcel_id: FK -> Parcel
- constraint_type: enum   # FLOOD_ZONE | WETLAND | STEEP_SLOPE | SOIL_LIMITATION | EASEMENT | HISTORIC_OVERLAY | OTHER_OVERLAY
- severity: enum          # BLOCKING | SIGNIFICANT | MINOR | INFORMATIONAL
- coverage_pct: float     # % of parcel area affected by this constraint
- detail: JSONB           # type-specific detail, e.g. {"fema_zone": "AE", "bfe_ft": 612.3}
- source: string          # e.g. "FEMA NFHL", "USFWS NWI", "USGS"
- source_fetched_at: timestamp
```

### 3.5 `SubdivisionScenario`

A single candidate way of splitting a parcel — the calculation engine produces 0 to N of these per parcel. This is the central output of the calculation engine described in Section 6.

```
SubdivisionScenario
- id: UUID (PK)
- parcel_id: FK -> Parcel
- scenario_rank: int                # 1 = primary/recommended scenario, 2 = alternative, etc.
- num_resulting_lots: int
- lot_layout_type: enum             # SIMPLE_HALVE | FRONTAGE_STRIP | FLAG_LOT | UNEVEN_SPLIT
- resulting_lots: JSONB             # array of {approx_area_sqft, approx_width_ft, approx_depth_ft, has_frontage, geometry (GeoJSON)}
- meets_min_lot_size: bool
- meets_min_frontage: bool
- requires_variance: bool
- requires_rezone: bool
- requires_flag_lot_provision: bool
- subdivision_review_tier: enum     # ADMINISTRATIVE_MINOR | PLANNING_COMMISSION_MAJOR
- engine_version: string            # version of calc engine that produced this, for reproducibility
- created_at
```

### 3.6 `FeasibilityReport`

The top-level object representing one completed report run — what gets rendered and delivered.

```
FeasibilityReport
- id: UUID (PK)
- parcel_id: FK -> Parcel
- requested_by: string/FK           # user or API key identifier
- status: enum                      # PENDING | DATA_GATHERING | CALCULATING | COMPLETE | FAILED
- overall_score: int (0-100, nullable until COMPLETE)
- recommendation: enum              # nullable until COMPLETE; PURSUE | PURSUE_WITH_CAUTION | UNLIKELY | NOT_FEASIBLE
- primary_scenario_id: FK -> SubdivisionScenario (nullable)
- risk_flags: JSONB                  # array of {category, severity, message}
- valuation_summary: JSONB           # see Section 7.3
- generated_pdf_url: string (nullable)
- generated_html_url: string (nullable)
- error_detail: text (nullable)
- requested_at: timestamp
- completed_at: timestamp (nullable)
```

### 3.7 Entity relationship summary

```
Jurisdiction 1───* ZoningDistrict
Jurisdiction 1───* Parcel
ZoningDistrict 1───* Parcel
Parcel 1───* EnvironmentalConstraint
Parcel 1───* SubdivisionScenario
Parcel 1───* FeasibilityReport
SubdivisionScenario 1───1 FeasibilityReport (as primary_scenario)
```

---

## 4. Pilot Jurisdiction Selection

Before writing any code, pick **one specific county or city** to build against. This is a real decision the engineer needs to make, not a placeholder — but the criteria for choosing well are specified here so Claude Code can evaluate candidates if asked to help decide.

### 4.1 Selection criteria, in priority order

1. **Has a public, parcel-level GIS feed with an open API or downloadable shapefile/GeoJSON** (not just a clunky web map with no data export). Most US counties run Esri ArcGIS Online or ArcGIS Server for their GIS; many expose a queryable REST endpoint (`.../MapServer/0/query`) even if not advertised. Check for this first — it's a hard requirement.
2. **Zoning ordinance is a manageable size and complexity.** Prefer a jurisdiction with a small number of residential zoning districts (5–15) over one with a sprawling code with dozens of overlay districts. This directly determines how much manual encoding work Section 5.2 requires.
3. **Active minor-subdivision / lot-split activity.** Growing exurban and suburban counties (especially in TX, FL, NC, GA, AZ, ID, UT, TN) tend to have more real lot-split activity than slow-growth rural counties or built-out urban cores. More activity = more comps for the valuation piece and a more obviously real market.
4. **"Minor subdivision" or "administrative lot split" is a defined, distinct process from full platting.** Many jurisdictions have a fast-track process (e.g., splitting into ≤3 or ≤4 lots without going through full planning commission review) — this is the exact product wedge, so a jurisdiction that has this distinction codified is ideal.
5. **FEMA flood data, soils data (USDA SSURGO), and wetlands data (USFWS NWI) all have coverage** — true almost everywhere in the continental US, low risk, but verify for the chosen county.

### 4.2 Recommended approach

Have a human (not Claude Code) shortlist 3–5 candidate counties against criteria #1 and #2 by manually poking at each county's GIS portal and zoning code before committing. This is worth a day of manual research up front — picking a jurisdiction with messy or inaccessible GIS data will cost far more than a day later. Once chosen, hardcode that jurisdiction as the only supported one in v1; do not build a jurisdiction-selector UI for a system that only supports one.

---

## 5. Data Sources & Ingestion

### 5.1 Parcel geometry & assessor data

**Source:** County GIS REST API (most commonly Esri ArcGIS REST). Query pattern:

```
GET {county_gis_base_url}/MapServer/{layer_id}/query
  ?where=APN='{apn}'
  &outFields=*
  &f=geojson
```

If the county does not expose a clean REST API, fall back to:
- Downloadable shapefile/GeoJSON bulk export (re-downloaded and re-imported into PostGIS on a schedule, e.g. weekly) — most counties publish a full parcel layer export even if they don't have a live query API.
- Regrid (formerly LoveLand Technologies) as a paid third-party aggregator that normalizes parcel data across ~3,100 US counties into one consistent schema/API. **Recommended as the pragmatic default for v1** even though it has a per-parcel cost, because it eliminates the need to write a bespoke adapter for the county's idiosyncratic GIS setup. Evaluate Regrid's API and pricing before deciding whether to build a direct-to-county adapter instead.

**Normalize into the `Parcel` table fields specified in Section 3.3.** Critically: always compute `area_sqft` from the actual geometry (via PostGIS `ST_Area` on a geometry transformed to an appropriate projected CRS — do NOT use a geographic/lat-lon CRS for area calculations, results will be wrong) rather than trusting a county-reported area field, which is sometimes stale or rounded. Use the county-reported value only as a sanity-check cross-reference, and flag a data-quality warning if it differs from the computed value by more than ~5%.

### 5.2 Zoning rules — hand-encoded, not scraped

This is the most important data-engineering decision in this spec, so it gets its own subsection.

**Do not attempt to automatically parse the zoning ordinance text into structured rules for v1.** Municipal zoning codes are inconsistent, full of cross-references, exceptions, and footnotes, and getting this wrong produces a feasibility report that's confidently incorrect — the worst possible failure mode for a product whose entire value proposition is "trustworthy automated screening." Several funded competitors (see prior market research) are actively working on NLP-based zoning code parsing and still need human review loops.

**Instead, for the pilot jurisdiction:**
1. A human reads the zoning ordinance directly (county/city zoning code, usually published on Municode, American Legal Publishing, or the jurisdiction's own site).
2. For each residential zoning district relevant to single-family/rural-residential subdivision, manually populate one row in the `ZoningDistrict` table (Section 3.2) with the dimensional standards.
3. Every row must record `source_ordinance_section` (the specific code citation) and `last_verified_date`/`last_verified_by`, so any future automated re-verification or human audit has a paper trail.
4. Build a lightweight internal admin view (even a simple read/write table editor — does not need to be polished) so this data can be corrected as errors are found. Treat this table as a living dataset that needs periodic re-verification, not a one-time import.

This means: **the system's accuracy is bounded by the quality of this manual encoding**, not by any ML/NLP component. This is a deliberate and correct trade-off for v1. Scaling to more jurisdictions later means scaling this manual encoding process (or building tooling to assist a human doing it faster — e.g. an LLM-assisted first-pass extraction that a human then verifies line-by-line against the source ordinance — but always with mandatory human verification before a `ZoningDistrict` row is marked usable in production).

**Add a `verified: bool` field-level concept** — actually implement this as a per-district `last_verified_date` plus a hard rule in application code: a `ZoningDistrict` row with no `last_verified_date` set, or with one older than some staleness threshold (e.g., 18 months), should not be used to generate a report; the report generation should fail loudly rather than silently use stale/unverified zoning data.

### 5.3 Zoning district assignment per parcel

The county GIS parcel layer or a separate zoning layer usually includes a zoning code field per parcel (e.g. `ZONE_CLASS = "SF-3"`). Map this raw string (`zoning_code_raw` on `Parcel`) to the corresponding `ZoningDistrict.code` row. Build this as an explicit mapping table/dictionary per jurisdiction (raw GIS string → ZoningDistrict code), not a fuzzy string match — zoning codes are short and look similar (`R1` vs `R-1` vs `RS-1`) and a wrong match here invalidates the entire downstream calculation.

If a parcel's raw zoning string has no mapping entry, the system must surface this as an explicit data gap (`zoning_district_id = NULL`) and refuse to generate dimensional-standard-dependent parts of the report rather than guessing.

### 5.4 Environmental & physical constraint layers

| Layer | Source | Format/Access | Notes |
|---|---|---|---|
| FEMA Flood Zones | FEMA National Flood Hazard Layer (NFHL) | ArcGIS REST feature service, nationwide, free | Query by intersecting parcel geometry; extract `FLD_ZONE` and `STATIC_BFE` |
| Wetlands | US Fish & Wildlife Service National Wetlands Inventory (NWI) | Downloadable geodatabase/shapefile per state, also has a web service | Lower resolution than parcel-level; use for screening-level flags, not precise boundary determination |
| Soils (septic suitability) | USDA NRCS SSURGO / Web Soil Survey | Bulk data download or SDA (Soil Data Access) web service | Only critical if the parcel is NOT on public sewer — check utility layer first (5.5) before even querying this |
| Slope/topography | USGS 3DEP elevation data (1m or 1/3 arc-second DEM) | Downloadable raster, or compute slope server-side from DEM tiles | Compute average and max slope across parcel; steep slope (commonly >15-25% depending on jurisdiction) often triggers additional engineering review or reduces buildable area |
| Easements/right-of-way | County GIS (often a separate "easements" layer) or plat records | Varies heavily by county; may not be in machine-readable form for older easements | Treat as best-effort; flag explicitly when data is unavailable rather than assuming no easements exist |

For each layer, the Data Aggregation Layer performs a spatial intersection (PostGIS `ST_Intersects` against locally cached/cloned layer data, or a live API query against the source if caching isn't practical for that layer) between the parcel geometry and the constraint layer, and writes one `EnvironmentalConstraint` row per intersecting feature.

**Caching strategy:** FEMA, NWI, and soils data change infrequently (months to years). Pull and cache these into local PostGIS tables on a scheduled refresh (e.g., monthly), rather than hitting external APIs on every report request. This dramatically improves report generation latency and reliability. Parcel/assessor data should also be cached but refreshed more frequently (e.g., weekly) since ownership and assessed values change more often.

### 5.5 Utility & access data

- **Water/sewer service area boundaries:** Usually published by the relevant municipal utility district or county as a GIS layer. If a parcel is outside the public sewer service area, each new lot from a split will likely need its own septic system, which depends on soil suitability (5.4) and typically requires more land area per lot than jurisdictions assume in their *zoning* minimum lot size — this is a common source of "technically zoning-compliant but not actually buildable" failures. Treat this as a distinct flag, not folded silently into the zoning calculation.
- **Road frontage / access:** Derive from parcel geometry adjacency to a road centerline layer (county GIS usually has one). A parcel needs legal frontage on a public right-of-way (or an established access easement) for each resulting lot, unless the jurisdiction's zoning explicitly allows flag lots (see `ZoningDistrict.allows_flag_lots`).

### 5.6 Comparables & valuation data

For the financial feasibility component (Section 7.3):
- **Recent vacant land sales** in the same zoning district and general area: assessor sales records (often available in the same county GIS/assessor feed as a sales history field) filtered to vacant/unimproved parcels, plus optionally a licensed real estate data API (e.g. ATTOM, Estated, or a regional MLS data feed if accessible) for broader coverage and recency.
- **Recent sales of parcels that were themselves products of a recent subdivision** in the area, if identifiable (e.g. by matching recently-created APNs with small sequential suffixes, which often indicates a recent split) — useful as a direct analog for "what do split lots actually sell for here."

This data source is lower-priority for the first working version of the engine — the zoning/physical feasibility determination (Sections 6–7.1) is the core deliverable and can be built and validated before the valuation layer is wired in. Sequence accordingly (see Section 12).

---

## 6. Subdivision Feasibility Calculation Engine

This is the heart of the system. It must be implemented as a **pure function with no I/O** — given a fully-populated input object, it returns a deterministic output. All randomness, external calls, and database access happen in the layers around it, never inside it. This makes it directly unit-testable against hand-constructed fixtures (real or synthetic parcels with known correct answers) without needing a database or network connection in the test suite.

### 6.1 Function signature (conceptual)

```python
def calculate_subdivision_scenarios(
    parcel_geometry: ParcelGeometryInput,   # boundary polygon, area, frontage info
    zoning_rules: ZoningRulesInput,          # the resolved ZoningDistrict for this parcel
    constraints: list[ConstraintInput],      # environmental/physical constraints
    existing_structures: list[StructureInput],  # buildings that constrain new lot lines
) -> SubdivisionFeasibilityResult:
    ...
```

### 6.2 Step-by-step algorithm

**Step 1 — Eligibility gate (fast fail).**
Before attempting any geometric split, check the disqualifying conditions that make further calculation pointless:
- Is `zoning_district_id` resolved? If not, abort with a data-gap result (do not guess).
- Is `parcel.area_sqft < (2 × zoning_rules.min_lot_area_sqft)`? If the parcel isn't at least twice the minimum lot size, a 2-lot split is geometrically impossible without a variance. This doesn't mean "stop" — it means the only possible scenarios are variance-dependent, which should be flagged as such, not silently dropped.
- Does the parcel have existing structure(s) whose footprint, combined with required setbacks, would consume more than the parcel's buildable area in any 2-way split? If so, flag `requires_structure_removal_or_relocation` — a very common real-world blocker (the existing house sits in the middle of the lot) that should surface prominently, not get buried.

**Step 2 — Determine maximum theoretical lot count.**
```
max_lots_by_area = floor(parcel.area_sqft / zoning_rules.min_lot_area_sqft)
max_lots_by_density = floor(parcel.area_acres * zoning_rules.max_density_units_per_acre)  # if density-based district
max_theoretical_lots = min of whichever constraints apply, given the district type
```
This is an upper bound, not the answer — frontage and geometry constraints in Step 3 will usually reduce it further.

**Step 3 — Generate candidate split geometries.**
For v1, implement a constrained, deterministic geometric search rather than a general-purpose arbitrary-polygon-partitioning algorithm (true general subdivision-layout optimization is a much harder problem — see the `Parcel-Divider` academic research tool referenced in market research, which exists precisely because this is nontrivial). Implement these specific, common real-world patterns as discrete strategies, evaluate each, and return whichever valid ones exist:

- **`SIMPLE_HALVE`**: For roughly rectangular parcels with frontage on one side, attempt a straight-line split parallel to the side lot lines, perpendicular to the frontage, creating two lots that each retain road frontage. Iterate the split-line position to find a position (if any) where both resulting lots meet `min_lot_area_sqft`, `min_lot_width_ft`, and (if applicable) `min_road_frontage_ft`.
- **`FRONTAGE_STRIP`**: For parcels with frontage significantly wider than `2 × min_lot_width_ft`, split into N strips perpendicular to the frontage (this is the most common real-world residential lot split pattern — a wide shallow lot becomes 2+ narrower lots side by side, each with its own frontage).
- **`FLAG_LOT`**: Only evaluate if `zoning_rules.allows_flag_lots == true`. For parcels with limited frontage relative to depth, create a front lot (with frontage) and a rear "flag" lot connected to the road by a narrow access strip meeting `flag_lot_min_access_strip_ft`. This pattern unlocks splits that would otherwise fail the frontage requirement for the rear portion.
- **`UNEVEN_SPLIT`**: Same mechanics as `SIMPLE_HALVE`/`FRONTAGE_STRIP` but explicitly searching for the highest-value uneven split (e.g., a smaller lot carved off near the road, leaving a larger remainder) rather than assuming an even split is optimal — relevant once the valuation layer (7.3) is wired in, since equal-area splits are not always equal-value splits.

For each strategy, the implementation should:
1. Check basic compatibility (e.g., don't attempt `FLAG_LOT` if the zoning district disallows it; don't attempt `FRONTAGE_STRIP` if frontage is too narrow to begin with).
2. If compatible, run a 1-D parametric search (e.g., sweep the split-line position from one boundary to the other, or sweep the number of strips from 2 up to `max_theoretical_lots`) checking the resulting lot dimensions against `zoning_rules` at each step.
3. Subtract setback envelopes and existing structure footprints (+ their required setbacks) from each candidate lot to confirm there's a valid buildable envelope remaining (not just that the *lot* meets minimum area, but that a house can actually be sited on it).
4. Check environmental constraints (Step 4 below) against each candidate lot's geometry, not just the parent parcel — a constraint might affect only part of the original parcel and thus only one of the resulting lots.

This should be implemented using a proper geometry library — **Shapely** (Python) is the recommended choice, operating on geometries in a projected (not geographic) CRS for accurate distance/area math. Do not hand-roll polygon math.

**Step 4 — Apply environmental/physical constraint penalties per candidate.**
For each candidate `SubdivisionScenario`, intersect each resulting lot's geometry against the parcel's `EnvironmentalConstraint` records:
- If a `BLOCKING` severity constraint (e.g., a wetland or floodway covering the entire buildable envelope of a resulting lot) intersects a candidate lot, that scenario is invalid — discard it.
- If a `SIGNIFICANT` severity constraint covers a large % of a resulting lot's buildable area, retain the scenario but attach a prominent risk flag and reduce its score (Section 7).
- `MINOR`/`INFORMATIONAL` constraints are surfaced in the report but don't invalidate or heavily penalize a scenario.

**Step 5 — Classify review tier.**
For each surviving scenario, set `subdivision_review_tier` based on `jurisdiction.minor_subdivision_threshold`: if `num_resulting_lots <= minor_subdivision_threshold` (and no variance/rezone is required), classify as `ADMINISTRATIVE_MINOR`; otherwise `PLANNING_COMMISSION_MAJOR`. This matters enormously to a real user's go/no-go decision (weeks vs. months of process, no public hearing vs. a public hearing where neighbors can object) and should be a prominent, plainly-stated field in the report, not buried.

**Step 6 — Rank and return.**
Rank surviving scenarios (highest-value first once 7.3 is wired in; before that, simplest/most-likely-to-succeed first as a placeholder heuristic — e.g., fewer required variances ranks higher) and return as an ordered list. The top-ranked scenario becomes `FeasibilityReport.primary_scenario_id`.

### 6.3 Required unit test fixtures

Before considering this engine "done," build and pass against at least these synthetic fixture cases (construct as literal polygon coordinates in test code, not requiring real data):
1. A clean rectangular parcel, 2× minimum lot size, ample frontage, no constraints, no flag lot needed → should produce a valid `SIMPLE_HALVE` scenario.
2. The same parcel but only 1.8× minimum lot size → should produce zero valid scenarios without a variance, and the result should clearly say why (area shortfall, with the actual numbers).
3. A deep narrow parcel with frontage on one short end only, 3× minimum lot size, in a district where `allows_flag_lots = true` → should produce a valid `FLAG_LOT` scenario for the rear portion.
4. The same deep narrow parcel but `allows_flag_lots = false` → should correctly produce zero valid scenarios (or a `requires_rezone`/variance flag) rather than incorrectly forcing a flag lot.
5. A parcel that's geometrically splittable but has an existing house positioned such that no valid split avoids violating setbacks against it → should flag `requires_structure_removal_or_relocation` rather than silently returning an invalid scenario or silently excluding it with no explanation.
6. A parcel where a FEMA floodway (BLOCKING severity) covers exactly the back third → should produce a valid front-lot scenario but correctly invalidate any scenario that would put a resulting lot's buildable envelope inside the floodway.
7. A parcel straddling two different zoning districts (edge case, but real and common near zoning boundary lines) → system should explicitly flag this as a special case requiring manual review rather than silently picking one district's rules.

---

## 7. Scoring & Risk Model

### 7.1 Design principle

The scoring model for v1 is **deterministic and rule-based, not a trained ML model.** This is a deliberate choice: there is no labeled training data (no large dataset of "parcel X was a good/bad lot-split candidate, here's the ground truth outcome") to train against, and a rule-based system is auditable — every score can be explained by pointing at the specific rule that produced it, which matters enormously for a product whose trust is its entire value proposition. Revisit this decision only after the system has been in real use long enough to accumulate actual outcome data (e.g., "did the user's actual subdivision application get approved").

### 7.2 Score composition

`FeasibilityReport.overall_score` (0–100) is computed as a weighted combination of sub-scores. Suggested starting weights (tune later based on real usage, but ship with explicit, documented weights rather than unweighted/arbitrary combination):

| Sub-score | Weight | Computation basis |
|---|---|---|
| Zoning compliance | 35% | 100 if the primary scenario meets all dimensional standards as-of-right; reduced for each variance/rezone required |
| Physical buildability | 25% | Based on severity/coverage of environmental constraints on the primary scenario's resulting lots |
| Access/utility feasibility | 15% | Penalize for missing public frontage requiring flag-lot workaround, or off-sewer parcels with poor soil suitability |
| Process complexity | 10% | `ADMINISTRATIVE_MINOR` scores higher than `PLANNING_COMMISSION_MAJOR`; presence of likely-controversial neighbors (e.g. parcel in a subdivision with an active HOA — if detectable) reduces this |
| Financial upside | 15% | Once Section 5.6/7.3 data is available: estimated post-split lot value sum vs. current whole-parcel value, normalized into a 0-100 sub-score |

Each sub-score and the overall weighted score must be stored and surfaced in the report with a plain-language explanation, not just the number — e.g., "Zoning compliance: 70/100 — meets minimum lot area but the rear lot would need a flag-lot provision, which this district does not explicitly allow as-of-right (Sec. 25-2-481)."

### 7.3 Financial feasibility sub-calculation

```
current_whole_parcel_value ≈ assessed_land_value (or comps-based estimate if more reliable)
estimated_post_split_value = sum of (estimated per-lot value for each resulting lot in primary scenario)
subdivision_premium_pct = (estimated_post_split_value - current_whole_parcel_value) / current_whole_parcel_value

estimated_cost_to_execute = survey_cost_estimate + application_fee_estimate + (engineering_cost_estimate if PLANNING_COMMISSION_MAJOR)
estimated_net_upside = estimated_post_split_value - current_whole_parcel_value - estimated_cost_to_execute
```

Per-lot value estimation should use the comps data from Section 5.6: find recent comparable vacant lot sales in the same zoning district within a reasonable radius, adjust by relative lot size (simple $/sqft or $/acre basis is sufficient for v1 — do not over-engineer this into a full automated valuation model). `survey_cost_estimate` and `application_fee_estimate` should start as jurisdiction-level configured constants (a human researches typical local survey costs and the jurisdiction's actual published subdivision application fee schedule) rather than computed values.

**Explicitly surface the uncertainty here.** This is the least precise part of the report and should be labeled as a rough estimate with a range, not a confident point figure — e.g. "$45,000–$70,000 estimated net upside" rather than "$57,500."

### 7.4 Risk flag taxonomy

Every risk that affects feasibility, regardless of whether it changes the score, should produce a `risk_flags` entry with a consistent shape: `{category, severity, message, source_citation (if applicable)}`. Standard categories to implement:

- `ZONING_AREA_SHORTFALL`
- `ZONING_FRONTAGE_SHORTFALL`
- `REQUIRES_VARIANCE`
- `REQUIRES_REZONE`
- `REQUIRES_FLAG_LOT_PROVISION_NOT_ALLOWED`
- `EXISTING_STRUCTURE_CONFLICT`
- `FLOOD_ZONE_EXPOSURE`
- `WETLAND_EXPOSURE`
- `STEEP_SLOPE`
- `SEPTIC_SUITABILITY_UNKNOWN_OR_POOR`
- `NO_PUBLIC_SEWER_ACCESS`
- `INSUFFICIENT_ROAD_ACCESS`
- `MULTI_DISTRICT_PARCEL` (the zoning-boundary edge case from fixture #7)
- `STALE_ZONING_DATA` (the `ZoningDistrict.last_verified_date` staleness case from Section 5.2)
- `DATA_GAP` (generic — used whenever an upstream data source failed or returned nothing, so the report is honest about what it couldn't check, rather than silently treating missing data as "no constraint found")

`severity` should always be one of `BLOCKING | SIGNIFICANT | MINOR | INFORMATIONAL`, consistent with the `EnvironmentalConstraint.severity` enum, reused here for consistency across the codebase.

---

## 8. Report Generation

### 8.1 Report structure

The generated report (rendered to both a web/HTML view and a downloadable PDF) should contain, in this order:

1. **Header**: parcel address, APN, jurisdiction, zoning district, report generation date, a prominent disclaimer (see Section 8.3).
2. **Headline verdict**: overall score, recommendation category (`PURSUE | PURSUE_WITH_CAUTION | UNLIKELY | NOT_FEASIBLE`), one-paragraph plain-language summary.
3. **Primary scenario visual**: a map showing the parcel boundary and the proposed lot split lines, with each resulting lot's approximate dimensions and area labeled. (See Section 8.2 — this is generated as an SVG/image from the geometry, not hand-drawn.)
4. **Scenario detail table**: for the primary scenario and any ranked alternatives, a table of resulting lots with area, frontage, whether each meets dimensional standards as-of-right.
5. **Risk & constraint summary**: every `risk_flags` entry, grouped by severity, in plain language with the source citation where applicable.
6. **Financial summary**: current value, estimated post-split value range, estimated costs, estimated net upside range — clearly labeled as estimates.
7. **Process summary**: which review tier applies (administrative minor vs. planning-commission major), a rough timeline estimate, and a link to the jurisdiction's actual subdivision ordinance/application page for the user's own follow-up.
8. **Data sources & methodology appendix**: list every data source used and its as-of date, plus the zoning ordinance citation(s) relied upon. This builds trust and gives a sophisticated user (or their attorney/surveyor) something to independently verify against.

### 8.2 Map/diagram rendering

Render the parcel boundary and candidate split lines as an SVG (server-side, from the PostGIS/Shapely geometry — e.g. using a library that converts Shapely geometries to SVG paths, or constructing the SVG directly from polygon coordinate arrays after projecting to a simple local coordinate system for the image). Overlay:
- Parcel boundary (solid line)
- Proposed split line(s) (dashed, distinct color)
- Resulting lot labels (lot number, approx. area, approx. frontage)
- North arrow and a scale bar (compute scale from the known real-world dimensions)
- Environmental constraint overlays if present (e.g. a hatched region for a flood zone), with a legend

Do not attempt to pull in live satellite/aerial imagery for v1 — that adds significant complexity (imagery licensing, tile-serving infrastructure) for a feature that a clean schematic diagram mostly substitutes for at this stage. A clean line-diagram is sufficient and arguably clearer for this specific use case (showing legal/dimensional boundaries, not visual context).

### 8.3 Required disclaimer language

Every report must prominently state, near the top, language to the effect of: *this report is a preliminary, automated screening tool based on public GIS and assessor data; it is not a survey, does not constitute legal or professional advice, and does not guarantee subdivision approval; consult a licensed surveyor, civil engineer, and/or land-use attorney before making investment decisions or filing any application.* The exact legal wording should be drafted/reviewed by a human (ideally with legal input) before any report is sold or shown to a real customer — this spec flags the requirement but the precise language is out of scope for Claude Code to finalize unilaterally.

### 8.4 Rendering pipeline

Suggested approach: generate the report as structured HTML (server-rendered template, e.g. Jinja2) first — this is the canonical representation. Convert HTML → PDF using a headless-browser-based renderer (e.g. Playwright/Chromium print-to-PDF, or WeasyPrint if the layout is simple enough to avoid needing a full browser engine) for the downloadable version. This avoids maintaining two parallel templating systems for HTML and PDF.

---

## 9. API Design

### 9.1 Core endpoints

```
POST   /v1/reports
  Body: { "address": "123 Main St, City, ST" }  OR  { "apn": "..." }
  Response: { "report_id": "...", "status": "PENDING" }

GET    /v1/reports/{report_id}
  Response: full FeasibilityReport object (status + results once COMPLETE)

GET    /v1/reports/{report_id}/pdf
  Response: redirect to / stream the generated PDF

GET    /v1/parcels/lookup?address=...
  Response: parcel match candidates (for disambiguation before committing to a report — useful when geocoding returns
  an address that doesn't cleanly map to exactly one parcel, e.g. unit-level addresses or new construction not yet in
  assessor records)

GET    /v1/jurisdictions
  Response: list of currently supported jurisdictions (will be a list of one for v1 — but build the endpoint now so
  the client doesn't need to change when jurisdiction #2 is added)
```

### 9.2 Job lifecycle

`POST /v1/reports` should return immediately after creating a `FeasibilityReport` row in `PENDING` status and enqueuing an async job — it must NOT block on the full data-aggregation + calculation pipeline (Section 5–7), which can take long enough to make a synchronous HTTP request a poor experience. Use a task queue (Celery with Redis/RabbitMQ as broker, or a simpler alternative like a Postgres-backed job queue if avoiding extra infra — see Section 10 for recommendation) to run the pipeline asynchronously, updating `FeasibilityReport.status` through `DATA_GATHERING → CALCULATING → COMPLETE` (or `FAILED` with `error_detail` populated).

The client polls `GET /v1/reports/{report_id}` or — preferable for v1 simplicity — the system sends an email/webhook when complete, since this is a "come back later for your report" product, not a live interactive tool.

### 9.3 Idempotency & caching

If a report is requested for the same `apn` within some recency window (e.g. 30 days) and underlying data hasn't materially changed, consider returning the cached prior report rather than re-running the full pipeline — this both saves cost (external API calls, comps data) and ensures consistent answers for the same input in a short window. Make this an explicit, configurable policy rather than an accidental side effect of caching at the data-layer level.

---

## 10. Recommended Technology Stack

| Layer | Recommendation | Rationale |
|---|---|---|
| Language | Python 3.11+ | Best ecosystem for geospatial work (Shapely, GeoPandas, PostGIS bindings) and rapid backend development |
| Web framework | FastAPI | Async-native, automatic OpenAPI docs (useful given the API-first design), strong typing via Pydantic which pairs well with the structured data model in Section 3 |
| Database | PostgreSQL + PostGIS extension | Industry standard for geospatial data; needed for `ST_Intersects`, `ST_Area`, and storing/querying parcel geometry directly |
| ORM | SQLAlchemy + GeoAlchemy2 | GeoAlchemy2 adds PostGIS-aware geometry column types to SQLAlchemy |
| Geometry/calculation engine | Shapely (+ pyproj for CRS transforms) | Standard, well-tested Python geometry library; do not hand-roll polygon math |
| Task queue | Celery + Redis | Mature, well-documented; Redis doubles as a cache layer for the external-API caching strategy in Section 5.4 |
| Report rendering | Jinja2 (HTML) + Playwright (HTML→PDF) | Single source-of-truth template; Playwright gives accurate, modern CSS support for PDF rendering vs. older PDF libraries |
| Geocoding | Third-party API (e.g. Census Bureau geocoder for a free option, or Google/Mapbox geocoding for higher reliability) | Don't build geocoding in-house |
| Parcel data aggregation | Direct county GIS REST API where available; Regrid as fallback/default (see Section 5.1) | |
| Frontend (if built in v1) | Simple server-rendered pages or a minimal React app | The product's value is the report, not a rich interactive app — don't over-invest in frontend complexity for v1 |
| Hosting | Any standard cloud provider (AWS/GCP/Render/Fly.io) | No unusual infra requirements; PostGIS is supported by all major managed Postgres offerings (e.g. AWS RDS for PostgreSQL with PostGIS enabled) |

### 10.1 Repository structure (suggested)

```
/app
  /models          # SQLAlchemy models (Section 3 entities)
  /adapters        # per-source data adapters (county GIS, FEMA, NWI, SSURGO, comps)
  /engine          # the pure calculation engine (Section 6) — NO imports from /adapters or /models inside here
  /scoring         # scoring & risk model (Section 7)
  /reports         # report generation/templating (Section 8)
  /api             # FastAPI routes (Section 9)
  /tasks           # Celery task definitions orchestrating adapters -> engine -> scoring -> reports
  /admin           # lightweight zoning-rules data-entry/editing views (Section 5.2)
/tests
  /fixtures        # synthetic parcel/zoning fixtures (Section 6.3)
  /engine          # unit tests against /engine, using only /fixtures — no DB, no network
  /integration     # tests that do hit a test DB / mocked adapters
/migrations        # Alembic migrations
```

The `/engine` directory's import isolation (no dependency on `/models` or `/adapters`) should be enforced, e.g. with a simple import-linter rule or CI check, because it's the property that keeps the core logic testable and portable.

---

## 11. Compliance & Data-Handling Notes

- **Assessor data including owner names is public record** in virtually all US jurisdictions, but build with the assumption that this product is a feasibility-screening tool for the person looking at the parcel, not a skip-tracing or marketing-list tool. Do not build features that compile owner contact information for outreach purposes — that's a different (and more legally sensitive) product. Section 3.3's `owner_name` field exists for report context ("this parcel is owned by...") only.
- **No automated decisions should be presented as authoritative.** Every report-level conclusion must be traceable to specific, cited rules (Section 7.4's `source_citation`) — this is both a trust feature and a liability-mitigation practice given Section 8.3's disclaimer requirements.
- **Respect rate limits and terms of service of every external data source** (county GIS servers in particular are often modest government infrastructure, not built for high-volume commercial querying) — implement backoff and caching aggressively, and consider reaching out to the jurisdiction's GIS department directly for bulk data access or higher rate limits if usage grows, rather than scraping aggressively.

---

## 12. Build Sequence (Recommended Phases)

This sequencing exists to make sure the hardest-to-validate, most central piece of the system (the calculation engine) is built and proven correct before time is spent on peripheral pieces.

**Phase 0 — Jurisdiction selection & zoning data encoding (no code).**
Pick the pilot jurisdiction (Section 4). Manually encode every relevant `ZoningDistrict` row by reading the actual ordinance (Section 5.2). This is a research/data task, not a coding task, and should be largely finished before Phase 2 begins — the engine can't be meaningfully tested without real rule data to test against.

**Phase 1 — Data models & core engine, fixture-driven.**
Build the SQLAlchemy models (Section 3). Build the calculation engine (Section 6) against hand-written test fixtures (Section 6.3) only — no real data adapters yet. Get all 7 required fixture cases passing. This phase should produce a fully unit-tested, deterministic engine with zero external dependencies.

**Phase 2 — Parcel data adapter for the pilot jurisdiction.**
Build the adapter(s) from Section 5.1 to pull real parcel geometry/assessor data for the chosen jurisdiction into the `Parcel` table. Validate by spot-checking 10-20 real known parcels against the county's own GIS web map to confirm geometry and attributes match.

**Phase 3 — Wire the engine to real parcels.**
Connect Phase 2's real parcel data + Phase 0's real zoning rules through the engine built in Phase 1. At this point the system should produce correct `SubdivisionScenario` results for real parcels in the pilot jurisdiction, without yet having environmental constraints, scoring, or report rendering. Manually validate against a handful of real-world cases where the human building this already has intuition about the right answer (e.g., a parcel they know was actually recently split, or one they know clearly couldn't be).

**Phase 4 — Environmental/physical constraint layers.**
Add the Section 5.4 adapters (FEMA, NWI, SSURGO, slope) and wire `EnvironmentalConstraint` generation + the engine's Step 4 constraint-checking into the pipeline.

**Phase 5 — Scoring & risk model.**
Implement Section 7 against the now-complete feasibility pipeline output.

**Phase 6 — Report generation.**
Implement Section 8 — HTML template, SVG diagram generation, PDF export.

**Phase 7 — API & async job orchestration.**
Implement Section 9 — FastAPI endpoints, Celery task wiring, status lifecycle.

**Phase 8 — Comps/valuation layer.**
Add Section 5.6/7.3 — intentionally last, because it's the least structurally certain part of the system and the rest of the product is fully functional (with financial sub-score simply omitted or flagged as "pending data") without it.

**Phase 9 — Pilot validation.**
Run the complete pipeline against a meaningful sample (50-100+) of real parcels in the pilot jurisdiction, including some with known real-world outcomes if any can be identified (parcels that did or didn't successfully subdivide recently, per county records), and manually audit a sample of reports for correctness before considering the system validated.

---

## 13. Open Technical Risks & Unknowns to Resolve Early

These are the things most likely to cause rework if not addressed early — surfacing them explicitly rather than discovering them mid-build.

1. **County GIS data quality/reliability is unknown until tested against the specific chosen jurisdiction.** Some counties have excellent open APIs; others have stale, inaccurate, or barely-accessible data. This is the single biggest risk to the whole project and should be derisked in Phase 0/2, not assumed.
2. **Zoning ordinance ambiguity and exceptions.** Real zoning codes have grandfathering clauses, conditional-use exceptions, and cross-references to other code sections (e.g. a subdivision ordinance separate from the zoning ordinance, with its own additional requirements like required road improvements or park dedication fees) that a simple dimensional-standards table won't capture. Section 5.2's manual encoding will necessarily be a simplification — be explicit in the report disclaimer (8.3) about this rather than pretending the model captures 100% of real legal nuance.
3. **Flag lot and odd-geometry parcels are common in practice and the hardest case for the geometric engine.** Section 6.2's three discrete strategies cover the most common real-world patterns but will not cover every real parcel shape. Decide explicitly (and document in the report when it happens) what the system does when a parcel's shape doesn't fit any implemented strategy — the correct behavior is to say "no automated scenario could be generated for this parcel's geometry; manual review recommended," never to force a low-quality guess.
4. **Septic suitability is a meaningfully complex sub-domain** (perc tests, soil types, lot size requirements that vary by effluent system type) that this spec treats fairly lightly (Section 5.4/5.5). If the pilot jurisdiction has significant off-sewer parcel inventory, this may need more dedicated design than this spec currently allocates — flag this for follow-up scoping once the pilot jurisdiction is chosen and its sewer-service-area footprint is understood.
5. **Comps data licensing.** Confirm what comps/sales data sources are actually legally usable for this purpose (some real estate data licenses restrict derivative commercial use) before building Section 5.6/7.3 — this is a research task to complete before Phase 8, not a v1-blocking concern.
