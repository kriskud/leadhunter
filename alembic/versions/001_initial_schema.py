"""Initial schema — leads, enrichment, qualification, message drafts."""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "leads",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("website", sa.String(length=512), nullable=True),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("city", sa.String(length=128), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "NEW",
                "ENRICHED",
                "QUALIFIED",
                "SCORED",
                "MESSAGE_GENERATED",
                "REJECTED",
                name="lead_status",
                native_enum=False,
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "enrichment_data",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("page_title", sa.String(length=512), nullable=True),
        sa.Column("page_text", sa.Text(), nullable=True),
        sa.Column("emails", sa.Text(), nullable=True),
        sa.Column("phones", sa.Text(), nullable=True),
        sa.Column("social_links", sa.Text(), nullable=True),
        sa.Column("booking_links", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
    )

    op.create_table(
        "qualifications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("is_private_practice", sa.Boolean(), nullable=True),
        sa.Column("estimated_staff_count", sa.Integer(), nullable=True),
        sa.Column("has_online_booking", sa.Boolean(), nullable=True),
        sa.Column("booking_provider", sa.String(length=128), nullable=True),
        sa.Column("has_crm", sa.Boolean(), nullable=True),
        sa.Column("business_type", sa.String(length=128), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("lead_id"),
    )

    op.create_table(
        "message_drafts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("lead_id", sa.Integer(), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lead_id"], ["leads.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("message_drafts")
    op.drop_table("qualifications")
    op.drop_table("enrichment_data")
    op.drop_table("leads")
