from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.jurisdiction import Jurisdiction
from app.models.zoning_district import ZoningDistrict

logger = logging.getLogger(__name__)


def resolve_zoning_district_id(
    zoning_code_raw: str | None,
    jurisdiction: Jurisdiction,
    session: Session,
) -> uuid.UUID | None:
    """
    Map a raw GIS zoning string to a ZoningDistrict.id for this jurisdiction.

    Returns None if:
    - zoning_code_raw is None or empty
    - no entry in jurisdiction.gis_zoning_code_map for this raw code
    - no ZoningDistrict row found in the DB for the canonical code

    Never raises — unmapped codes are an explicit data gap, not an error.
    """
    if not zoning_code_raw:
        return None

    code_map: dict = jurisdiction.gis_zoning_code_map or {}
    canonical_code = code_map.get(zoning_code_raw)

    if not canonical_code:
        logger.debug(
            "No zoning code mapping for raw='%s' in jurisdiction '%s'",
            zoning_code_raw,
            jurisdiction.name,
        )
        return None

    district_id = session.execute(
        select(ZoningDistrict.id).where(
            ZoningDistrict.jurisdiction_id == jurisdiction.id,
            ZoningDistrict.code == canonical_code,
        )
    ).scalar_one_or_none()

    if district_id is None:
        logger.debug(
            "Raw code '%s' maps to canonical '%s' but no ZoningDistrict row found "
            "for jurisdiction '%s'",
            zoning_code_raw,
            canonical_code,
            jurisdiction.name,
        )

    return district_id
