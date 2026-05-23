import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
import redis.asyncio as aioredis
from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage
from app.schemas.chat import ChatMessageResponse, ConversationResponse, RecipientResponse, ChatMessageCreate, ActorSchema, MarkReadRequest
from datetime import datetime, timezone

router = APIRouter()


# ==================== REST ENDPOINTS ====================

def _get_conversation_filter(user_id: int):
    return or_(
        ChatConversation.admin_user_id == user_id,
        ChatConversation.partner_user_id == user_id,
        ChatConversation.client_user_id == user_id,
    )


def _get_counterpart_info(conv: ChatConversation, user_id: int):
    if conv.admin_user_id == user_id:
        if conv.client_user_id is not None:
            return conv.client_user_id, "client"
        return conv.partner_user_id, "partner"
    if conv.partner_user_id == user_id:
        return conv.admin_user_id, "admin"
    return conv.admin_user_id, "admin"


@router.get("/conversations/", response_model=List[ConversationResponse])
async def get_conversations(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatConversation)
        .where(_get_conversation_filter(current_user.id))
        .options(selectinload(ChatConversation.messages))
    )
    conversations = result.scalars().all()

    counterpart_ids = set()
    for conv in conversations:
        cid, _ = _get_counterpart_info(conv, current_user.id)
        counterpart_ids.add(cid)

    if counterpart_ids:
        user_result = await db.execute(
            select(User).where(User.id.in_(counterpart_ids))
        )
        user_map = {u.id: u for u in user_result.scalars().all()}
    else:
        user_map = {}

    resp = []
    for conv in conversations:
        counterpart_id, counterpart_type = _get_counterpart_info(conv, current_user.id)
        last_msg = conv.messages[-1] if conv.messages else None
        unread = sum(1 for m in conv.messages if m.receiver_user_id == current_user.id and not m.is_read)

        user = user_map.get(counterpart_id)
        full_name = "Unknown"
        if user:
            if user.first_name or user.last_name:
                full_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
            elif user.username:
                full_name = user.username
            elif user.email:
                full_name = user.email
        actor = ActorSchema(
            id=counterpart_id,
            role=counterpart_type,
            full_name=full_name,
            email=user.email if user else None,
            username=user.username if user else None,
            phone_number=user.phone_number if user else None,
        )

        resp.append(ConversationResponse(
            conversation_id=conv.id,
            counterpart=actor,
            last_message=last_msg.content if last_msg else None,
            unread_count=unread,
            created_at=conv.created_at,
        ))
    return resp


@router.get("/recipient/{role}/")
async def get_recipient(
    role: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return RecipientResponse(id="admin", name="Admin", role="admin")


@router.get("/messages/{partner_id}/")
async def get_messages(
    partner_id: str,
    role: str = Query("partner"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pid = int(partner_id)
    result = await db.execute(
        select(ChatConversation)
        .where(
            or_(
                and_(ChatConversation.admin_user_id == current_user.id, ChatConversation.partner_user_id == pid),
                and_(ChatConversation.admin_user_id == pid, ChatConversation.partner_user_id == current_user.id),
                and_(ChatConversation.admin_user_id == current_user.id, ChatConversation.client_user_id == pid),
                and_(ChatConversation.admin_user_id == pid, ChatConversation.client_user_id == current_user.id),
                and_(ChatConversation.client_user_id == current_user.id, ChatConversation.admin_user_id == pid),
                and_(ChatConversation.client_user_id == pid, ChatConversation.admin_user_id == current_user.id),
            )
        )
        .options(selectinload(ChatConversation.messages))
    )
    conv = result.scalar_one_or_none()
    if not conv:
        return []

    return [
        ChatMessageResponse(
            id=m.id,
            conversation_id=str(conv.id),
            sender_id=str(m.sender_user_id),
            sender_type=m.sender_role,
            receiver_id=str(m.receiver_user_id),
            receiver_type=m.receiver_role,
            content=m.content,
            is_read=m.is_read or False,
            created_at=m.created_at,
        )
        for m in conv.messages
    ]


@router.post("/messages/", response_model=ChatMessageResponse)
async def send_message(
    data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    receiver_id = int(data.receiver_id)
    result = await db.execute(
        select(ChatConversation).where(
            or_(
                and_(ChatConversation.admin_user_id == current_user.id, ChatConversation.partner_user_id == receiver_id),
                and_(ChatConversation.admin_user_id == receiver_id, ChatConversation.partner_user_id == current_user.id),
                and_(ChatConversation.admin_user_id == current_user.id, ChatConversation.client_user_id == receiver_id),
                and_(ChatConversation.admin_user_id == receiver_id, ChatConversation.client_user_id == current_user.id),
                and_(ChatConversation.client_user_id == current_user.id, ChatConversation.admin_user_id == receiver_id),
                and_(ChatConversation.client_user_id == receiver_id, ChatConversation.admin_user_id == current_user.id),
            )
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        receiver_role = data.receiver_type
        if current_user.role == "admin":
            if receiver_role == "client":
                conv = ChatConversation(
                    admin_user_id=current_user.id,
                    partner_user_id=receiver_id,
                    client_user_id=receiver_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            else:
                conv = ChatConversation(
                    admin_user_id=current_user.id,
                    partner_user_id=receiver_id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
        else:
            if current_user.role == "client":
                conv = ChatConversation(
                    admin_user_id=receiver_id,
                    partner_user_id=current_user.id,
                    client_user_id=current_user.id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
            else:
                conv = ChatConversation(
                    admin_user_id=receiver_id,
                    partner_user_id=current_user.id,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                )
        db.add(conv)
        await db.flush()

    msg = ChatMessage(
        conversation_id=conv.id,
        sender_user_id=current_user.id,
        sender_role=current_user.role or "client",
        receiver_user_id=receiver_id,
        receiver_role=data.receiver_type,
        content=data.content,
        is_read=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)

    response = {
        "id": msg.id,
        "sender_id": msg.sender_user_id,
        "sender_type": msg.sender_role,
        "receiver_id": msg.receiver_user_id,
        "receiver_type": msg.receiver_role,
        "content": msg.content,
        "is_read": False,
        "created_at": msg.created_at.isoformat(),
    }

    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.publish("chat:messages", json.dumps({"type": "message", "data": response}, default=str))
        await r.aclose()
    except Exception:
        pass

    return ChatMessageResponse(
        id=msg.id,
        conversation_id=str(conv.id),
        sender_id=str(msg.sender_user_id),
        sender_type=msg.sender_role,
        receiver_id=str(msg.receiver_user_id),
        receiver_type=msg.receiver_role,
        content=msg.content,
        is_read=msg.is_read or False,
        created_at=msg.created_at,
    )


@router.post("/messages/{message_id}/read/")
async def mark_message_read(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ChatMessage).where(ChatMessage.id == message_id))
    msg = result.scalar_one_or_none()
    if msg and msg.receiver_user_id == current_user.id:
        msg.is_read = True
        await db.commit()
    return {"detail": "Marked as read"}


@router.post("/read/")
async def mark_messages_read(
    data: MarkReadRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if data.message_ids:
        await db.execute(
            ChatMessage.__table__.update().where(
                and_(
                    ChatMessage.id.in_(data.message_ids),
                    ChatMessage.receiver_user_id == current_user.id,
                )
            ).values(is_read=True)
        )
    else:
        await db.execute(
            ChatMessage.__table__.update().where(
                and_(ChatMessage.receiver_user_id == current_user.id, ChatMessage.is_read == False)
            ).values(is_read=True)
        )
    await db.commit()

    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.publish("chat:messages", json.dumps({
            "type": "read",
            "data": {
                "partnerId": data.counterpart_id,
                "partnerType": data.counterpart_type,
                "messageIds": data.message_ids,
            },
        }, default=str))
        await r.aclose()
    except Exception:
        pass

    return {"detail": "Messages marked as read"}
