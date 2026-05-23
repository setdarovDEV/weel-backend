from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from app.database import get_db
from app.dependencies import get_current_user, get_current_partner, get_current_client
from app.models.user import User
from app.models.property import Property
from app.models.story import Story, StoryView
from app.models.review import Review
from app.schemas.story import StoryResponse, StoryCreateRequest, ReviewCreateRequest, ReviewResponse
from datetime import datetime, timezone, timedelta

router = APIRouter()

MEDIA_BASE_URL = "https://media.weel.uz/weel-media/"


def resolve_media_url(url: str) -> str:
    if url and url.startswith("http"):
        return url
    if url:
        return f"{MEDIA_BASE_URL}{url}"
    return ""


# ==================== STORIES ====================

@router.get("/stories/", response_model=List[StoryResponse])
async def get_stories(
    filter: Optional[str] = None,
    property_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    query = select(Story).where(
        and_(
            Story.is_verified == True,
            Story.expires_at > now,
        )
    ).options(
        selectinload(Story.views),
        selectinload(Story.property),
    )
    if filter == "week":
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        query = query.where(Story.created_at >= week_ago)
    if property_type:
        query = query.join(Property).where(Property.property_type_id == property_type)

    query = query.order_by(Story.created_at.desc())
    result = await db.execute(query)
    stories = result.scalars().all()

    return [
        StoryResponse(
            guid=s.guid,
            property_id=s.property_id,
            media_url=resolve_media_url(s.media_url),
            media_type=s.media_type,
            views=len(s.views),
            created_at=s.created_at,
        )
        for s in stories
    ]


@router.get("/public/stories/", response_model=List[StoryResponse])
async def get_public_stories(
    filter: Optional[str] = None,
    property_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    return await get_stories(filter=filter, property_type=property_type, current_user=None, db=db)


@router.post("/stories/")
async def create_story(
    property_id: str,
    media_file: UploadFile = File(...),
    media_type: str = "image",
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    prop_result = await db.execute(
        select(Property).where(
            and_(Property.guid == property_id, Property.partner_id == current_user.guid)
        )
    )
    if not prop_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Property not found")

    # TODO: Upload to MinIO
    media_url = f"https://dev.weel.uz/media/{media_file.filename}"
    story = Story(
        property_id=property_id,
        partner_id=current_user.guid,
        media_url=media_url,
        media_type=media_type,
    )
    db.add(story)
    await db.commit()

    return {"detail": "Story created", "guid": story.guid}


@router.delete("/stories/{story_id}/")
async def delete_story(
    story_id: str,
    current_user: User = Depends(get_current_partner),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Story).where(and_(Story.guid == story_id, Story.partner_id == current_user.guid))
    )
    story = result.scalar_one_or_none()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")

    await db.delete(story)
    await db.commit()
    return {"detail": "Story deleted"}


@router.get("/stories/{story_id}/")
async def track_story_view(
    story_id: str,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StoryView).where(
            and_(StoryView.story_id == story_id, StoryView.user_id == current_user.guid)
        )
    )
    if not result.scalar_one_or_none():
        db.add(StoryView(story_id=story_id, user_id=current_user.guid))
        await db.commit()
    return {"detail": "View tracked"}


# ==================== REVIEWS ====================

@router.get("/properties/{property_id}/reviews/", response_model=List[ReviewResponse])
async def get_property_reviews(
    property_id: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Review).where(Review.property_id == property_id)
        .order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()

    return [
        ReviewResponse(
            guid=r.guid,
            user_name="Anonymous",
            rating=r.rating,
            comment=r.comment,
            created_at=r.created_at,
            reply_comment=r.reply_comment,
            reply_created_at=r.reply_created_at,
        )
        for r in reviews
    ]


@router.post("/properties/{property_id}/reviews/")
async def create_review(
    property_id: str,
    data: ReviewCreateRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    review = Review(
        property_id=property_id,
        client_id=current_user.guid,
        rating=data.rating,
        comment=data.comment,
    )
    db.add(review)
    await db.commit()
    return {"detail": "Review created"}
