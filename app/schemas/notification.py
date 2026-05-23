from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime


class DeviceTokenRequest(BaseModel):
    fcm_token: str
    device_type: str


class NotificationResponse(BaseModel):
    guid: str
    title: str
    body: str
    notification_type: str
    is_read: bool
    created_at: datetime

    @field_validator('guid', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class NotificationReadRequest(BaseModel):
    notification_ids: Optional[list] = None
