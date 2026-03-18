"""Add paper_tags.tag_id index and updated_at trigger on papers

Revision ID: 003
Revises: 002
Create Date: 2026-03-18
"""

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_paper_tags_tag_id", "paper_tags", ["tag_id"])

    op.execute("""
        CREATE OR REPLACE FUNCTION update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
    """)
    op.execute("""
        CREATE TRIGGER trg_papers_updated_at
        BEFORE UPDATE ON papers
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_papers_updated_at ON papers")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column()")
    op.drop_index("ix_paper_tags_tag_id", table_name="paper_tags")
