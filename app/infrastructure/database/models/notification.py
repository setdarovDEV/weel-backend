"""Notification model matching the legacy database schema."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class Notification(Base):
    __tablename__ = "notification"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_client_notification_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    legacy_partner_notification_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    push_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notification_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False)
    is_for_every_one: Mapped[bool] = mapped_column(Boolean, nullable=False)
    recipient_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    recipient_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="'{}'::jsonb", nullable=False)
