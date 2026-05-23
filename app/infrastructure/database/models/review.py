"""Review model matching the legacy database schema."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class Review(Base):
    __tablename__ = "review"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_review_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(2, 1), default=1, server_default="1")
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_hidden: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    apartment_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("apartment.id"), nullable=True)
    cottage_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("cottage.id"), nullable=True)
