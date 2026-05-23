"""Story models matching the legacy database schema."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


class Stories(Base):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_story_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    views: Mapped[Optional[int]] = mapped_column(Integer, default=0, server_default="0")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    verified_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    property_apartment_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("apartment.id"), nullable=True)
    property_cottage_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("cottage.id"), nullable=True)

    medias: Mapped[List["StoryMedia"]] = relationship(back_populates="story", lazy="selectin", cascade="all, delete-orphan")


class StoryMedia(Base):
    __tablename__ = "story_media"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_media_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    media: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[str] = mapped_column(String(10), nullable=False)
    story_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("stories.id", ondelete="CASCADE"), nullable=False)

    story: Mapped["Stories"] = relationship(back_populates="medias", lazy="selectin")
