from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.dependencies import get_current_user, get_current_partner
from app.models.user import User
from app.models.location import Location
from app.models.property import (
    PropertyType, PropertyService, Property,
    PropertyImage, PropertyServiceLink,
    PropertyPrice,
)
from app.schemas.property import (
    PropertyTypeResponse, PropertyServiceResponse,
    RegionResponse, DistrictResponse, PrefectureResponse,
    PropertyListItem, PropertyDetailResponse,
    CottageCreateRequest, ApartmentCreateRequest,
    CottageUpdateRequest, ApartmentUpdateRequest,
    PropertyImageResponse, PropertyListResponse,
    PropertyLocationResponse, PropertyRoomBase,
)
from app.utils.enums import VerificationStatus
from uuid import UUID

router = APIRouter()

MEDIA_BASE_URL = "https://media.weel.uz/weel-media/"


def resolve_media_url(url: str) -> str:
    if url and url.startswith("http"):
        return url
    if url:
        return f"{MEDIA_BASE_URL}{url}"
    return ""


def _build_location_response(p: Property):
    """Build PropertyLocationResponse from merged Property fields."""
    loc = p.location_ref
    region = district = prefecture = None
    if loc:
        if loc.type == 'prefecture':
            prefecture = loc
            district = loc.parent
            region = district.parent if district else None
        elif loc.type == 'district':
            district = loc
            region = loc.parent
        elif loc.type == 'region':
            region = loc
    return PropertyLocationResponse(
        latitude=p.latitude,
        longitude=p.longitude,
        country=p.country,
        city=p.city,
        region_id=region.id if region else None,
        district_id=district.id if district else None,
        prefecture_id=prefecture.id if prefecture else None,
        region=RegionResponse(id=region.id, guid=region.guid, title=region.title, img_url=region.img_url) if region else None,
        district=DistrictResponse(id=district.id, guid=district.guid, title=district.title, region_id=region.id if region else None) if district else None,
        prefecture=PrefectureResponse(id=prefecture.id, guid=prefecture.guid, title=prefecture.title) if prefecture else None,
    ) if (p.latitude or p.city) else None


# ==================== PROPERTY TYPES ====================

@router.get("/types/", response_model=List[PropertyTypeResponse])
async def get_property_types(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PropertyType))
    types = result.scalars().all()
    def sort_key(t):
        if t.slug == "dachas":
            return 0
        if t.slug == "apartments":
            return 1
        return 2
    return sorted(types, key=sort_key)


# ==================== SERVICES ====================

@router.get("/services/", response_model=List[PropertyServiceResponse])
async def get_services(
    property_type_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(PropertyService)
    if property_type_id:
        query = query.where(PropertyService.property_type_id == property_type_id)
    result = await db.execute(query)
    return result.scalars().all()


# ==================== LOCATIONS ====================

@router.get("/regions/", response_model=List[RegionResponse])
async def get_regions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Location).where(Location.type == 'region'))
    regions = result.scalars().all()
    return [RegionResponse(id=r.id, guid=r.guid, title=r.title, img_url=r.img_url) for r in regions]


@router.get("/districts/", response_model=List[DistrictResponse])
async def get_districts(
    region_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Location).where(Location.type == 'district')
    if region_id:
        query = query.where(Location.parent_id == region_id)
    result = await db.execute(query)
    districts = result.scalars().all()
    return [
        DistrictResponse(
            id=d.id, guid=d.guid, title=d.title,
            region_id=d.parent_id,
        ) for d in districts
    ]


@router.get("/prefectures/", response_model=List[PrefectureResponse])
async def get_prefectures(
    district_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(Location).where(Location.type == 'prefecture')
    if district_id:
        query = query.where(Location.parent_id == district_id)
    result = await db.execute(query)
    prefectures = result.scalars().all()
    return [
        PrefectureResponse(id=p.id, guid=p.guid, title=p.title)
        for p in prefectures
    ]


# ==================== PROPERTY LIST ====================

@router.get("/properties/", response_model=PropertyListResponse)
async def list_properties(
    property_type: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    currency: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    search: Optional[str] = None,
    adults: Optional[int] = None,
    children: Optional[int] = None,
    pets: Optional[bool] = None,
    property_services: Optional[List[str]] = Query(None),
    ordering: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    query = select(Property).where(
        and_(
            Property.verification_status == VerificationStatus.VERIFIED.value,
            Property.is_archived == False,
        )
    ).options(
        selectinload(Property.location_ref),
        selectinload(Property.images),
        selectinload(Property.prices),
        selectinload(Property.property_type),
    )

    if property_type:
        query = query.join(PropertyType).where(PropertyType.slug == property_type)
    if search:
        query = query.where(Property.title.ilike(f"%{search}%"))
    if currency:
        query = query.where(Property.currency == currency)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = count_result.scalar()

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    properties = result.scalars().all()

    items = []
    for p in properties:
        price = None
        if p.prices:
            price_vals = [pr.price_on_working_days for pr in p.prices if pr.price_on_working_days > 0]
            if price_vals:
                price = min(price_vals)

        items.append(PropertyListItem(
            guid=p.guid,
            title=p.title,
            location=_build_location_response(p),
            images=[PropertyImageResponse(guid=img.guid, image_url=resolve_media_url(img.image_url), order=img.order) for img in p.images],
            average_rating=None,
            comment_count=0,
            property_type_guid=p.property_type_id,
            property_type_name=p.property_type.title if p.property_type else None,
            price=price,
            currency=p.currency,
        ))

    next_url = None
    if offset + limit < total_count:
        next_url = f"?offset={offset + limit}&limit={limit}"
    prev_url = None
    if offset > 0:
        prev_url = f"?offset={max(0, offset - limit)}&limit={limit}"

    return PropertyListResponse(count=total_count, next=next_url, previous=prev_url, results=items)


# ==================== PROPERTY DETAIL ====================

@router.get("/properties/{guid}/", response_model=PropertyDetailResponse)
async def get_property_detail(guid: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Property).where(Property.guid == guid).options(
            selectinload(Property.location_ref),
            selectinload(Property.images),
            selectinload(Property.prices),
            selectinload(Property.service_links).selectinload(PropertyServiceLink.service),
            selectinload(Property.property_type),
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    services = []
    for link in prop.service_links:
        if link.service:
            services.append(PropertyServiceResponse(guid=str(link.service.guid), title=link.service.title, icon_url=link.service.icon_url))

    return PropertyDetailResponse(
        guid=prop.guid,
        title=prop.title,
        location=_build_location_response(prop),
        images=[PropertyImageResponse(guid=img.guid, image_url=resolve_media_url(img.image_url), order=img.order) for img in prop.images],
        average_rating=None,
        comment_count=0,
        description=prop.description,
        services=services,
        room=PropertyRoomBase(guests=prop.guests, bedrooms=prop.bedrooms, beds=prop.beds, bathrooms=prop.bathrooms),
        is_allowed_alcohol=prop.is_allowed_alcohol,
        is_allowed_pets=prop.is_allowed_pets,
        is_allowed_corporate=prop.is_allowed_corporate,
        is_quiet_hours=prop.is_quiet_hours,
        check_in_time=prop.check_in_time,
        check_out_time=prop.check_out_time,
        property_type_guid=prop.property_type_id,
        property_type_name=prop.property_type.title if prop.property_type else None,
        price=None,
        currency=prop.currency,
    )


# ==================== PARTNER PROPERTIES ====================

@router.get("/partner/properties/", response_model=List[PropertyListItem])
async def get_partner_properties(
    property_type: Optional[str] = None,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    query = select(Property).where(Property.partner_id == current_user.guid).options(
        selectinload(Property.location_ref),
        selectinload(Property.images),
        selectinload(Property.prices),
        selectinload(Property.property_type),
    )
    if property_type:
        query = query.join(PropertyType).where(PropertyType.slug == property_type)

    result = await db.execute(query)
    properties = result.scalars().all()

    items = []
    for p in properties:
        items.append(PropertyListItem(
            guid=p.guid,
            title=p.title,
            location=_build_location_response(p),
            images=[PropertyImageResponse(guid=img.guid, image_url=resolve_media_url(img.image_url), order=img.order) for img in p.images],
            average_rating=None,
            comment_count=0,
            property_type_guid=p.property_type_id,
            property_type_name=p.property_type.title if p.property_type else None,
            price=None,
            currency=p.currency,
        ))
    return items


# ==================== CREATE ====================

@router.post("/cottages/", response_model=PropertyListItem)
async def create_cottage(
    data: CottageCreateRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop = Property(
        partner_id=current_user.guid,
        property_type_id=data.property_type_id,
        title=data.title,
        currency=data.currency,
        latitude=data.location.latitude,
        longitude=data.location.longitude,
        country=data.location.country,
        city=data.location.city,
        location_id=data.location.prefecture_id or data.location.district_id or data.location.region_id,
        description=data.detail.description_ru,
        check_in_time=data.detail.check_in_time,
        check_out_time=data.detail.check_out_time,
        is_allowed_alcohol=data.detail.is_allowed_alcohol,
        is_allowed_pets=data.detail.is_allowed_pets,
        is_allowed_corporate=data.detail.is_allowed_corporate,
        is_quiet_hours=data.detail.is_quiet_hours,
        guests=data.room.guests,
        bedrooms=data.room.bedrooms,
        beds=data.room.beds,
        bathrooms=data.room.bathrooms,
    )
    db.add(prop)
    await db.flush()

    for price in data.prices:
        db.add(PropertyPrice(property_id=prop.guid, **price.dict()))
    for svc_id in data.services:
        db.add(PropertyServiceLink(property_id=prop.guid, service_id=svc_id))

    await db.commit()
    await db.refresh(prop)

    return PropertyListItem(
        guid=prop.guid,
        title=prop.title,
        location=_build_location_response(prop),
        images=[],
        property_type_guid=prop.property_type_id,
        currency=prop.currency,
    )


@router.post("/apartments/", response_model=PropertyListItem)
async def create_apartment(
    data: ApartmentCreateRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop = Property(
        partner_id=current_user.guid,
        property_type_id=data.property_type_id,
        title=data.title,
        currency=data.currency,
        latitude=data.location.latitude,
        longitude=data.location.longitude,
        country=data.location.country,
        city=data.location.city,
        location_id=data.location.prefecture_id or data.location.district_id or data.location.region_id,
        description=data.detail.description_ru,
        check_in_time=data.detail.check_in_time,
        check_out_time=data.detail.check_out_time,
        is_allowed_alcohol=data.detail.is_allowed_alcohol,
        is_allowed_pets=data.detail.is_allowed_pets,
        is_allowed_corporate=data.detail.is_allowed_corporate,
        is_quiet_hours=data.detail.is_quiet_hours,
        guests=data.room.guests,
        bedrooms=data.room.bedrooms,
        beds=data.room.beds,
        bathrooms=data.room.bathrooms,
        apartment_number=data.apartment_number,
        home_number=data.home_number,
        entrance_number=data.entrance_number,
        floor_number=data.floor_number,
        pass_code=data.pass_code,
    )
    db.add(prop)
    await db.flush()

    for price in data.prices:
        db.add(PropertyPrice(property_id=prop.guid, **price.dict()))
    for svc_id in data.services:
        db.add(PropertyServiceLink(property_id=prop.guid, service_id=svc_id))

    await db.commit()
    await db.refresh(prop)

    return PropertyListItem(
        guid=prop.guid,
        title=prop.title,
        location=_build_location_response(prop),
        images=[],
        property_type_guid=prop.property_type_id,
        currency=prop.currency,
    )


# ==================== UPDATE / DELETE ====================

@router.patch("/cottages/{property_id}/")
async def update_cottage(
    property_id: str,
    data: CottageUpdateRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if data.title:
        prop.title = data.title
    if data.currency:
        prop.currency = data.currency
    await db.commit()
    return {"detail": "Updated"}


@router.patch("/apartments/{property_id}/")
async def update_apartment(
    property_id: str,
    data: ApartmentUpdateRequest,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    if data.title:
        prop.title = data.title
    if data.currency:
        prop.currency = data.currency
    await db.commit()
    return {"detail": "Updated"}


@router.delete("/cottages/{property_id}/")
async def delete_cottage(
    property_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    await db.delete(prop)
    await db.commit()
    return {"detail": "Deleted"}


@router.delete("/apartments/{property_id}/")
async def delete_apartment(
    property_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    prop = result.scalar_one_or_none()
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    await db.delete(prop)
    await db.commit()
    return {"detail": "Deleted"}


# ==================== IMAGES ====================

@router.post("/cottages/{property_id}/images/")
async def upload_cottage_images(
    property_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    return {"detail": f"Uploaded {len(files)} files"}


@router.post("/apartments/{property_id}/images/")
async def upload_apartment_images(
    property_id: str,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    return {"detail": f"Uploaded {len(files)} files"}


@router.delete("/{kind}/{property_id}/images/{image_id}/")
async def delete_property_image(
    kind: str,
    property_id: str,
    image_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PropertyImage).where(
            and_(PropertyImage.guid == image_id, PropertyImage.property_id == property_id)
        )
    )
    img = result.scalar_one_or_none()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    await db.delete(img)
    await db.commit()
    return {"detail": "Deleted"}


# ==================== RECOMMENDATIONS ====================

@router.get("/recommendations/", response_model=List[PropertyListItem])
async def get_recommendations(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    query = select(Property).where(
        and_(
            Property.verification_status == VerificationStatus.VERIFIED.value,
            Property.is_recommended == True,
        )
    ).options(
        selectinload(Property.location_ref),
        selectinload(Property.images),
        selectinload(Property.prices),
        selectinload(Property.property_type),
    ).limit(limit)

    result = await db.execute(query)
    properties = result.scalars().all()

    items = []
    for p in properties:
        items.append(PropertyListItem(
            guid=p.guid,
            title=p.title,
            location=_build_location_response(p),
            images=[PropertyImageResponse(guid=img.guid, image_url=resolve_media_url(img.image_url), order=img.order) for img in p.images],
            average_rating=None,
            comment_count=0,
            property_type_guid=p.property_type_id,
            property_type_name=p.property_type.title if p.property_type else None,
            price=None,
            currency=p.currency,
        ))
    return items
