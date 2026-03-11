"""Initial schema — papers, tags, paper_tags

Revision ID: 001
Revises:
Create Date: 2026-03-05
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "papers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("pmid", sa.String(20), nullable=False, unique=True, index=True),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("authors", JSONB, nullable=False, server_default="[]"),
        sa.Column("abstract", sa.Text, nullable=True),
        sa.Column("journal", sa.String(500), nullable=True),
        sa.Column("publication_date", sa.String(50), nullable=True),
        sa.Column("doi", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "tags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "paper_tags",
        sa.Column(
            "paper_id",
            UUID(as_uuid=True),
            sa.ForeignKey("papers.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )


def downgrade() -> None:
    op.drop_table("paper_tags")
    op.drop_table("tags")
    op.drop_table("papers")
