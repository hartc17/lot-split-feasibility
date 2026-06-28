# Architecture

## System Overview

```mermaid
flowchart TB
    subgraph Input["Input Layer — user provides geometry + rules"]
        UPLOAD["File Upload\n(GeoJSON / KML / Shapefile zip)"]
        DRAW["Draw on Map\n(OpenLayers — app/static/)"]
        APN["Address / APN Lookup\n(optional convenience path)"]
        FORM["Zoning Rules Form\n(min lot size, setbacks, etc.)"]
    end

    subgraph Parsers["app/parsers/"]
        PGJ["geojson.py"]
        PKML["kml.py"]
        PSHP["shapefile.py"]
        PROJ["projection.py\nWGS84 → local feet\n(auto-UTM zone detection)"]

        PGJ --> PROJ
        PKML --> PROJ
        PSHP --> PROJ
    end

    subgraph API["app/api/"]
        PARSE["/v1/parse/*\nReturns polygon + labeled edges\n(user picks road side)"]
        FEAS["/v1/feasibility POST\nRuns engine, returns result"]
        HEALTH["/health"]
    end

    subgraph EngineInputs["app/engine/inputs.py"]
        BPG["build_parcel_geometry_input()\nprojects polygon, extracts frontage edge"]
        BZR["build_zoning_rules_input()\nvalidates user-entered fields"]
    end

    subgraph Engine["app/engine/  — pure functions, zero I/O"]
        T["types.py\nParcelGeometryInput\nZoningRulesInput\nConstraintInput"]
        G["geometry.py"]
        EL["eligibility.py"]
        STRAT["strategies/\nsimple_halve, frontage_strip, flag_lot"]
        CN["constraints.py"]
        CA["calculator.py\ncalculate_subdivision_scenarios()"]

        T --> G
        T --> EL
        T --> STRAT
        T --> CN
        EL --> CA
        STRAT --> CA
        CN --> CA
        G --> EL
        G --> STRAT
    end

    subgraph OptionalAPN["Optional: APN lookup path (app/adapters/)"]
        ARC["ArcGISParcelAdapter\nGeneric — any ArcGIS county"]
        NORM["normalizer.py\nGeoJSON → area_sqft, centroid"]
        CFG["JurisdictionConfig.from_orm()\nBuilt from Jurisdiction DB row"]
        CFG --> ARC
        ARC --> NORM
    end

    subgraph DB["PostgreSQL + PostGIS (Phase 4+)"]
        REPORTS["reports\ngeometry_geojson, zoning_rules\nresult (JSONB), status"]
        JURISDICTIONS["jurisdictions (optional)\ngis_feature_server_url\ngis_field_map"]
        JURISDICTIONS --> CFG
    end

    UPLOAD --> Parsers
    DRAW --> FEAS
    APN --> OptionalAPN
    NORM --> PARSE

    Parsers --> PARSE
    PARSE --> FEAS
    FORM --> FEAS

    FEAS --> BPG
    FEAS --> BZR
    BPG --> CA
    BZR --> CA

    CA --> REPORTS
    CA --> FEAS
```

## Input → Parse → Select Edge → Run Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Parsers
    participant Engine

    User->>Frontend: Upload GeoJSON / KML / SHP
    Frontend->>API: POST /v1/parse/{format}
    API->>Parsers: parse → project to feet
    Parsers-->>API: polygon + edges [{index, length_ft}]
    API-->>Frontend: ParseResponse

    Frontend->>User: Show parcel on map, label each edge
    User->>Frontend: Click road-facing edge (frontage_edge_index)
    User->>Frontend: Fill in zoning rules form

    Frontend->>API: POST /v1/feasibility {geometry, frontage_edge_index, zoning}
    API->>Engine: build_parcel_geometry_input() + calculate_subdivision_scenarios()
    Engine-->>API: SubdivisionFeasibilityResult
    API-->>Frontend: FeasibilityResponse {scenarios, flags, max_lots}
```

## Engine Data Flow

```mermaid
flowchart LR
    IN["ParcelGeometryInput\n(boundary in feet, frontage_edge)\nZoningRulesInput\nConstraintInput[]\nStructureInput[]"]

    IN --> EL["check_eligibility()"]
    EL -->|"DATA_GAP or\nMULTI_DISTRICT"| EARLY1["return early\ndata_gap=True"]
    EL -->|"area shortfall or\nstructure conflict"| EARLY2["return early\nno scenarios"]
    EL -->|pass| STRAT

    subgraph STRAT["Strategy Layer"]
        FS["run_frontage_strip()\n2–6 equal-width strips"]
        FLG["run_flag_lot()\nif allows_flag_lots"]
    end

    STRAT --> AC["apply_constraints()\nBLOCKING ≥50% → eliminate\nSIGNIFICANT/MINOR → flag"]
    AC --> RANK["_rank_scenarios()\nvariance → rezone → flag lot\n→ risk flags → num lots"]
    RANK --> OUT["SubdivisionFeasibilityResult\nmax_theoretical_lots\nscenarios[]\ndisqualifying_flags[]"]
```

## Projection Pipeline

```mermaid
flowchart LR
    RAW["Uploaded geometry\nEPSG:4326 (WGS84)\nPolygon Z or 2D"]

    RAW -->|"parse_geojson / parse_kml\n/ parse_shapefile_zip"| POLY["Shapely Polygon\n(2D, WGS84)"]
    POLY -->|"get_utm_epsg(centroid)\nTransformer.from_crs()"| UTM["Polygon\n(UTM meters)"]
    UTM -->|"× 3.28084"| FEET["Polygon\n(US survey feet)\nready for engine"]
    FEET -->|"extract_edge(n)"| EDGE["LineString\nfrontage_edge\n(feet)"]
```

## Database Schema

```mermaid
erDiagram
    reports {
        uuid id PK
        jsonb geometry_geojson
        int frontage_edge_index
        jsonb zoning_rules
        jsonb result
        string status
        text error_message
        timestamp created_at
        timestamp completed_at
    }

    jurisdictions {
        uuid id PK
        string name
        string state
        enum jurisdiction_type
        string fips_code
        int minor_subdivision_threshold
        text gis_feature_server_url
        jsonb gis_field_map
        jsonb gis_zoning_code_map
    }

    zoning_districts {
        uuid id PK
        uuid jurisdiction_id FK
        string code
        int min_lot_area_sqft
        int min_lot_width_ft
        int setback_front_ft
        int setback_side_ft
        int setback_rear_ft
        bool allows_flag_lots
        date last_verified_date
    }

    parcels {
        uuid id PK
        uuid jurisdiction_id FK
        uuid zoning_district_id FK
        string apn
        geometry geometry
        float area_sqft
        string zoning_code_raw
        timestamp data_fetched_at
    }

    jurisdictions ||--o{ zoning_districts : "has"
    jurisdictions ||--o{ parcels : "contains"
    zoning_districts ||--o{ parcels : "governs"
```

> **Note:** The `reports` table is the primary table for the user-input flow and requires only PostgreSQL (no PostGIS). The `jurisdictions`, `zoning_districts`, and `parcels` tables support the optional APN-lookup path and are only needed if that feature is activated.

## Engine Isolation Contract

`app/engine/` is enforced (via AST scan in `tests/engine/test_engine_isolation.py`) to have zero imports from:

| Forbidden module | Why |
|---|---|
| `app.models` | No ORM types in engine inputs/outputs |
| `app.adapters` | Engine knows nothing about data fetching |
| `sqlalchemy` | No DB session leakage |
| `geoalchemy2` | Engine uses Shapely geometries only |
| `psycopg2` | No direct DB connections |

All engine inputs are plain Python dataclasses (`app/engine/types.py`). The calling layer (`app/engine/inputs.py` → `app/api/routes/feasibility.py`) is responsible for parsing uploaded geometry, projecting to feet, selecting the frontage edge, and constructing the input structs before calling `calculate_subdivision_scenarios()`.

## Two Input Paths

```mermaid
flowchart LR
    subgraph Primary["Primary path (any jurisdiction, no DB)"]
        UP["Upload / Draw"] --> PARSE["app/parsers/\n→ Shapely Polygon"] --> PROJ2["projection.py\n→ feet"] --> INP["inputs.py\n→ ParcelGeometryInput"]
        FORM2["Zoning form"] --> ZR["inputs.py\n→ ZoningRulesInput"]
    end

    subgraph Optional["Optional path (ArcGIS-served counties)"]
        APN2["APN / address"] --> ARC2["ArcGISParcelAdapter"] --> NORM2["normalizer.py"] --> INP
        DB2["Jurisdiction DB row"] --> ARC2
    end

    INP --> CALC["calculate_subdivision_scenarios()"]
    ZR --> CALC
    CALC --> RESULT["FeasibilityResponse"]
```
