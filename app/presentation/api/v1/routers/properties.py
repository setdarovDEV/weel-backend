from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.property_service import PropertyApplicationService
from app.infrastructure.database.models.user import User
from app.presentation.api.v1.deps import get_current_partner, get_db
from app.presentation.api.schemas.property import (
    PropertyCreateRequest,
    PropertyDetailResponse,
    PropertyListItem,
    PropertyTypeRead,
)

router = APIRouter()


def _build_property_list_item(p) -> PropertyListItem:
    """Assemble PropertyListItem from merged 3NF/4NF property."""
    imgs = p.images or []
    return PropertyListItem(
        guid=str(p.guid),
        title=p.title,
        city=p.city,
        country=p.country,
        guests=p.guests,
        bedrooms=p.bedrooms,
        beds=p.beds,
        bathrooms=p.bathrooms,
        is_recommended=p.is_recommended,
        verification_status=p.verification_status,
        images=[
            {"guid": str(img.guid), "image_url": img.image_url, "order": img.order}
            for img in imgs
        ],
    )


def _build_property_detail(p) -> PropertyDetailResponse:
    """Assemble PropertyDetailResponse from merged property."""
    imgs = p.images or []
    prices = p.pricing_tiers or []
    services = p.service_assignments or []

    # Get default description (e.g., Russian)
    descriptions = {loc.language_code: loc.description for loc in (p.localizations or [])}
    description = descriptions.get("ru") or descriptions.get("uz") or next(iter(descriptions.values()), None)

    return PropertyDetailResponse(
        guid=str(p.guid),
        title=p.title,
        description=description,
        city=p.city,
        country=p.country,
        latitude=p.latitude,
        longitude=p.longitude,
        guests=p.guests,
        bedrooms=p.bedrooms,
        beds=p.beds,
        bathrooms=p.bathrooms,
        check_in_time=p.check_in_time,
        check_out_time=p.check_out_time,
        is_allowed_alcohol=p.is_allowed_alcohol,
        is_allowed_pets=p.is_allowed_pets,
        is_allowed_corporate=p.is_allowed_corporate,
        is_quiet_hours=p.is_quiet_hours,
        apartment_number=p.apartment_number,
        home_number=p.home_number,
        entrance_number=p.entrance_number,
        floor_number=p.floor_number,
        pass_code=p.pass_code,
        images=[
            {"guid": str(img.guid), "image_url": img.image_url, "order": img.order}
            for img in imgs
        ],
        prices=[
            {
                "id": pr.id,
                "month_from": pr.month_from,
                "month_to": pr.month_to,
                "price_per_person": pr.price_per_person,
                "price_on_working_days": pr.price_on_working_days,
                "price_on_weekends": pr.price_on_weekends,
            }
            for pr in prices
        ],
        services=[
            {
                "guid": str(sa.service.guid),
                "title": next(
                    (loc.name for loc in (sa.service.localizations or []) if loc.language_code == "ru"),
                    sa.service.localizations[0].name if sa.service.localizations else "",
                ),
                "icon_url": next(
                    (loc.icon_url for loc in (sa.service.localizations or []) if loc.language_code == "ru"),
                    sa.service.localizations[0].icon_url if sa.service.localizations else None,
                ),
            }
            for sa in services
            if sa.service
        ],
    )


@router.get("/types/", response_model=List[PropertyTypeRead])
async def list_property_types(
    db: AsyncSession = Depends(get_db),
):
    service = PropertyApplicationService(db)
    types = await service.list_property_types()
    result = []
    for t in types:
        locs = {loc.language_code: loc.name for loc in (t.localizations or [])}
        name = locs.get("ru") or locs.get("uz") or next(iter(locs.values()), t.slug)
        result.append(PropertyTypeRead(guid=str(t.guid), title=name, slug=t.slug, icon_url=t.icon_url))
    return result


@router.get("/", response_model=List[PropertyListItem])
async def list_properties(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    city: Optional[str] = Query(None),
    property_type_id: Optional[str] = Query(None),
    is_recommended: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = PropertyApplicationService(db)
    props = await service.list_properties(
        skip=skip, limit=limit, city=city, property_type_id=property_type_id, is_recommended=is_recommended
    )
    return [_build_property_list_item(p) for p in props]


@router.get("/{property_id}/", response_model=PropertyDetailResponse)
async def get_property_detail(
    property_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = PropertyApplicationService(db)
    prop = await service.get_property_detail(property_id)
    return _build_property_detail(prop)


@router.post("/partner/create/")
async def create_property(
    data: PropertyCreateRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    service = PropertyApplicationService(db)
    prop = await service.create_property(str(current_user.guid), data.model_dump())
    return {"guid": str(prop.guid), "status": "created"}
