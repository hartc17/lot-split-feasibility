from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ZoningDistrict(Base):
    __tablename__ = "zoning_districts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jurisdiction_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jurisdictions.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    min_lot_area_sqft: Mapped[int] = mapped_column(Integer, nullable=False)
    min_lot_width_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    min_lot_depth_ft: Mapped[int | None] = mapped_column(Integer)
    max_density_units_per_acre: Mapped[float | None] = mapped_column(Float)
    setback_front_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    setback_side_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    setback_side_corner_ft: Mapped[int | None] = mapped_column(Integer)
    setback_rear_ft: Mapped[int] = mapped_column(Integer, nullable=False)
    max_height_ft: Mapped[int | None] = mapped_column(Integer)
    max_lot_coverage_pct: Mapped[float | None] = mapped_column(Float)
    max_far: Mapped[float | None] = mapped_column(Float)
    requires_public_road_frontage: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    min_road_frontage_ft: Mapped[int | None] = mapped_column(Integer)
    allows_flag_lots: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    flag_lot_min_access_strip_ft: Mapped[int | None] = mapped_column(Integer)
    source_ordinance_section: Mapped[str | None] = mapped_column(String(100))
    last_verified_date: Mapped[date | None] = mapped_column(Date)
    last_verified_by: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    jurisdiction: Mapped[Jurisdiction] = relationship(back_populates="zoning_districts")  # noqa: F821
    parcels: Mapped[list[Parcel]] = relationship(back_populates="zoning_district")  # noqa: F821
