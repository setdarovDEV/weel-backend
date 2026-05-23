"""User models matching the legacy database schema."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.connection import Base


class UserRoleEnum:
    ADMIN = "admin"
    CLIENT = "client"
    PARTNER = "partner"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    role: Mapped[str] = mapped_column(SAEnum(UserRoleEnum.ADMIN, UserRoleEnum.CLIENT, UserRoleEnum.PARTNER, name="user_role", native_enum=True), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(254), nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True, server_default="true")
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    legacy_admin_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)
    legacy_client_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    legacy_partner_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    fcm_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    device_type: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)


class UserSMSLog(Base):
    __tablename__ = "users_smslog"

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(32), nullable=False)
    purpose: Mapped[str] = mapped_column(String(16), nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)


class UserMap(Base):
    __tablename__ = "user_map"

    legacy_table: Mapped[str] = mapped_column(Text, primary_key=True)
    legacy_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
