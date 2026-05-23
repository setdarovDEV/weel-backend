from typing import List
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.database import get_db
from app.dependencies import get_current_client
from app.models.user import User
from app.models.payment import Card, CardVerificationSession
from app.schemas.payment import CardResponse, AddCardRequest, AddCardResponse, VerifyCardRequest, ResendCardOtpRequest
from app.utils.enums import CardType

router = APIRouter()


@router.get("/cards/", response_model=List[CardResponse])
async def list_cards(
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Card).where(Card.client_id == current_user.guid)
    )
    cards = result.scalars().all()
    return [
        CardResponse(
            id=str(c.guid),
            guid=str(c.guid),
            card_number=c.card_number_masked,
            expiry_date=c.expiry_date,
            card_holder=c.card_holder,
            type=c.type,
        )
        for c in cards
    ]


@router.post("/cards/", response_model=AddCardResponse)
async def add_card(
    data: AddCardRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    # Create card record
    card = Card(
        client_id=current_user.guid,
        card_number_masked=f"****{data.card_number[-4:]}",
        expiry_date=data.expiry_date,
        card_holder=data.card_holder,
        type=CardType.UZCARD.value if data.card_number.startswith("8600") else CardType.HUMO.value,
        plum_token="pending",
    )
    db.add(card)
    await db.flush()

    # Create verification session
    session = CardVerificationSession(
        card_id=card.guid,
        otp_code="1234",  # TODO: Generate real OTP
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=2),
    )
    db.add(session)
    await db.commit()

    return AddCardResponse(session=str(session.session_id))


@router.post("/cards/verify/")
async def verify_card(
    data: VerifyCardRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CardVerificationSession).where(
            and_(
                CardVerificationSession.session_id == data.session_id,
                CardVerificationSession.otp_code == data.otp_code,
                CardVerificationSession.expires_at > datetime.now(timezone.utc),
            )
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    session.verified_at = datetime.now(timezone.utc)
    session.card.is_verified = True
    session.card.plum_token = "verified_token"

    await db.commit()
    return {"detail": "Card verified"}


@router.post("/cards/resend/")
async def resend_card_otp(
    data: ResendCardOtpRequest,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CardVerificationSession).where(CardVerificationSession.session_id == data.session_id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.otp_code = "1234"  # TODO: Generate new OTP
    session.expires_at = datetime.now(timezone.utc) + timedelta(minutes=2)
    await db.commit()
    return {"detail": "OTP resent"}


@router.delete("/cards/{card_id}/")
async def delete_card(
    card_id: str,
    current_user: User = Depends(get_current_client),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Card).where(and_(Card.guid == card_id, Card.client_id == current_user.guid))
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")

    await db.delete(card)
    await db.commit()
    return {"detail": "Card deleted"}
