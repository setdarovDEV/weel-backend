"""Property models matching the legacy database schema."""

import uuid
from datetime import datetime, time, date
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.connection import Base


class Apartment(Base):
    __tablename__ = "apartment"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_property_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(75), nullable=False)
    title_sort: Mapped[str] = mapped_column(String(75), nullable=False)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String(10), default="waiting", server_default="'waiting'")
    is_archived: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_recommended: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, server_default="0")
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD", server_default="'USD'")
    img: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    partner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    verified_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(17, 14), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(17, 14), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    district_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    shaharcha_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    mahalla_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    check_in: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    check_out: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_allowed_alcohol: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_allowed_corporate: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_allowed_pets: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_quiet_hours: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    apartment_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    home_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entrance_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    floor_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pass_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    services: Mapped[Optional[list[uuid.UUID]]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    prefecture_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("prefecture.id"), nullable=True)
    guests: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)


class Cottage(Base):
    __tablename__ = "cottage"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    legacy_property_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(75), nullable=False)
    title_sort: Mapped[str] = mapped_column(String(75), nullable=False)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verification_status: Mapped[Optional[str]] = mapped_column(String(10), default="waiting", server_default="'waiting'")
    is_archived: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_recommended: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    weekend_only_sunday_inclusive: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0, server_default="0")
    price_per_person: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    price_on_working_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    price_on_weekends: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD", server_default="'USD'")
    img: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    partner_user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    verified_by_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(17, 14), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(17, 14), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description_en: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description_uz: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    check_in: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    check_out: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    is_allowed_alcohol: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_allowed_corporate: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_allowed_pets: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    is_quiet_hours: Mapped[Optional[bool]] = mapped_column(Boolean, default=False, server_default="false")
    services: Mapped[Optional[list[uuid.UUID]]] = mapped_column(ARRAY(UUID(as_uuid=True)), nullable=True)
    prefecture_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("prefecture.id"), nullable=True)
    region_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    district_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    guests: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    prices: Mapped[List["CottagePrice"]] = relationship(back_populates="cottage", lazy="selectin")


class CottagePrice(Base):
    __tablename__ = "cottage_price"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cottage_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("cottage.id", ondelete="CASCADE"), nullable=False)
    month_from: Mapped[date] = mapped_column(Date, nullable=False)
    month_to: Mapped[date] = mapped_column(Date, nullable=False)
    price_per_person: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    price_on_working_days: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    price_on_weekends: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    cottage: Mapped["Cottage"] = relationship(back_populates="prices", lazy="selectin")


class Service(Base):
    __tablename__ = "services"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    icon_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    title_ru: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    type: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)


class PropertyMap(Base):
    __tablename__ = "property_map"

    legacy_property_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    property_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_table: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[int] = mapped_column(BigInteger, nullable=False)


class PropertyType(Base):
    __tablename__ = "property_type"

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)


class PropertyService(Base):
    __tablename__ = "property_service"

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("property_type.guid"), nullable=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)


class PropertyImage(Base):
    __tablename__ = "property_image"

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("property.guid"), nullable=False)
    image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)


class PropertyServiceLink(Base):
    __tablename__ = "property_service_link"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("property.guid"), nullable=False)
    service_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("property_service.guid"), nullable=False)

    service: Mapped["PropertyService"] = relationship("PropertyService", lazy="selectin")


class PropertyPrice(Base):
    __tablename__ = "property_price"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    property_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("property.guid"), nullable=False)
    month_from: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    month_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    price_per_person: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    price_on_working_days: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    price_on_weekends: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)


class Property(Base):
    __tablename__ = "property"

    guid: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    legacy_property_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    is_verified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    verification_status: Mapped[Optional[str]] = mapped_column(String(20), default="waiting")
    is_archived: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    is_recommended: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    comment_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[Optional[str]] = mapped_column(String(3), default="USD")
    img: Mapped[Optional[list[str]]] = mapped_column(ARRAY(Text), nullable=True)
    partner_user_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(17, 14), nullable=True)
    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(17, 14), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    region_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    district_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    prefecture_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    guests: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bedrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    beds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    bathrooms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_allowed_alcohol: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    property_type_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("property_type.guid"), nullable=True)

    location_ref: Mapped[Optional["Location"]] = relationship("Location", lazy="selectin", viewonly=True, primaryjoin="foreign(Property.region_id)==Location.region_id")
    images: Mapped[List["PropertyImage"]] = relationship("PropertyImage", backref="property", lazy="selectin")
    prices: Mapped[List["PropertyPrice"]] = relationship("PropertyPrice", backref="property", lazy="selectin")
    property_type: Mapped[Optional["PropertyType"]] = relationship("PropertyType", lazy="selectin")
    service_links: Mapped[List["PropertyServiceLink"]] = relationship("PropertyServiceLink", backref="property", lazy="selectin")
