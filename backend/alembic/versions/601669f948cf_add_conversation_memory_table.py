"""add_conversation_memory_table

Revision ID: 601669f948cf
Revises: b789def12345
Create Date: 2026-02-05 16:45:47.921052

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision: str = "601669f948cf"
down_revision: Union[str, Sequence[str], None] = "b789def12345"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - create conversation_memories table for hierarchical memory."""
    op.create_table(
        "conversation_memories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "session_id",
            sa.String(length=255),
            nullable=False,
            comment="會話 session ID",
        ),
        sa.Column(
            "summary", sa.Text(), nullable=True, comment="對話摘要（壓縮的歷史脈絡）"
        ),
        sa.Column(
            "summary_updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="摘要最後更新時間",
        ),
        sa.Column(
            "message_count",
            sa.Integer(),
            nullable=True,
            server_default="0",
            comment="已摘要的訊息數量",
        ),
        sa.Column(
            "structured_data",
            JSON(),
            nullable=True,
            comment="結構化長期記憶（專案資訊、使用者偏好等）",
        ),
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
    op.create_index(
        op.f("ix_conversation_memories_id"),
        "conversation_memories",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_conversation_memories_session_id"),
        "conversation_memories",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema - drop conversation_memories table."""
    op.drop_index(
        op.f("ix_conversation_memories_session_id"), table_name="conversation_memories"
    )
    op.drop_index(
        op.f("ix_conversation_memories_id"), table_name="conversation_memories"
    )
    op.drop_table("conversation_memories")
