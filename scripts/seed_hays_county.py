"""
Seed the Jurisdiction row for City of Kyle, TX (Hays County pilot).

Run once after `alembic upgrade head`:

    python scripts/seed_hays_county.py

Safe to re-run — skips insert if the jurisdiction already exists.
"""
import os
import sys

# Allow running from project root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.models import Jurisdiction

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL)

KYLE_TX = dict(
    name="City of Kyle, TX",
    state="TX",
    jurisdiction_type="CITY",
    fips_code="48209",
    minor_subdivision_threshold=4,
    minor_subdivision_process_notes=(
        "Administrative review for ≤4 lots fronting an existing street with no new "
        "street creation. Texas LGC §212.0065. Approved by planning director + city "
        "engineer + director of public works; no P&Z commission or council required."
    ),
    zoning_ordinance_url="https://ecode360.com/KY6871",
    subdivision_authority_url="https://ecode360.com/KY6871",
    # ----------------------------------------------------------------
    # GIS adapter config
    # ----------------------------------------------------------------
    # Interim URL — confirmed live 2026-06-28, Hays County 2020 vintage.
    # Navigate https://hays-county-haysgis.hub.arcgis.com to find the live
    # parcel FeatureServer URL and update this value once verified.
    gis_feature_server_url=(
        "https://gis.urbaneng.com/arcgis/rest/services/HaysCountyParcels/FeatureServer/0"
    ),
    # Field name mapping: canonical role → actual GIS attribute name.
    # Fields set to None are absent in this layer; update once the live Hub
    # endpoint is verified and its full field list is inspected.
    gis_field_map={
        "apn": "PROP_ID",
        "address": None,
        "zoning_code": None,
        "owner_name": None,
        "assessed_land": None,
        "assessed_improvement": None,
        "last_sale_price": None,
        "last_sale_date": None,
        "structures_count": None,
    },
    # Raw GIS zoning strings → ZoningDistrict.code for Kyle TX.
    # Verify these against the actual GIS layer zoning field values before Phase 3.
    gis_zoning_code_map={
        "R-1-1": "R-1-1",
        "R-1-2": "R-1-2",
        "R-1-3": "R-1-3",
        "R1-1":  "R-1-1",
        "R1-2":  "R-1-2",
        "R1-3":  "R-1-3",
        "UE":    "UE",
        "A":     "A",
        "AG":    "A",
    },
)

with Session(engine) as session:
    existing = session.execute(
        select(Jurisdiction).where(
            Jurisdiction.name == KYLE_TX["name"],
            Jurisdiction.state == KYLE_TX["state"],
        )
    ).scalar_one_or_none()

    if existing is not None:
        print(f"Jurisdiction '{KYLE_TX['name']}' already exists (id={existing.id}). Skipping.")
    else:
        j = Jurisdiction(**KYLE_TX)
        session.add(j)
        session.commit()
        print(f"Inserted jurisdiction '{j.name}' with id={j.id}")
