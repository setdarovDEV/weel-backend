"""Location models matching the legacy database schema."""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import BigInteger, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


class Region(Base):
    __tablename__ = "region"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    title_en: Mapped[str] = mapped_column(String(100), nullable=False)
    img: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    districts: Mapped[List["District"]] = relationship(back_populates="region", lazy="selectin")


class District(Base):
    __tablename__ = "district"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title_uz: Mapped[str] = mapped_column(String(100), nullable=False)
    title_ru: Mapped[str] = mapped_column(String(100), nullable=False)
    title_en: Mapped[str] = mapped_column(String(100), nullable=False)
    region_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("region.id"), nullable=False)

    region: Mapped["Region"] = relationship(back_populates="districts", lazy="selectin")


class Prefecture(Base):
    __tablename__ = "prefecture"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ru_name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, server_default="now()")


class DistrictPrefecture(Base):
    __tablename__ = "district_prefecture"

    district_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("district.id", ondelete="CASCADE"), primary_key=True)
    prefecture_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("prefecture.id", ondelete="CASCADE"), primary_key=True)
