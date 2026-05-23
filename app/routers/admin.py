from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, String
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone, timedelta
from uuid import UUID
from app.database import get_db
from app.dependencies import get_current_user, get_current_admin
from app.models.user import User
from app.models.property import Apartment, Cottage, Service
from app.models.location import Region, District, Prefecture
from app.models.booking import Booking
from app.models.story import Stories as Story
from app.schemas.admin import (
    AdminLoginRequest, AdminAuthResponse, UserListItem,
    AdminPropertyUpdate, StoryModerateRequest, DashboardStats,
)
from app.config import settings
from app.utils.security import decode_token
from app.services.auth_service import AuthService
from app.utils.enums import VerificationStatus
from app.schemas.auth import TokenRefreshRequest, TokenResponse

MEDIA_BASE_URL = "https://media.weel.uz/weel-media/"


def resolve_media_url(url: str) -> str:
    if url and url.startswith("http"):
        return url
    if url:
        return f"{MEDIA_BASE_URL}{url}"
    return ""

router = APIRouter()


# ==================== ADMIN AUTH ====================

@router.post("/login/", response_model=AdminAuthResponse)
async def admin_login(data: AdminLoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email, User.role == 'admin'))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if data.password != settings.admin_default_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access, refresh = await AuthService.generate_token_pair(user.id)
    await AuthService.store_refresh_token(db, refresh, user.id)
    await db.commit()

    return AdminAuthResponse(
        access=access,
        refresh=refresh,
        user={
            "id": user.id,
            "phone": user.phone_number,
            "email": user.email,
            "is_staff": True,
            "is_superuser": True,
        },
    )


@router.post("/token/refresh/", response_model=TokenResponse)
async def admin_refresh_token(data: TokenRefreshRequest, db: AsyncSession = Depends(get_db)):
    if not data.refresh or not await AuthService.is_refresh_token_valid(db, data.refresh):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    payload = decode_token(data.refresh)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = int(payload.get("sub"))
    await AuthService.revoke_refresh_token(db, data.refresh)
    access, new_refresh = await AuthService.generate_token_pair(user_id)
    await AuthService.store_refresh_token(db, new_refresh, user_id)
    await db.commit()

    return TokenResponse(access=access, refresh=new_refresh)


@router.get("/me/")
async def admin_me(current_user: User = Depends(get_current_admin), db: AsyncSession = Depends(get_db)):
    return {
        "id": current_user.id,
        "phone": current_user.phone_number,
        "email": current_user.email,
        "is_staff": current_user.role == 'admin',
        "is_superuser": current_user.role == 'admin',
    }


# ==================== USERS ====================

@router.get("/users/partners/")
async def list_partners(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total = await db.execute(select(func.count()).select_from(User).where(User.role == 'partner'))
    total_count = total.scalar() or 0
    result = await db.execute(
        select(User).where(User.role == 'partner')
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for user in result.scalars().all():
        items.append(UserListItem(
            guid=user.id,
            phone_number=user.phone_number,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
        ))
    base_url = "/api/v2/admin-auth/users/partners/"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page * page_size < total_count else None
    previous_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None
    return {"count": total_count, "next": next_url, "previous": previous_url, "results": items}


@router.get("/users/clients/")
async def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total = await db.execute(select(func.count()).select_from(User).where(User.role == 'client'))
    total_count = total.scalar() or 0
    result = await db.execute(
        select(User).where(User.role == 'client')
        .offset((page - 1) * page_size).limit(page_size)
    )
    items = []
    for user in result.scalars().all():
        items.append(UserListItem(
            guid=user.id,
            phone_number=user.phone_number,
            first_name=user.first_name,
            last_name=user.last_name,
            created_at=user.created_at,
        ))
    base_url = "/api/v2/admin-auth/users/clients/"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page * page_size < total_count else None
    previous_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None
    return {"count": total_count, "next": next_url, "previous": previous_url, "results": items}


# ==================== BOOKINGS ====================

@router.get("/bookings/")
async def list_admin_bookings(
    status: Optional[str] = None,
    region: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    overdue: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Booking)
    if status:
        query = query.where(Booking.status == status)
    if date_from:
        query = query.where(Booking.check_in >= date_from)
    if date_to:
        query = query.where(Booking.check_out <= date_to)

    query = query.order_by(Booking.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    bookings = result.scalars().all()
    return bookings


# ==================== PROPERTIES ====================

@router.get("/properties/all/")
async def list_admin_properties(
    property_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if property_type == 'cottage':
        query = select(Cottage)
        if search:
            query = query.where(Cottage.title.ilike(f"%{search}%"))
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all()
    else:
        query = select(Apartment)
        if search:
            query = query.where(Apartment.title.ilike(f"%{search}%"))
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        return result.scalars().all()


# ==================== STORIES ====================

@router.get("/stories/")
async def list_admin_stories(
    is_verified: Optional[bool] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Story)
    if is_verified is not None:
        query = query.where(Story.is_verified == is_verified)
    query = query.order_by(Story.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.patch("/stories/{story_id}/moderate/")
async def moderate_story(
    story_id: str,
    data: StoryModerateRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Story).where(Story.guid == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    story.is_verified = data.is_verified
    await db.commit()
    return {"detail": "Story moderated"}


@router.delete("/stories/{story_id}/delete/")
async def delete_admin_story(
    story_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Story).where(Story.guid == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    await db.delete(story)
    await db.commit()
    return {"detail": "Story deleted"}


# ==================== DASHBOARD ====================

@router.get("/dashboard/stats/", response_model=DashboardStats)
async def dashboard_stats(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = await db.execute(select(func.count()).select_from(User))
    total_partners = await db.execute(select(func.count()).select_from(User).where(User.role == 'partner'))
    total_apartments = await db.execute(select(func.count()).select_from(Apartment))
    total_cottages = await db.execute(select(func.count()).select_from(Cottage))
    total_properties = total_apartments.scalar() + total_cottages.scalar()
    total_bookings = await db.execute(select(func.count()).select_from(Booking))
    pending_apartments = await db.execute(
        select(func.count()).select_from(Apartment).where(Apartment.verification_status == VerificationStatus.WAITING.value)
    )
    pending_cottages = await db.execute(
        select(func.count()).select_from(Cottage).where(Cottage.verification_status == VerificationStatus.WAITING.value)
    )
    pending_verifications = pending_apartments.scalar() + pending_cottages.scalar()

    return DashboardStats(
        total_users=total_users.scalar(),
        total_partners=total_partners.scalar(),
        total_properties=total_properties,
        total_bookings=total_bookings.scalar(),
        pending_verifications=pending_verifications,
    )


# ==================== LEGACY COMPATIBILITY ROUTERS ====================
# These match the old URL patterns the frontend still uses

property_admin_router = APIRouter()


@property_admin_router.get("/all/")
async def legacy_properties_all(
    property_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=1000),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    if property_type == 'cottage':
        query = select(Cottage).order_by(Cottage.created_at.desc())
        if search:
            query = query.where(Cottage.title.ilike(f"%{search}%"))
        result = await db.execute(query)
        items = result.scalars().all()
        return [{
            "id": item.id,
            "guid": str(item.guid),
            "title": item.title,
            "title_sort": item.title_sort,
            "img": [resolve_media_url(u) for u in (item.img or [])],
            "city": item.city,
            "country": item.country,
            "is_verified": item.is_verified,
            "is_archived": item.is_archived,
            "is_recommended": item.is_recommended,
            "verification_status": item.verification_status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "price_per_person": str(item.price_per_person) if item.price_per_person else None,
            "price_on_working_days": str(item.price_on_working_days) if item.price_on_working_days else None,
            "price_on_weekends": str(item.price_on_weekends) if item.price_on_weekends else None,
            "currency": item.currency,
            "guests": item.guests,
            "rooms": item.rooms,
            "beds": item.beds,
            "bathrooms": item.bathrooms,
            "latitude": str(item.latitude) if item.latitude else None,
            "longitude": str(item.longitude) if item.longitude else None,
            "region_id": item.region_id,
            "property_type": "cottage",
        } for item in items]
    else:
        query = select(Apartment).order_by(Apartment.created_at.desc())
        if search:
            query = query.where(Apartment.title.ilike(f"%{search}%"))
        result = await db.execute(query)
        items = result.scalars().all()
        return [{
            "id": item.id,
            "guid": str(item.guid),
            "title": item.title,
            "title_sort": item.title_sort,
            "img": [resolve_media_url(u) for u in (item.img or [])],
            "city": item.city,
            "country": item.country,
            "is_verified": item.is_verified,
            "is_archived": item.is_archived,
            "is_recommended": item.is_recommended,
            "verification_status": item.verification_status,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "price": str(item.price) if item.price else None,
            "currency": item.currency,
            "guests": item.guests,
            "rooms": item.rooms,
            "beds": item.beds,
            "bathrooms": item.bathrooms,
            "latitude": str(item.latitude) if item.latitude else None,
            "longitude": str(item.longitude) if item.longitude else None,
            "region_id": item.region_id,
            "property_type": "apartment",
        } for item in items]


booking_admin_router = APIRouter()


@booking_admin_router.get("/bookings/")
async def legacy_bookings_list(
    status: Optional[str] = None,
    region: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    search: Optional[str] = None,
    overdue: Optional[bool] = None,
    ordering: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status:
        filters.append(Booking.status == status)
    if date_from:
        filters.append(Booking.check_in >= date_from)
    if date_to:
        filters.append(Booking.check_out <= date_to)

    base_query = select(Booking)
    if filters:
        base_query = base_query.where(and_(*filters))

    count_query = select(func.count()).select_from(Booking)
    if filters:
        count_query = count_query.where(and_(*filters))

    if search:
        search_filter = or_(
            Booking.booking_number.ilike(f"%{search}%"),
            Booking.client_user_id == (int(search) if search.isdigit() else -1),
        )
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = await db.execute(count_query)
    total_count = total.scalar() or 0

    order_col = Booking.created_at.desc()
    if ordering == "check_in":
        order_col = Booking.check_in.asc()
    elif ordering == "-check_in":
        order_col = Booking.check_in.desc()

    query = base_query.order_by(order_col).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    rows = result.scalars().all()

    # Fetch related client and property data
    client_ids = set()
    cottage_ids = set()
    apartment_ids = set()
    for b in rows:
        if b.client_user_id:
            client_ids.add(b.client_user_id)
        if b.property_cottage_id:
            cottage_ids.add(b.property_cottage_id)
        if b.property_apartment_id:
            apartment_ids.add(b.property_apartment_id)

    # Batch fetch clients
    client_map = {}
    if client_ids:
        c_result = await db.execute(
            select(User).where(User.id.in_(list(client_ids)))
        )
        for u in c_result.scalars().all():
            client_map[u.id] = u

    # Batch fetch cottages
    cottage_map = {}
    if cottage_ids:
        co_result = await db.execute(
            select(Cottage).where(Cottage.id.in_(list(cottage_ids)))
        )
        for c in co_result.scalars().all():
            cottage_map[c.id] = c

    # Batch fetch apartments
    apartment_map = {}
    if apartment_ids:
        ap_result = await db.execute(
            select(Apartment).where(Apartment.id.in_(list(apartment_ids)))
        )
        for a in ap_result.scalars().all():
            apartment_map[a.id] = a

    items = []
    for b in rows:
        client = client_map.get(b.client_user_id)
        cottage = cottage_map.get(b.property_cottage_id) if b.property_cottage_id else None
        apartment = apartment_map.get(b.property_apartment_id) if b.property_apartment_id else None
        prop = cottage or apartment
        prop_type = "cottage" if cottage else "apartment" if apartment else None

        items.append({
            "guid": str(b.guid) if b.guid else None,
            "booking_number": b.booking_number,
            "check_in": str(b.check_in) if b.check_in else None,
            "check_out": str(b.check_out) if b.check_out else None,
            "adults": b.adults,
            "children": b.children,
            "babies": b.babies,
            "status": b.status,
            "cancellation_reason": b.cancellation_reason,
            "confirmed_at": b.confirmed_at.isoformat() if b.confirmed_at else None,
            "cancelled_at": b.cancelled_at.isoformat() if b.cancelled_at else None,
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "client": {
                "id": client.id if client else None,
                "first_name": client.first_name if client else None,
                "last_name": client.last_name if client else None,
                "phone_number": client.phone_number if client else None,
            },
            "property": {
                "guid": str(prop.guid) if prop else None,
                "title": prop.title if prop else None,
                "property_type": prop_type,
            },
            "booking_price": None,
        })

    base_url = "/api/v2/booking/admin/bookings/"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page * page_size < total_count else None
    previous_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None

    # Queue counts for tabs
    queue_counts = {}
    for s in ("pending", "confirmed", "checked_in", "cancelled", "completed", "no_show"):
        q_result = await db.execute(
            select(func.count()).select_from(Booking).where(Booking.status == s)
        )
        queue_counts[s] = q_result.scalar() or 0

    return {"count": total_count, "next": next_url, "previous": previous_url, "results": items, "queue_counts": queue_counts}


story_admin_router = APIRouter()


@story_admin_router.get("/stories/")
async def legacy_stories_list(
    is_verified: Optional[bool] = None,
    search: Optional[str] = None,
    ordering: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if is_verified is not None:
        filters.append(Story.is_verified == is_verified)

    base_query = select(Story)
    if filters:
        base_query = base_query.where(and_(*filters))

    count_query = select(func.count()).select_from(Story)
    if filters:
        count_query = count_query.where(and_(*filters))

    if search:
        search_filter = or_(
            func.cast(Story.guid, String).ilike(f"%{search}%"),
        )
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = await db.execute(count_query)
    total_count = total.scalar() or 0

    order_col = Story.created_at.desc()
    if ordering == "created_at":
        order_col = Story.created_at.asc()
    elif ordering == "-expires_at":
        order_col = Story.expires_at.desc()
    elif ordering == "-views":
        order_col = Story.views.desc()

    query = (
        base_query
        .options(selectinload(Story.medias))
        .order_by(order_col)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.scalars().all()

    # Batch fetch related properties and users
    cottage_ids = set()
    apartment_ids = set()
    user_ids = set()
    for s in rows:
        if s.property_cottage_id:
            cottage_ids.add(s.property_cottage_id)
        if s.property_apartment_id:
            apartment_ids.add(s.property_apartment_id)
        if s.verified_by_user_id:
            user_ids.add(s.verified_by_user_id)

    # Batch fetch cottages
    cottage_map = {}
    if cottage_ids:
        co_result = await db.execute(
            select(Cottage).where(Cottage.id.in_(list(cottage_ids)))
        )
        for c in co_result.scalars().all():
            cottage_map[c.id] = c

    # Batch fetch apartments
    apartment_map = {}
    if apartment_ids:
        ap_result = await db.execute(
            select(Apartment).where(Apartment.id.in_(list(apartment_ids)))
        )
        for a in ap_result.scalars().all():
            apartment_map[a.id] = a

    # Batch fetch users
    user_map = {}
    if user_ids:
        u_result = await db.execute(
            select(User).where(User.id.in_(list(user_ids)))
        )
        for u in u_result.scalars().all():
            user_map[u.id] = u

    items = []
    for s in rows:
        cottage = cottage_map.get(s.property_cottage_id) if s.property_cottage_id else None
        apartment = apartment_map.get(s.property_apartment_id) if s.property_apartment_id else None
        prop = cottage or apartment
        kind = "cottage" if cottage else "apartment" if apartment else None

        items.append({
            "guid": str(s.guid),
            "property_id": str(prop.guid) if prop else None,
            "property_title": prop.title if prop else None,
            "property_kind": kind,
            "property_img": resolve_media_url(prop.img[0]) if prop and prop.img else None,
            "partner_user_id": prop.partner_user_id if prop else None,
            "is_verified": bool(s.is_verified) if s.is_verified is not None else False,
            "verified_by_user_id": s.verified_by_user_id,
            "verified_at": s.verified_at.isoformat() if s.verified_at else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "uploaded_at": s.uploaded_at.isoformat() if s.uploaded_at else None,
            "views": s.views or 0,
            "media": [
                {
                    "guid": str(m.guid),
                    "media_type": m.media_type,
                    "media_url": resolve_media_url(m.media),
                }
                for m in (s.medias or [])
            ],
        })

    base_url = "/api/v2/story/admin/stories/"
    next_url = f"{base_url}?page={page + 1}&page_size={page_size}" if page * page_size < total_count else None
    previous_url = f"{base_url}?page={page - 1}&page_size={page_size}" if page > 1 else None

    return {"count": total_count, "next": next_url, "previous": previous_url, "results": items}


@story_admin_router.patch("/stories/{story_id}/moderate/")
async def legacy_story_moderate(
    story_id: str,
    data: StoryModerateRequest,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Story).where(Story.guid == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    story.is_verified = data.is_verified
    await db.commit()
    return {"detail": "Story moderated"}


@story_admin_router.delete("/stories/{story_id}/delete/")
async def legacy_story_delete(
    story_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Story).where(Story.guid == story_id))
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    await db.delete(story)
    await db.commit()
    return {"detail": "Story deleted"}


@property_admin_router.get("/regions/")
async def legacy_regions(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Region))
    return [{"id": r.id, "guid": str(r.guid), "name": r.title_uz or r.title_en} for r in result.scalars().all()]


@property_admin_router.get("/districts/")
async def legacy_districts(
    region_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(District)
    if region_id:
        query = query.where(District.region_id == region_id)
    result = await db.execute(query)
    return [{"id": d.id, "guid": str(d.guid), "name": d.title_uz or d.title_en, "region_id": d.region_id} for d in result.scalars().all()]


@property_admin_router.get("/prefectures/")
async def legacy_prefectures(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Prefecture))
    return [{"id": str(p.id), "name": p.name, "ru_name": p.ru_name} for p in result.scalars().all()]


@property_admin_router.get("/cottages/{cottage_id}/")
async def legacy_cottage_detail(
    cottage_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Cottage).where(Cottage.guid == cottage_id))
    cottage = result.scalar_one_or_none()
    if not cottage:
        raise HTTPException(status_code=404, detail="Cottage not found")
    return {
        "id": cottage.id,
        "guid": str(cottage.guid),
        "title": cottage.title,
        "img": [resolve_media_url(u) for u in (cottage.img or [])],
        "city": cottage.city,
        "country": cottage.country,
        "is_verified": cottage.is_verified,
        "is_archived": cottage.is_archived,
        "is_recommended": cottage.is_recommended,
        "verification_status": cottage.verification_status,
        "description_en": cottage.description_en,
        "description_ru": cottage.description_ru,
        "description_uz": cottage.description_uz,
        "check_in": str(cottage.check_in) if cottage.check_in else None,
        "check_out": str(cottage.check_out) if cottage.check_out else None,
        "latitude": str(cottage.latitude) if cottage.latitude else None,
        "longitude": str(cottage.longitude) if cottage.longitude else None,
        "guests": cottage.guests,
        "rooms": cottage.rooms,
        "beds": cottage.beds,
        "bathrooms": cottage.bathrooms,
        "price_per_person": str(cottage.price_per_person) if cottage.price_per_person else None,
        "price_on_working_days": str(cottage.price_on_working_days) if cottage.price_on_working_days else None,
        "price_on_weekends": str(cottage.price_on_weekends) if cottage.price_on_weekends else None,
        "currency": cottage.currency,
        "region_id": cottage.region_id,
        "district_id": cottage.district_id,
        "partner_user_id": cottage.partner_user_id,
        "is_allowed_alcohol": cottage.is_allowed_alcohol,
        "is_allowed_corporate": cottage.is_allowed_corporate,
        "is_allowed_pets": cottage.is_allowed_pets,
        "is_quiet_hours": cottage.is_quiet_hours,
        "prices": [{"id": p.id, "guid": str(p.guid), "month_from": str(p.month_from), "month_to": str(p.month_to), "price_per_person": str(p.price_per_person) if p.price_per_person else None, "price_on_working_days": str(p.price_on_working_days), "price_on_weekends": str(p.price_on_weekends)} for p in (cottage.prices or [])],
    }


@property_admin_router.get("/apartments/{apartment_id}/")
async def legacy_apartment_detail(
    apartment_id: str,
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Apartment).where(Apartment.guid == apartment_id))
    apartment = result.scalar_one_or_none()
    if not apartment:
        raise HTTPException(status_code=404, detail="Apartment not found")
    return {
        "id": apartment.id,
        "guid": str(apartment.guid),
        "title": apartment.title,
        "img": [resolve_media_url(u) for u in (apartment.img or [])],
        "city": apartment.city,
        "country": apartment.country,
        "is_verified": apartment.is_verified,
        "is_archived": apartment.is_archived,
        "is_recommended": apartment.is_recommended,
        "verification_status": apartment.verification_status,
        "description_en": apartment.description_en,
        "description_ru": apartment.description_ru,
        "description_uz": apartment.description_uz,
        "check_in": str(apartment.check_in) if apartment.check_in else None,
        "check_out": str(apartment.check_out) if apartment.check_out else None,
        "latitude": str(apartment.latitude) if apartment.latitude else None,
        "longitude": str(apartment.longitude) if apartment.longitude else None,
        "guests": apartment.guests,
        "rooms": apartment.rooms,
        "beds": apartment.beds,
        "bathrooms": apartment.bathrooms,
        "price": str(apartment.price) if apartment.price else None,
        "currency": apartment.currency,
        "region_id": apartment.region_id,
        "district_id": apartment.district_id,
        "partner_user_id": apartment.partner_user_id,
        "is_allowed_alcohol": apartment.is_allowed_alcohol,
        "is_allowed_corporate": apartment.is_allowed_corporate,
        "is_allowed_pets": apartment.is_allowed_pets,
        "is_quiet_hours": apartment.is_quiet_hours,
        "floor_number": apartment.floor_number,
        "apartment_number": apartment.apartment_number,
        "home_number": apartment.home_number,
        "entrance_number": apartment.entrance_number,
        "pass_code": apartment.pass_code,
    }


services_router = APIRouter()


@services_router.get("/")
async def legacy_services(
    current_user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service))
    return [{"id": str(s.id), "title": s.title, "icon_url": s.icon_url, "type": s.type} for s in result.scalars().all()]
