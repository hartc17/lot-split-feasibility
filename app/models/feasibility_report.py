from __future__ import annotations
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class FeasibilityReport(Base):
    __tablename__ = "feasibility_reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parcel_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("parcels.id"), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(
        Enum(
            "PENDING", "DATA_GATHERING", "CALCULATING", "COMPLETE", "FAILED",
            name="report_status_enum",
        ),
        nullable=False,
        default="PENDING",
    )
    overall_score: Mapped[int | None] = mapped_column(Integer)
    recommendation: Mapped[str | None] = mapped_column(
        Enum(
            "PURSUE", "PURSUE_WITH_CAUTION", "UNLIKELY", "NOT_FEASIBLE",
            name="recommendation_enum",
        ),
    )
    primary_scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("subdivision_scenarios.id")
    )
    risk_flags: Mapped[dict | None] = mapped_column(JSONB)
    valuation_summary: Mapped[dict | None] = mapped_column(JSONB)
    generated_pdf_url: Mapped[str | None] = mapped_column(Text)
    generated_html_url: Mapped[str | None] = mapped_column(Text)
    error_detail: Mapped[str | None] = mapped_column(Text)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    parcel: Mapped["Parcel"] = relationship(back_populates="feasibility_reports")  # noqa: F821
    primary_scenario: Mapped["SubdivisionScenario | None"] = relationship()  # noqa: F821
