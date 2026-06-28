# Pilot Jurisdiction: City of Kyle, TX

**Decision date:** 2026-06-28  
**Status:** Phase 0 complete — zoning data encoded below; Phase 2 (parcel adapter) ready to start

---

## Why Kyle (not unincorporated Hays County)

The user's intent was "Hays County, TX." However, **Texas counties have no general zoning authority** — unincorporated Hays County has no zoning code and no dimensional standards by district. The feasibility engine requires a `ZoningDistrict` table; there is nothing to populate it with for unincorporated county land.

**Kyle, TX** is the correct pilot target:
- It is within Hays County, so Hays County GIS parcel data covers it
- It has a complete zoning ordinance (Chapter 53) with residential districts and dimensional standards
- It is one of the fastest-growing cities in Texas — active lot-split activity
- It has a defined administrative minor plat process (Chapter 41)
- FEMA, NWI, SSURGO, and 3DEP all have full coverage

---

## Jurisdiction Record

| Field | Value |
|---|---|
| Name | City of Kyle, TX |
| State | TX |
| jurisdiction_type | CITY |
| FIPS code | 48209 (Hays County), city FIPS 40888 |
| Zoning ordinance | Chapter 53, City of Kyle Code of Ordinances |
| Zoning ordinance URL | https://ecode360.com/KY6871 → Chapter 53 |
| Subdivision ordinance | Chapter 41, City of Kyle Code of Ordinances |
| Subdivision ordinance URL | https://ecode360.com/KY6871 → Chapter 41 |
| minor_subdivision_threshold | **4 lots** (Texas LGC §212.0065; Ch. 41 adopts this standard — admin approval by planning director + city engineer + director of public works, no P&Z commission or council required) |
| Minor subdivision process notes | Administrative review only for ≤4 lots fronting existing street, no new street creation, no extension of municipal facilities required. Prepared plat + surveyor seal + application + fees submitted to administrator. |

---

## GIS & Parcel Data Sources

### Parcel geometry (authoritative)
**Hays County GIS Hub (ArcGIS Online)**  
URL: https://hays-county-haysgis.hub.arcgis.com/  
Format: ArcGIS Feature Service, GeoJSON, Shapefile download  
Coverage: All parcels county-wide (includes Kyle)  
**⚠ Human action needed for Phase 2:** Navigate the Hub to find the current parcel feature service REST URL and test a live query by APN before building the adapter. The county's primary ArcGIS server (maps.co.hays.tx.us) currently only exposes an address geocoder — the parcel feature layer is on the Hub.

**Fallback / interim option (confirmed live, sparse fields):**  
`https://gis.urbaneng.com/arcgis/rest/services/HaysCountyParcels/FeatureServer/0`  
Queryable: yes (tested 2026-06-28)  
Fields available: OBJECTID, PROP_ID, Class, geometry (polygon)  
Vintage: "Hays County 2020" — stale for recent parcels; use geometry only, cross-reference Hays CAD for attributes

### Assessor data (attributes)
**Hays Central Appraisal District (Hays CAD)**  
URL: https://hayscad.com/data-downloads/  
Format: Downloadable CSV/shapefile (account may be required)  
Fields: APN (PROP_ID), owner, address, land value, improvement value, last sale, acreage  
Update frequency: Annual  
**Alternative:** Regrid API (https://app.regrid.com/us/tx/hays) — normalised parcel + assessor data, per-query pricing, eliminates bespoke adapter work

### Zoning layer (for parcel → ZoningDistrict mapping)
**City of Kyle ArcGIS Hub**  
URL: https://city-of-kyle-maps-giskyle.hub.arcgis.com/  
The Hub has a zoning layer dataset; REST URL needs verification for Phase 2.  
Alternative: Use the zoning_code_raw → ZoningDistrict mapping table (hand-curated) instead of a live spatial join — simpler for v1.

---

## Residential ZoningDistrict Rows

Source: City of Kyle Code of Ordinances Chapter 53, verified against Zoneomics (https://www.zoneomics.com/code/kyle-TX/chapter_2), 2026-06-28.

**⚠ Human verification required before use in production:** Read each district section in the actual Chapter 53 ordinance at ecode360.com/KY6871 and record the `source_ordinance_section` citation before setting `last_verified_date`. The setback values below come from Zoneomics and are consistent with partial readings of the ordinance but have not been directly line-checked against the authoritative PDF.

### R-1-1 — Single-Family Residential 1 (low density)

| Field | Value |
|---|---|
| code | R-1-1 |
| name | Single-Family Residential 1 |
| min_lot_area_sqft | 8,190 |
| min_lot_width_ft | 80 |
| min_lot_depth_ft | NULL |
| max_density_units_per_acre | 3.9 |
| setback_front_ft | 35 |
| setback_side_ft | 10 |
| setback_side_corner_ft | 20 |
| setback_rear_ft | 20 |
| max_height_ft | 35 |
| requires_public_road_frontage | true |
| min_road_frontage_ft | 80 (cul-de-sac minimum: 35 ft) |
| allows_flag_lots | **TBD — verify in Ch. 53** |
| flag_lot_min_access_strip_ft | NULL (TBD) |
| source_ordinance_section | Ch. 53, Division 2 (to be confirmed) |
| last_verified_date | NULL — do not use in production until verified |

### R-1-2 — Single-Family Residential 2 (standard suburban)

| Field | Value |
|---|---|
| code | R-1-2 |
| name | Single-Family Residential 2 |
| min_lot_area_sqft | 6,825 |
| min_lot_width_ft | 65 |
| min_lot_depth_ft | NULL |
| max_density_units_per_acre | 4.7 |
| setback_front_ft | 25 |
| setback_side_ft | 8 (7.5 ft rounded to nearest integer — confirm exact value) |
| setback_side_corner_ft | 15 |
| setback_rear_ft | 15 |
| max_height_ft | 35 |
| requires_public_road_frontage | true |
| min_road_frontage_ft | 65 (cul-de-sac minimum: 35 ft) |
| allows_flag_lots | **TBD — verify in Ch. 53** |
| flag_lot_min_access_strip_ft | NULL (TBD) |
| source_ordinance_section | Ch. 53, Division 3 (ecode360.com/45580813) |
| last_verified_date | NULL — do not use in production until verified |

### R-1-3 — Single-Family Residential 3 (higher density SF)

| Field | Value |
|---|---|
| code | R-1-3 |
| name | Single-Family Residential 3 |
| min_lot_area_sqft | 5,540 |
| min_lot_width_ft | 50 |
| min_lot_depth_ft | NULL |
| max_density_units_per_acre | 5.5 |
| setback_front_ft | 20 |
| setback_side_ft | 5 |
| setback_side_corner_ft | 10 |
| setback_rear_ft | 10 |
| max_height_ft | 35 |
| requires_public_road_frontage | true |
| min_road_frontage_ft | 50 (cul-de-sac minimum: 35 ft) |
| allows_flag_lots | **TBD — verify in Ch. 53** |
| flag_lot_min_access_strip_ft | NULL (TBD) |
| source_ordinance_section | Ch. 53 (to be confirmed) |
| last_verified_date | NULL — do not use in production until verified |

### UE — Urban Estate

| Field | Value |
|---|---|
| code | UE |
| name | Urban Estate |
| min_lot_area_sqft | 22,500 |
| min_lot_width_ft | 100 |
| min_lot_depth_ft | NULL |
| max_density_units_per_acre | NULL |
| setback_front_ft | 25 |
| setback_side_ft | 25 |
| setback_side_corner_ft | NULL |
| setback_rear_ft | 25 |
| max_height_ft | 45 |
| requires_public_road_frontage | true |
| min_road_frontage_ft | 100 |
| allows_flag_lots | **TBD — verify in Ch. 53** |
| flag_lot_min_access_strip_ft | NULL (TBD) |
| source_ordinance_section | Ch. 53 (to be confirmed) |
| last_verified_date | NULL — do not use in production until verified |

### A — Agricultural

| Field | Value |
|---|---|
| code | A |
| name | Agricultural |
| min_lot_area_sqft | 43,560 (1 acre) |
| min_lot_width_ft | 150 |
| min_lot_depth_ft | NULL |
| max_density_units_per_acre | NULL |
| setback_front_ft | 40 |
| setback_side_ft | 25 |
| setback_side_corner_ft | NULL |
| setback_rear_ft | 25 |
| max_height_ft | 45 |
| requires_public_road_frontage | true |
| min_road_frontage_ft | 150 |
| allows_flag_lots | **TBD — verify in Ch. 53** |
| flag_lot_min_access_strip_ft | NULL (TBD) |
| source_ordinance_section | Ch. 53 (to be confirmed) |
| last_verified_date | NULL — do not use in production until verified |

---

## Typical Residential Zoning Code Distribution in Kyle

Based on the zoning map (https://www.zoneomics.com/zoning-maps/texas/kyle):
- **R-1-2** and **R-1-3** are the dominant SF districts in established areas
- **R-1-1** appears in older/larger-lot neighborhoods
- **UE** in semi-rural transitional areas at the city fringe
- **A** at the outermost edge / ETJ boundary

For Phase 2 validation, focus on R-1-2 and R-1-3 parcels — highest volume, most likely to have real lot-split candidates.

---

## Zoning Code → ZoningDistrict Mapping

This table maps the raw zoning code string (as it appears in the Kyle/Hays County GIS parcel layer) to the ZoningDistrict.code in our database. **Must be verified against actual GIS layer attribute values before Phase 2.**

| GIS raw value | ZoningDistrict.code |
|---|---|
| R-1-1 | R-1-1 |
| R-1-2 | R-1-2 |
| R-1-3 | R-1-3 |
| R1-1 | R-1-1 |
| R1-2 | R-1-2 |
| R1-3 | R-1-3 |
| UE | UE |
| A | A |
| AG | A |

---

## Open Items Before Phase 2

1. **Flag lot provisions:** Chapter 53 must be read to determine if any residential district explicitly allows or disallows flag lots. Set `allows_flag_lots` and `flag_lot_min_access_strip_ft` accordingly. This is the single most important field still missing.

2. **Source ordinance section citations:** Read each district in Chapter 53 (ecode360.com/KY6871) and record the exact section number (e.g., "Ch. 53, §53-18") for `source_ordinance_section`. Required before setting `last_verified_date`.

3. **Side setback for R-1-2:** Zoneomics says 7.5 ft; the integer field in our schema rounds this. Confirm whether the ordinance says "7 ft" or "7.5 ft" and store accordingly (may need schema update to Float).

4. **GIS parcel feature service URL:** Navigate https://hays-county-haysgis.hub.arcgis.com to find the live parcel REST endpoint and test a query by APN before building the Phase 2 adapter.

5. **Kyle GIS parcel vs. Regrid decision:** Decide whether to use the Hays County GIS Hub directly (free, requires bespoke adapter) or Regrid (paid, schema-normalised, much faster adapter dev). Recommend Regrid for v1 per the spec.

6. **Minor plat definition wording:** Confirm Kyle Ch. 41's exact definition matches Texas LGC §212.0065 (≤4 lots, fronting existing street, no new street). If Kyle has a stricter threshold (e.g., 3 lots), update `minor_subdivision_threshold` in the Jurisdiction record.
