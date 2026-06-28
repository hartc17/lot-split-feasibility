# Architecture

## System Overview

```mermaid
flowchart TB
    subgraph External["External Data Sources"]
        GIS["Hays County GIS\nArcGIS FeatureServer"]
        CAD["Hays CAD\nAssessor Data"]
        ENV["FEMA / NWI / SSURGO\nEnvironmental Layers (Phase 4)"]
        ZON["Kyle TX Code Ch. 53\nZoning Ordinance (hand-encoded)"]
    end

    subgraph Adapters["app/adapters/  — DB-driven, jurisdiction-generic"]
        CFG["JurisdictionConfig.from_orm()\nReads GIS config from Jurisdiction DB row"]
        ARC["ArcGISParcelAdapter\narcgis.py — generic for any ArcGIS county"]
        NORM["normalizer.py\nGeoJSON → Parcel fields\ngeodetic area via pyproj.Geod"]
        ZM["zoning_mapper.py\nRaw GIS code → ZoningDistrict.id\nvia Jurisdiction.gis_zoning_code_map"]
        ING["ingestion.py\nOrchestrates fetch → normalize → upsert"]
        EA["Env Constraint Adapter\n(Phase 4)"]

        CFG --> ARC
        ARC --> NORM
        NORM --> ZM
        ZM --> ING
        NORM --> ING
    end

    subgraph DB["PostgreSQL + PostGIS"]
        J["jurisdictions\n(+ gis_feature_server_url\n  gis_field_map\n  gis_zoning_code_map)"]
        ZD["zoning_districts"]
        P["parcels"]
        EC["environmental_constraints"]
        SS["subdivision_scenarios"]
        FR["feasibility_reports"]

        J -->|1:many| ZD
        J -->|1:many| P
        ZD -->|1:many| P
        P -->|1:many| EC
        P -->|1:many| SS
        P -->|1:many| FR
        SS -->|referenced by| FR
    end

    subgraph Engine["app/engine/  — pure functions, zero I/O"]
        T["types.py\nParcelGeometryInput\nZoningRulesInput\nConstraintInput\nSubdivisionFeasibilityResult"]
        G["geometry.py\ninterior_normal()\nmeasure_frontage_width()\nhas_buildable_envelope()"]
        EL["eligibility.py\ncheck_eligibility()"]
        SH["strategies/simple_halve.py\nrun_frontage_strip()\nrun_simple_halve()"]
        FL["strategies/flag_lot.py\nrun_flag_lot()"]
        CN["constraints.py\n_lot_constraint_flags()\n_evaluate_scenario()\napply_constraints()"]
        CA["calculator.py\ncalculate_subdivision_scenarios()"]

        T --> G
        T --> EL
        T --> SH
        T --> FL
        T --> CN
        EL --> CA
        SH --> CA
        FL --> CA
        CN --> CA
        G --> EL
        G --> SH
        G --> FL
    end

    subgraph API["app/api/  (Phase 7)"]
        EP["/v1/reports POST\n/v1/reports/{id} GET"]
    end

    subgraph Scripts["scripts/"]
        SEED["seed_hays_county.py\nOne-time DB seed for Kyle TX"]
        VAL["validate_parcels.py\nCLI spot-check vs. live GIS"]
    end

    GIS --> ARC
    CAD --> ARC
    ENV --> EA
    ZON -->|human encodes| ZD
    J -->|config| CFG

    ING --> P
    EA --> EC

    P --> CA
    ZD --> CA
    EC --> CA

    CA --> SS
    CA --> FR

    EP --> CA
    SEED --> J
```

## Adapter Data Flow

```mermaid
flowchart LR
    subgraph Input
        JR["Jurisdiction DB row\n(gis_feature_server_url\ngis_field_map\ngis_zoning_code_map)"]
        APN["APN string"]
    end

    JR --> CFG["JurisdictionConfig.from_orm()"]
    CFG --> ADA["ArcGISParcelAdapter\nHTTP GET → GeoJSON"]
    APN --> ADA

    ADA -->|"None if not found"| NONE["return None"]
    ADA -->|"ParcelRecord"| NORM["normalizer.normalize()\nShapely + pyproj.Geod\narea_sqft, centroid, WKB"]

    NORM --> ZM["zoning_mapper\n.resolve_zoning_district_id()\nDB lookup via gis_zoning_code_map"]
    ZM -->|"UUID or None"| UPSERT

    NORM --> UPSERT["ingestion\nSELECT existing → UPDATE\nor INSERT new Parcel"]
    UPSERT --> DB["parcels table"]
```

## Engine Data Flow

```mermaid
flowchart LR
    IN["ParcelGeometryInput\nZoningRulesInput\nConstraintInput[]\nStructureInput[]"]

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

## Database Schema

```mermaid
erDiagram
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
        int flag_lot_min_access_strip_ft
        date last_verified_date
        string source_ordinance_section
    }

    parcels {
        uuid id PK
        uuid jurisdiction_id FK
        uuid zoning_district_id FK
        string apn
        geometry geometry
        geometry centroid
        float area_sqft
        float area_acres
        string zoning_code_raw
        jsonb raw_assessor_data
        timestamp data_fetched_at
    }

    environmental_constraints {
        uuid id PK
        uuid parcel_id FK
        enum constraint_type
        enum severity
        geometry geometry
        float coverage_pct
        jsonb detail
    }

    subdivision_scenarios {
        uuid id PK
        uuid parcel_id FK
        int num_resulting_lots
        enum lot_layout_type
        jsonb resulting_lots
        bool requires_variance
        bool requires_rezone
        bool requires_flag_lot_provision
        enum subdivision_review_tier
        string engine_version
    }

    feasibility_reports {
        uuid id PK
        uuid parcel_id FK
        uuid primary_scenario_id FK
        enum status
        int overall_score
        enum recommendation
        jsonb risk_flags
        timestamp requested_at
        timestamp completed_at
    }

    jurisdictions ||--o{ zoning_districts : "has"
    jurisdictions ||--o{ parcels : "contains"
    zoning_districts ||--o{ parcels : "governs"
    parcels ||--o{ environmental_constraints : "has"
    parcels ||--o{ subdivision_scenarios : "has"
    parcels ||--o{ feasibility_reports : "has"
    subdivision_scenarios ||--o| feasibility_reports : "primary scenario"
```

## Engine Isolation Contract

`app/engine/` is enforced (via AST scan in `tests/engine/test_engine_isolation.py`) to have zero imports from:

| Forbidden module | Why |
|---|---|
| `app.models` | No ORM types in engine inputs/outputs |
| `app.adapters` | Engine knows nothing about data fetching |
| `sqlalchemy` | No DB session leakage |
| `geoalchemy2` | Engine uses Shapely geometries only |
| `psycopg2` | No direct DB connections |

All engine inputs are plain Python dataclasses (`app/engine/types.py`). The calling layer (adapters → orchestration → API) is responsible for fetching data from the DB, projecting geometries to feet, and constructing the input structs before calling `calculate_subdivision_scenarios()`.

## Adding a New Jurisdiction

No new Python code is required. The steps are:

1. Create a seed script in `scripts/` that inserts one `Jurisdiction` row with:
   - `gis_feature_server_url` — the county's ArcGIS FeatureServer URL
   - `gis_field_map` — JSON mapping canonical roles to actual GIS field names
   - `gis_zoning_code_map` — JSON mapping raw GIS zoning strings to `ZoningDistrict.code` values
2. Manually encode `ZoningDistrict` rows for each relevant residential district (per spec §5.2), citing `source_ordinance_section` and setting `last_verified_date`.
3. Run the seed script against the target DB.

The `ArcGISParcelAdapter` and `ParcelIngestionService` require no changes.
