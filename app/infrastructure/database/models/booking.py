"""Booking models matching the legacy database schema."""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, SmallInteger, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class Booking(Base):
    __tablename__ = "booking"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_booking_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    booking_number: Mapped[str] = mapped_column(String(7), nullable=False, unique=True)
    check_in: Mapped[date] = mapped_column(Date, nullable=False)
    check_out: Mapped[date] = mapped_column(Date, nullable=False)
    adults: Mapped[Optional[int]] = mapped_column(SmallInteger, default=1, server_default="1")
    children: Mapped[Optional[int]] = mapped_column(SmallInteger, default=0, server_default="0")
    babies: Mapped[Optional[int]] = mapped_column(SmallInteger, default=0, server_default="0")
    reminder_sent: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", server_default="'pending'")
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_reminder_stage: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    client_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    property_apartment_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("apartment.id"), nullable=True)
    property_cottage_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("cottage.id"), nullable=True)


class Calendar(Base):
    __tablename__ = "calendar"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_calendar_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="available", server_default="'available'")
    date: Mapped[date] = mapped_column(Date, nullable=False)
    property_apartment_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("apartment.id"), nullable=True)
    property_cottage_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("cottage.id"), nullable=True)
