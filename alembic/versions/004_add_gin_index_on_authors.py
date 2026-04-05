"""Add GIN index on papers.authors JSONB column

Revision ID: 004
Revises: 003
Create Date: 2026-04-04
"""

from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_papers_authors_gin", "papers", ["authors"], postgresql_using="gin"
    )


def downgrade() -> None:
    op.drop_index("ix_papers_authors_gin", table_name="papers")
