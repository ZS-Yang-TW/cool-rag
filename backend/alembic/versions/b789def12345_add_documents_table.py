"""add documents table for tracking document status

Revision ID: b789def12345
Revises: afe456c4fa28
Create Date: 2026-02-04 10:02:30.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "b789def12345"
down_revision = "afe456c4fa28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for document status
    documentstatus_enum = sa.Enum('indexed', 'modified', 'new', 'deleted', name='documentstatus', create_type=True)
    
    # Create documents table
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            documentstatus_enum,
            nullable=False,
        ),
        sa.Column("indexed_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_documents_id"), "documents", ["id"], unique=False)
    op.create_index(
        op.f("ix_documents_filename"), "documents", ["filename"], unique=True
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_documents_filename"), table_name="documents")
    op.drop_index(op.f("ix_documents_id"), table_name="documents")
    op.drop_table("documents")
    op.execute("DROP TYPE documentstatus")
    op.execute("DROP TYPE documentstatus")
