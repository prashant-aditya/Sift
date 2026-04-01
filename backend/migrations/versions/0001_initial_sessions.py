from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_sessions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_external_id", "users", ["external_id"], unique=True)

    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_research_sessions_status", "research_sessions", ["status"])
    op.create_index(
        "ix_research_sessions_updated_at", "research_sessions", ["updated_at"]
    )
    op.create_index("ix_research_sessions_user_id", "research_sessions", ["user_id"])

    op.create_table(
        "research_turns",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("session_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations", sa.JSON(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["research_sessions.id"],
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_research_turns_session_id", "research_turns", ["session_id"])
    op.create_index(
        "ix_research_turns_session_created",
        "research_turns",
        ["session_id", "created_at"],
    )

    op.create_table(
        "source_cache",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("query_hash", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_source_cache_query_hash", "source_cache", ["query_hash"])
    op.create_index("ix_source_cache_source_name", "source_cache", ["source_name"])
    op.create_index(
        "ux_source_cache_query_source",
        "source_cache",
        ["query_hash", "source_name"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_source_cache_query_source", table_name="source_cache")
    op.drop_index("ix_source_cache_source_name", table_name="source_cache")
    op.drop_index("ix_source_cache_query_hash", table_name="source_cache")
    op.drop_table("source_cache")

    op.drop_index("ix_research_turns_session_created", table_name="research_turns")
    op.drop_index("ix_research_turns_session_id", table_name="research_turns")
    op.drop_table("research_turns")

    op.drop_index("ix_research_sessions_user_id", table_name="research_sessions")
    op.drop_index("ix_research_sessions_updated_at", table_name="research_sessions")
    op.drop_index("ix_research_sessions_status", table_name="research_sessions")
    op.drop_table("research_sessions")

    op.drop_index("ix_users_external_id", table_name="users")
    op.drop_table("users")
