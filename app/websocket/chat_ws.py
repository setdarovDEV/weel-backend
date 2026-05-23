import asyncio
import json
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select, and_, or_
import redis.asyncio as aioredis
from app.config import settings
from app.utils.security import decode_token
from app.infrastructure.database.connection import AsyncSessionLocal
from app.models.user import User
from app.models.chat import ChatConversation, ChatMessage

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]

    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            await self.active_connections[user_id].send_json(message)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.values():
            await connection.send_json(message)


manager = ConnectionManager()

REDIS_CHANNEL = "chat:messages"
_redis_listener_task: Optional[asyncio.Task] = None


async def _publish_message(message: dict):
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        await r.publish(REDIS_CHANNEL, json.dumps(message, default=str))
        await r.aclose()
    except Exception:
        pass


async def _handle_redis_message(data: dict):
    msg_type = data.get("type")
    payload = data.get("data", {})
    if msg_type == "message":
        receiver_id = payload.get("receiver_id")
        if receiver_id:
            await manager.send_personal_message({"type": "message", "data": payload}, str(receiver_id))
        sender_id = payload.get("sender_id")
        if sender_id:
            await manager.send_personal_message({"type": "message", "data": payload}, str(sender_id))
    elif msg_type == "read":
        partner_id = payload.get("partnerId")
        if partner_id:
            await manager.send_personal_message({"type": "read", "data": payload}, str(partner_id))


async def _listen_redis():
    try:
        r = aioredis.from_url(settings.redis_url, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(REDIS_CHANNEL)
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await _handle_redis_message(data)
                except Exception:
                    pass
    except asyncio.CancelledError:
        pass
    except Exception:
        pass


def _ensure_listener():
    global _redis_listener_task
    if _redis_listener_task is None or _redis_listener_task.done():
        _redis_listener_task = asyncio.create_task(_listen_redis())


@router.websocket("/chat/")
async def websocket_chat(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001)
        return

    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = str(payload.get("sub"))
    await manager.connect(websocket, user_id)
    _ensure_listener()

    async with AsyncSessionLocal() as db:
        try:
            while True:
                raw = await websocket.receive_text()
                try:
                    msg = json.loads(raw)
                    msg_type = msg.get("type", "message")
                    data = msg.get("data", {})

                    if msg_type == "message":
                        receiver_id = int(data.get("receiver_id", 0))
                        receiver_type = data.get("receiver_type", "partner")
                        content = data.get("content", "")
                        sender_id = int(user_id)

                        result = await db.execute(
                            select(ChatConversation).where(
                                or_(
                                    and_(ChatConversation.admin_user_id == sender_id, ChatConversation.partner_user_id == receiver_id),
                                    and_(ChatConversation.admin_user_id == receiver_id, ChatConversation.partner_user_id == sender_id),
                                    and_(ChatConversation.admin_user_id == sender_id, ChatConversation.client_user_id == receiver_id),
                                    and_(ChatConversation.admin_user_id == receiver_id, ChatConversation.client_user_id == sender_id),
                                )
                            )
                        )
                        conv = result.scalar_one_or_none()
                        if not conv:
                            if receiver_type == "client":
                                conv = ChatConversation(
                                    admin_user_id=sender_id,
                                    partner_user_id=receiver_id,
                                    client_user_id=receiver_id,
                                    created_at=datetime.now(timezone.utc),
                                    updated_at=datetime.now(timezone.utc),
                                )
                            else:
                                conv = ChatConversation(
                                    admin_user_id=sender_id,
                                    partner_user_id=receiver_id,
                                    created_at=datetime.now(timezone.utc),
                                    updated_at=datetime.now(timezone.utc),
                                )
                            db.add(conv)
                            await db.flush()

                        user_result = await db.execute(select(User).where(User.id == sender_id))
                        sender_user = user_result.scalar_one_or_none()
                        sender_role = sender_user.role if sender_user else "client"

                        msg_obj = ChatMessage(
                            conversation_id=conv.id,
                            sender_user_id=sender_id,
                            sender_role=sender_role,
                            receiver_user_id=receiver_id,
                            receiver_role=receiver_type,
                            content=content,
                            is_read=False,
                            created_at=datetime.now(timezone.utc),
                            updated_at=datetime.now(timezone.utc),
                        )
                        db.add(msg_obj)
                        await db.commit()
                        await db.refresh(msg_obj)

                        response = {
                            "id": msg_obj.id,
                            "sender_id": sender_id,
                            "sender_type": sender_role,
                            "receiver_id": receiver_id,
                            "receiver_type": receiver_type,
                            "content": content,
                            "is_read": False,
                            "created_at": msg_obj.created_at.isoformat(),
                        }

                        await manager.send_personal_message({
                            "type": "message",
                            "data": response,
                        }, str(receiver_id))
                        await manager.send_personal_message({
                            "type": "message",
                            "data": response,
                        }, user_id)

                        await _publish_message({"type": "message", "data": response})

                    elif msg_type == "typing":
                        receiver_id = data.get("receiver_id")
                        if receiver_id:
                            await manager.send_personal_message({
                                "type": "typing",
                                "data": {"sender_id": int(user_id)},
                            }, str(receiver_id))

                    elif msg_type == "read":
                        partner_id = data.get("partnerId")
                        message_ids = data.get("messageIds", [])
                        partner_type = data.get("partnerType", "partner")

                        if message_ids:
                            await db.execute(
                                ChatMessage.__table__.update().where(
                                    ChatMessage.id.in_(message_ids)
                                ).values(is_read=True)
                            )
                            await db.commit()

                        payload = {
                            "partnerId": partner_id,
                            "partnerType": partner_type,
                            "messageIds": message_ids,
                        }
                        await manager.send_personal_message({
                            "type": "read",
                            "data": payload,
                        }, user_id)

                        await _publish_message({"type": "read", "data": payload})

                    elif msg_type == "ping":
                        await websocket.send_json({"type": "pong"})

                except json.JSONDecodeError:
                    await websocket.send_json({"type": "error", "detail": "Invalid JSON"})

        except WebSocketDisconnect:
            manager.disconnect(user_id)
