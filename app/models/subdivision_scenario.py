from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SubdivisionScenario(Base):
    __tablename__ = "subdivision_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    scenario_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    num_resulting_lots: Mapped[int] = mapped_column(Integer, nullable=False)
    lot_layout_type: Mapped[str] = mapped_column(
        Enum(
            "SIMPLE_HALVE", "FRONTAGE_STRIP", "FLAG_LOT", "UNEVEN_SPLIT",
            name="lot_layout_type_enum",
        ),
        nullable=False,
    )
    resulting_lots: Mapped[dict] = mapped_column(JSONB, nullable=False)
    meets_min_lot_size: Mapped[bool] = mapped_column(Boolean, nullable=False)
    meets_min_frontage: Mapped[bool] = mapped_column(Boolean, nullable=False)
    requires_variance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_rezone: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_flag_lot_provision: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    subdivision_review_tier: Mapped[str] = mapped_column(
        Enum(
            "ADMINISTRATIVE_MINOR", "PLANNING_COMMISSION_MAJOR",
            name="subdivision_review_tier_enum",
        ),
        nullable=False,
    )
    engine_version: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parcel: Mapped["Parcel"] = relationship(back_populates="subdivision_scenarios")  # noqa: F821
