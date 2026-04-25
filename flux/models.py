"""Flux database models — core engine tables.

All tables are generic. Plugin-specific data lives in JSON columns.
Adding a new plugin never requires a core schema migration.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from flux.db import Base


def _now() -> datetime:
    """Return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


def _new_id() -> str:
    """Generate a URL-safe unique identifier."""
    return uuid.uuid4().hex


class Plugin(Base):
    """Registered content plugins."""

    __tablename__ = "plugins"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    version: Mapped[str] = mapped_column(String(16), nullable=False)
    api_version: Mapped[str] = mapped_column(String(8), nullable=False)
    module_path: Mapped[str] = mapped_column(String(256), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_schema: Mapped[Optional[str]] = mapped_column(Text)
    installed_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    pipelines: Mapped[list["Pipeline"]] = relationship(
        "Pipeline", back_populates="plugin", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Plugin {self.name} v{self.version}>"


class Pipeline(Base):
    """Automation pipeline — one per content stream."""

    __tablename__ = "pipelines"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    plugin_id: Mapped[str] = mapped_column(
        ForeignKey("plugins.id", ondelete="RESTRICT"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    config_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    plugin: Mapped["Plugin"] = relationship("Plugin", back_populates="pipelines")
    ingredients: Mapped[list["Ingredient"]] = relationship(
        "Ingredient", back_populates="pipeline", cascade="all, delete-orphan"
    )
    produced_content: Mapped[list["ProducedContent"]] = relationship(
        "ProducedContent", back_populates="pipeline", cascade="all, delete-orphan"
    )
    workers: Mapped[list["PlatformWorker"]] = relationship(
        "PlatformWorker", secondary="pipeline_workers", back_populates="pipelines"
    )

    def __repr__(self) -> str:
        return f"<Pipeline {self.name}>"


class PlatformWorker(Base):
    """Social media account / publishing destination."""

    __tablename__ = "platform_workers"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    platform: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # youtube, instagram, telegram, tiktok, x
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    credentials_json: Mapped[str] = mapped_column(Text, default="{}")
    schedule_cron: Mapped[Optional[str]] = mapped_column(String(64))
    caption_template_override: Mapped[Optional[str]] = mapped_column(Text)
    hashtags_json: Mapped[Optional[str]] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_error_message: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    pipelines: Mapped[list["Pipeline"]] = relationship(
        "Pipeline", secondary="pipeline_workers", back_populates="workers"
    )
    post_records: Mapped[list["PostRecord"]] = relationship(
        "PostRecord", back_populates="worker", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<PlatformWorker {self.platform}:{self.display_name}>"


class PipelineWorker(Base):
    """Junction table: pipelines <-> platform_workers."""

    __tablename__ = "pipeline_workers"

    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), primary_key=True
    )
    worker_id: Mapped[str] = mapped_column(
        ForeignKey("platform_workers.id", ondelete="CASCADE"), primary_key=True
    )


class Ingredient(Base):
    """Raw source material fetched by a plugin."""

    __tablename__ = "ingredients"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    source_url: Mapped[Optional[str]] = mapped_column(Text)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending"
    )  # pending, approved, rejected
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    duration_secs: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    pipeline: Mapped["Pipeline"] = relationship("Pipeline", back_populates="ingredients")

    def __repr__(self) -> str:
        return f"<Ingredient {self.type}:{self.status}>"


class ProducedContent(Base):
    """Rendered artifact ready for publishing."""

    __tablename__ = "produced_content"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    pipeline_id: Mapped[str] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False
    )
    ingredient_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    render_method: Mapped[Optional[str]] = mapped_column(
        String(32)
    )  # video_compose, image_compose, text_only, passthrough
    file_path: Mapped[Optional[str]] = mapped_column(Text)
    thumbnail_path: Mapped[Optional[str]] = mapped_column(Text)
    content_meta_json: Mapped[Optional[str]] = mapped_column(Text)
    caption_text: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="rendering"
    )  # rendering, rendered, ready, published, failed
    render_log: Mapped[Optional[str]] = mapped_column(Text)
    rendered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    ready_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    pipeline: Mapped["Pipeline"] = relationship(
        "Pipeline", back_populates="produced_content"
    )
    post_records: Mapped[list["PostRecord"]] = relationship(
        "PostRecord", back_populates="produced_content", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ProducedContent {self.status}>"


class PostRecord(Base):
    """Immutable audit trail of every post attempt."""

    __tablename__ = "post_records"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_new_id)
    produced_content_id: Mapped[str] = mapped_column(
        ForeignKey("produced_content.id", ondelete="CASCADE"), nullable=False
    )
    worker_id: Mapped[str] = mapped_column(
        ForeignKey("platform_workers.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # pending, published, failed
    platform_post_id: Mapped[Optional[str]] = mapped_column(Text)
    platform_url: Mapped[Optional[str]] = mapped_column(Text)
    caption_used: Mapped[Optional[str]] = mapped_column(Text)
    error_log: Mapped[Optional[str]] = mapped_column(Text)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    produced_content: Mapped["ProducedContent"] = relationship(
        "ProducedContent", back_populates="post_records"
    )
    worker: Mapped["PlatformWorker"] = relationship(
        "PlatformWorker", back_populates="post_records"
    )

    __table_args__ = (
        UniqueConstraint("produced_content_id", "worker_id", name="uq_post_dedup"),
    )

    def __repr__(self) -> str:
        return f"<PostRecord {self.status}>"


class ActivityLog(Base):
    """System event log."""

    __tablename__ = "activity_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)
    level: Mapped[str] = mapped_column(
        String(16), nullable=False
    )  # info, warn, error, critical
    pipeline_id: Mapped[Optional[str]] = mapped_column(String(32))
    worker_id: Mapped[Optional[str]] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text)

    def __repr__(self) -> str:
        return f"<ActivityLog {self.level}:{self.event_type}>"


class Setting(Base):
    """Key-value runtime configuration."""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    def __repr__(self) -> str:
        return f"<Setting {self.key}>"
