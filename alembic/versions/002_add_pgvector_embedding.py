"""Add pgvector extension and embedding column to papers

Revision ID: 002
Revises: 001
Create Date: 2026-03-17
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Raw SQL because Alembic's autogenerate doesn't support pgvector
    # extension creation or HNSW index syntax.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.add_column("papers", sa.Column("embedding", Vector(1536), nullable=True))
    op.execute(
        "CREATE INDEX ix_papers_embedding_hnsw ON papers "
        "USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.drop_index("ix_papers_embedding_hnsw", table_name="papers")
    op.drop_column("papers", "embedding")
    op.execute("DROP EXTENSION IF EXISTS vector")
