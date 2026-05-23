from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
from app.utils.enums import SenderType


class ChatMessageBase(BaseModel):
    id: Optional[int]
    text: str
    is_me: bool
    time: Optional[datetime]


class ChatMessageCreate(BaseModel):
    receiver_id: str
    receiver_type: str
    content: str


class ActorSchema(BaseModel):
    id: int
    role: Optional[str] = None
    full_name: str
    email: Optional[str] = None
    username: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


class ChatMessageResponse(BaseModel):
    id: int
    conversation_id: str
    sender_id: str
    sender_type: str
    receiver_id: str
    receiver_type: str
    content: str
    is_read: bool
    created_at: datetime

    @field_validator('conversation_id', 'sender_id', 'receiver_id', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    conversation_id: int
    counterpart: ActorSchema
    last_message: Optional[str] = None
    unread_count: int = 0
    created_at: datetime

    @field_validator('conversation_id', mode='before')
    @classmethod
    def convert_id(cls, v):
        return int(v) if v else v


class MarkReadRequest(BaseModel):
    message_ids: List[int] = []
    counterpart_id: Optional[int] = None
    counterpart_type: Optional[str] = None


class RecipientResponse(BaseModel):
    id: str
    name: str
    role: str
