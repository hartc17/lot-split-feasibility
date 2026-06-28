from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Jurisdiction(Base):
    __tablename__ = "jurisdictions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    jurisdiction_type: Mapped[str] = mapped_column(
        Enum("COUNTY_UNINCORPORATED", "CITY", "TOWNSHIP", name="jurisdiction_type_enum"),
        nullable=False,
    )
    fips_code: Mapped[str] = mapped_column(String(10), nullable=False)
    subdivision_authority_url: Mapped[str | None] = mapped_column(Text)
    zoning_ordinance_url: Mapped[str | None] = mapped_column(Text)
    minor_subdivision_threshold: Mapped[int] = mapped_column(Integer, nullable=False)
    minor_subdivision_process_notes: Mapped[str | None] = mapped_column(Text)
    # GIS adapter config — all per-jurisdiction data lives here, not in Python files
    gis_feature_server_url: Mapped[str | None] = mapped_column(Text)
    gis_field_map: Mapped[dict | None] = mapped_column(JSONB)
    gis_zoning_code_map: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    zoning_districts: Mapped[list["ZoningDistrict"]] = relationship(back_populates="jurisdiction")  # noqa: F821
    parcels: Mapped[list["Parcel"]] = relationship(back_populates="jurisdiction")  # noqa: F821
