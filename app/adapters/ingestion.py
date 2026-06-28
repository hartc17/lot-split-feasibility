from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.arcgis import ArcGISParcelAdapter
from app.adapters.base import JurisdictionConfig
from app.adapters.normalizer import normalize
from app.adapters.zoning_mapper import resolve_zoning_district_id
from app.models.jurisdiction import Jurisdiction
from app.models.parcel import Parcel

logger = logging.getLogger(__name__)


class ParcelIngestionService:
    """
    Orchestrates: fetch from county GIS → normalize → upsert into parcels table.
    Session management is the caller's responsibility.
    """

    def ingest_by_apn(
        self,
        apn: str,
        jurisdiction: Jurisdiction,
        session: Session,
    ) -> Parcel | None:
        """
        Fetch, normalize, and upsert one parcel.
        Returns the Parcel ORM object, or None if the county has no record for this APN.
        Raises ValueError if the Jurisdiction is not configured for GIS queries.
        """
        config = JurisdictionConfig.from_orm(jurisdiction)
        adapter = ArcGISParcelAdapter(config)

        record = adapter.fetch_by_apn(apn)
        if record is None:
            logger.info("No GIS record found for APN '%s' in '%s'", apn, jurisdiction.name)
            return None

        zoning_district_id = resolve_zoning_district_id(
            record.zoning_code_raw, jurisdiction, session
        )
        fields = normalize(record, jurisdiction.id, zoning_district_id)

        existing = session.execute(
            select(Parcel).where(
                Parcel.apn == apn,
                Parcel.jurisdiction_id == jurisdiction.id,
            )
        ).scalar_one_or_none()

        if existing is not None:
            for key, value in fields.items():
                setattr(existing, key, value)
            logger.debug("Updated existing parcel APN='%s'", apn)
            return existing

        parcel = Parcel(**fields, id=uuid.uuid4())
        session.add(parcel)
        logger.debug("Inserted new parcel APN='%s'", apn)
        return parcel
