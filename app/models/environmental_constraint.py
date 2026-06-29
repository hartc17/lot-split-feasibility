from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class EnvironmentalConstraint(Base):
    __tablename__ = "environmental_constraints"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    constraint_type: Mapped[str] = mapped_column(
        Enum(
            "FLOOD_ZONE",
            "WETLAND",
            "STEEP_SLOPE",
            "SOIL_LIMITATION",
            "EASEMENT",
            "HISTORIC_OVERLAY",
            "OTHER_OVERLAY",
            name="constraint_type_enum",
        ),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(
        Enum("BLOCKING", "SIGNIFICANT", "MINOR", "INFORMATIONAL", name="constraint_severity_enum"),
        nullable=False,
    )
    coverage_pct: Mapped[float] = mapped_column(Float, nullable=False)
    detail: Mapped[dict | None] = mapped_column(JSONB)
    source: Mapped[str | None] = mapped_column(String(255))
    source_fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    parcel: Mapped[Parcel] = relationship(back_populates="environmental_constraints")  # noqa: F821
