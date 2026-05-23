from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException
from app.core.logging_config import get_logger
from app.infrastructure.database.models.property import (
    Property,
    PropertyImage,
    PropertyLocalization,
    PropertyPricingTier,
    PropertyService,
    PropertyServiceAssignment,
    PropertyType,
)
from app.infrastructure.database.models.user import PartnerProfile

logger = get_logger(__name__)


class PropertyApplicationService:
    """Application service for Property aggregate use cases (practical 3NF/4NF)."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_property_types(self) -> List[PropertyType]:
        result = await self._db.execute(select(PropertyType))
        return list(result.scalars().all())

    async def get_property_detail(self, property_id: str) -> Property:
        result = await self._db.execute(
            select(Property)
            .where(Property.guid == property_id, Property.is_archived == False)
            .options(
                selectinload(Property.localizations),
                selectinload(Property.images),
                selectinload(Property.service_assignments).selectinload(PropertyServiceAssignment.service).selectinload(PropertyService.localizations),
                selectinload(Property.pricing_tiers),
                selectinload(Property.partner),
                selectinload(Property.location_ref),
            )
        )
        prop: Optional[Property] = result.scalar_one_or_none()
        if not prop:
            raise NotFoundException("Property not found")
        return prop

    async def list_properties(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        city: Optional[str] = None,
        property_type_id: Optional[str] = None,
        is_recommended: Optional[bool] = None,
    ) -> List[Property]:
        query = select(Property).where(Property.is_archived == False)
        if city:
            query = query.where(Property.city.ilike(f"%{city}%"))
        if property_type_id:
            query = query.where(Property.property_type_id == property_type_id)
        if is_recommended is not None:
            query = query.where(Property.is_recommended == is_recommended)

        query = query.offset(skip).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def create_property(self, partner_id: str, data: dict) -> Property:
        partner_result = await self._db.execute(
            select(PartnerProfile).where(PartnerProfile.user_id == partner_id)
        )
        partner = partner_result.scalar_one_or_none()
        if not partner:
            raise NotFoundException("Partner not found")

        property_type_id = data.get("property_type_id")
        pt_result = await self._db.execute(
            select(PropertyType).where(PropertyType.guid == property_type_id)
        )
        if not pt_result.scalar_one_or_none():
            raise NotFoundException("Property type not found")

        # Core property with merged 1:1 facts
        prop = Property(
            partner_id=partner_id,
            property_type_id=property_type_id,
            title=data.get("title", ""),
            currency=data.get("currency", "UZS"),
            # Location (merged)
            latitude=data.get("latitude"),
            longitude=data.get("longitude"),
            city=data.get("city", ""),
            location_id=data.get("location_id"),
            # Accommodation (merged)
            guests=data.get("guests", 1),
            bedrooms=data.get("bedrooms", 0),
            beds=data.get("beds", 1),
            bathrooms=data.get("bathrooms", 1),
            # House Rules (merged)
            check_in_time=data.get("check_in_time"),
            check_out_time=data.get("check_out_time"),
            is_allowed_alcohol=data.get("is_allowed_alcohol", False),
            is_allowed_pets=data.get("is_allowed_pets", False),
            is_allowed_corporate=data.get("is_allowed_corporate", False),
            is_quiet_hours=data.get("is_quiet_hours", False),
            # Apartment Details (merged, nullable for cottages)
            apartment_number=data.get("apartment_number"),
            home_number=data.get("home_number"),
            entrance_number=data.get("entrance_number"),
            floor_number=data.get("floor_number"),
            pass_code=data.get("pass_code"),
        )
        self._db.add(prop)
        await self._db.flush()

        # Localization (multi-language -> separate)
        desc = data.get("description")
        if desc:
            self._db.add(
                PropertyLocalization(
                    property_id=prop.guid, language_code="ru", description=desc
                )
            )

        # Pricing Tiers (1:N -> separate)
        prices = data.get("prices", [])
        for price_data in prices:
            self._db.add(
                PropertyPricingTier(
                    property_id=prop.guid,
                    month_from=price_data.get("month_from", 1),
                    month_to=price_data.get("month_to", 12),
                    price_per_person=price_data.get("price_per_person", 0),
                    price_on_working_days=price_data.get("price_on_working_days", 0),
                    price_on_weekends=price_data.get("price_on_weekends", 0),
                )
            )

        # Service Assignments (M2M -> junction)
        service_ids = data.get("service_ids", [])
        for sid in service_ids:
            self._db.add(PropertyServiceAssignment(property_id=prop.guid, service_id=sid))

        await self._db.flush()
        logger.info(f"Property created {prop.guid} by partner {partner_id}")
        return prop
