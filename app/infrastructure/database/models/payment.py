"""Payment/transaction models matching the legacy database schema."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class TransactionHistory(Base):
    __tablename__ = "transaction_history"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_booking_transaction_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    legacy_payment_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    booking_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("booking.id"), nullable=False)
    client_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    partner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD", server_default="'USD'")
    transaction_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hold_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    type: Mapped[Optional[str]] = mapped_column(String(4), nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    card_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    extra_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
