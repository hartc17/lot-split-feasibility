from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from geoalchemy2 import Geometry
from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Parcel(Base):
    __tablename__ = "parcels"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jurisdictions.id"), nullable=False
    )
    apn: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    address_normalized: Mapped[str | None] = mapped_column(String(500))
    geometry: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326), nullable=False)
    centroid: Mapped[object] = mapped_column(Geometry("POINT", srid=4326))
    area_sqft: Mapped[float] = mapped_column(Float, nullable=False)
    area_acres: Mapped[float] = mapped_column(Float, nullable=False)
    zoning_district_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zoning_districts.id"))
    zoning_code_raw: Mapped[str | None] = mapped_column(String(50))
    existing_structures_count: Mapped[int] = mapped_column(Integer, default=0)
    assessed_land_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    assessed_improvement_value: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_sale_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    last_sale_date: Mapped[date | None] = mapped_column(Date)
    owner_name: Mapped[str | None] = mapped_column(String(500))
    raw_assessor_data: Mapped[dict | None] = mapped_column(JSONB)
    data_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="parcels")  # noqa: F821
    zoning_district: Mapped[ZoningDistrict | None] = relationship(back_populates="parcels")  # noqa: F821
    environmental_constraints: Mapped[list[EnvironmentalConstraint]] = relationship(  # noqa: F821
        back_populates="parcel"
    )
    subdivision_scenarios: Mapped[list[SubdivisionScenario]] = relationship(back_populates="parcel")  # noqa: F821
    feasibility_reports: Mapped[list[FeasibilityReport]] = relationship(back_populates="parcel")  # noqa: F821
