"""initial_schema

Revision ID: a1f1873cc084
Revises:
Create Date: 2026-06-28

"""

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a1f1873cc084"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    jurisdiction_type_enum = sa.Enum(
        "COUNTY_UNINCORPORATED",
        "CITY",
        "TOWNSHIP",
        name="jurisdiction_type_enum",
    )
    constraint_type_enum = sa.Enum(
        "FLOOD_ZONE",
        "WETLAND",
        "STEEP_SLOPE",
        "SOIL_LIMITATION",
        "EASEMENT",
        "HISTORIC_OVERLAY",
        "OTHER_OVERLAY",
        name="constraint_type_enum",
    )
    constraint_severity_enum = sa.Enum(
        "BLOCKING",
        "SIGNIFICANT",
        "MINOR",
        "INFORMATIONAL",
        name="constraint_severity_enum",
    )
    lot_layout_type_enum = sa.Enum(
        "SIMPLE_HALVE",
        "FRONTAGE_STRIP",
        "FLAG_LOT",
        "UNEVEN_SPLIT",
        name="lot_layout_type_enum",
    )
    subdivision_review_tier_enum = sa.Enum(
        "ADMINISTRATIVE_MINOR",
        "PLANNING_COMMISSION_MAJOR",
        name="subdivision_review_tier_enum",
    )
    report_status_enum = sa.Enum(
        "PENDING",
        "DATA_GATHERING",
        "CALCULATING",
        "COMPLETE",
        "FAILED",
        name="report_status_enum",
    )
    recommendation_enum = sa.Enum(
        "PURSUE",
        "PURSUE_WITH_CAUTION",
        "UNLIKELY",
        "NOT_FEASIBLE",
        name="recommendation_enum",
    )

    op.create_table(
        "jurisdictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("jurisdiction_type", jurisdiction_type_enum, nullable=False),
        sa.Column("fips_code", sa.String(10), nullable=False),
        sa.Column("subdivision_authority_url", sa.Text),
        sa.Column("zoning_ordinance_url", sa.Text),
        sa.Column("minor_subdivision_threshold", sa.Integer, nullable=False),
        sa.Column("minor_subdivision_process_notes", sa.Text),
        sa.Column("gis_feature_server_url", sa.Text),
        sa.Column("gis_field_map", postgresql.JSONB),
        sa.Column("gis_zoning_code_map", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "zoning_districts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "jurisdiction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("min_lot_area_sqft", sa.Integer, nullable=False),
        sa.Column("min_lot_width_ft", sa.Integer, nullable=False),
        sa.Column("min_lot_depth_ft", sa.Integer),
        sa.Column("max_density_units_per_acre", sa.Float),
        sa.Column("setback_front_ft", sa.Integer, nullable=False),
        sa.Column("setback_side_ft", sa.Integer, nullable=False),
        sa.Column("setback_side_corner_ft", sa.Integer),
        sa.Column("setback_rear_ft", sa.Integer, nullable=False),
        sa.Column("max_height_ft", sa.Integer),
        sa.Column("max_lot_coverage_pct", sa.Float),
        sa.Column("max_far", sa.Float),
        sa.Column(
            "requires_public_road_frontage", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column("min_road_frontage_ft", sa.Integer),
        sa.Column("allows_flag_lots", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("flag_lot_min_access_strip_ft", sa.Integer),
        sa.Column("source_ordinance_section", sa.String(100)),
        sa.Column("last_verified_date", sa.Date),
        sa.Column("last_verified_by", sa.String(255)),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "parcels",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "jurisdiction_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("jurisdictions.id"),
            nullable=False,
        ),
        sa.Column("apn", sa.String(100), nullable=False, index=True),
        sa.Column("address_normalized", sa.String(500)),
        sa.Column("geometry", geoalchemy2.Geometry("POLYGON", srid=4326), nullable=False),
        sa.Column("centroid", geoalchemy2.Geometry("POINT", srid=4326)),
        sa.Column("area_sqft", sa.Float, nullable=False),
        sa.Column("area_acres", sa.Float, nullable=False),
        sa.Column(
            "zoning_district_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("zoning_districts.id"),
        ),
        sa.Column("zoning_code_raw", sa.String(50)),
        sa.Column("existing_structures_count", sa.Integer, server_default="0"),
        sa.Column("assessed_land_value", sa.Numeric(12, 2)),
        sa.Column("assessed_improvement_value", sa.Numeric(12, 2)),
        sa.Column("last_sale_price", sa.Numeric(12, 2)),
        sa.Column("last_sale_date", sa.Date),
        sa.Column("owner_name", sa.String(500)),
        sa.Column("raw_assessor_data", postgresql.JSONB),
        sa.Column("data_fetched_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "environmental_constraints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parcel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parcels.id"), nullable=False
        ),
        sa.Column("constraint_type", constraint_type_enum, nullable=False),
        sa.Column("severity", constraint_severity_enum, nullable=False),
        sa.Column("coverage_pct", sa.Float, nullable=False),
        sa.Column("detail", postgresql.JSONB),
        sa.Column("source", sa.String(255)),
        sa.Column("source_fetched_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "subdivision_scenarios",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parcel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parcels.id"), nullable=False
        ),
        sa.Column("scenario_rank", sa.Integer, nullable=False),
        sa.Column("num_resulting_lots", sa.Integer, nullable=False),
        sa.Column("lot_layout_type", lot_layout_type_enum, nullable=False),
        sa.Column("resulting_lots", postgresql.JSONB, nullable=False),
        sa.Column("meets_min_lot_size", sa.Boolean, nullable=False),
        sa.Column("meets_min_frontage", sa.Boolean, nullable=False),
        sa.Column("requires_variance", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("requires_rezone", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "requires_flag_lot_provision", sa.Boolean, nullable=False, server_default="false"
        ),
        sa.Column("subdivision_review_tier", subdivision_review_tier_enum, nullable=False),
        sa.Column("engine_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "feasibility_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "parcel_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("parcels.id"), nullable=False
        ),
        sa.Column("requested_by", sa.String(255)),
        sa.Column("status", report_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("overall_score", sa.Integer),
        sa.Column("recommendation", recommendation_enum),
        sa.Column(
            "primary_scenario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("subdivision_scenarios.id"),
        ),
        sa.Column("risk_flags", postgresql.JSONB),
        sa.Column("valuation_summary", postgresql.JSONB),
        sa.Column("generated_pdf_url", sa.Text),
        sa.Column("generated_html_url", sa.Text),
        sa.Column("error_detail", sa.Text),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table("feasibility_reports")
    op.drop_table("subdivision_scenarios")
    op.drop_table("environmental_constraints")
    op.drop_table("parcels")
    op.drop_table("zoning_districts")
    op.drop_table("jurisdictions")

    for enum_name in [
        "recommendation_enum",
        "report_status_enum",
        "subdivision_review_tier_enum",
        "lot_layout_type_enum",
        "constraint_severity_enum",
        "constraint_type_enum",
        "jurisdiction_type_enum",
    ]:
        sa.Enum(name=enum_name).drop(op.get_bind(), checkfirst=True)
