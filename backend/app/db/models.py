"""SQLAlchemy models for persistent research sessions and cached source data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Index, String, Text
from sqlalchemy import Uuid as SAUuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False
    )


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[SAUuid] = mapped_column(SAUuid(as_uuid=True), primary_key=True)
    external_id: Mapped[Optional[str]] = mapped_column(
        String(255), unique=True, index=True
    )

    sessions: Mapped[list["ResearchSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class ResearchSession(Base, TimestampMixin):
    __tablename__ = "research_sessions"

    id: Mapped[SAUuid] = mapped_column(SAUuid(as_uuid=True), primary_key=True)
    user_id: Mapped[Optional[SAUuid]] = mapped_column(
        SAUuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    name: Mapped[str] = mapped_column(
        String(255), default="Untitled session", nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(32), default="active", index=True, nullable=False
    )
    archived_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    turns: Mapped[list["ResearchTurn"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ResearchTurn.created_at",
    )
    user: Mapped[Optional[User]] = relationship(back_populates="sessions")


class ResearchTurn(Base, TimestampMixin):
    __tablename__ = "research_turns"

    id: Mapped[SAUuid] = mapped_column(SAUuid(as_uuid=True), primary_key=True)
    session_id: Mapped[SAUuid] = mapped_column(
        SAUuid(as_uuid=True),
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    citations: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    compressed_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    session: Mapped[ResearchSession] = relationship(back_populates="turns")

    __table_args__ = (
        Index("ix_research_turns_session_created", "session_id", "created_at"),
    )


class SourceCache(Base, TimestampMixin):
    __tablename__ = "source_cache"

    id: Mapped[SAUuid] = mapped_column(SAUuid(as_uuid=True), primary_key=True)

    query_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    source_name: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)

    __table_args__ = (
        Index("ux_source_cache_query_source", "query_hash", "source_name", unique=True),
    )
