from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime


class StoryResponse(BaseModel):
    guid: str
    property_id: str
    media_url: str
    media_type: str
    views: int
    created_at: datetime

    @field_validator('guid', 'property_id', mode='before')
    @classmethod
    def convert_guid(cls, v):
        return str(v) if v else v

    class Config:
        from_attributes = True


class StoryCreateRequest(BaseModel):
    property_id: str
    media_type: str


class ReviewCreateRequest(BaseModel):
    rating: int
    comment: Optional[str]


class ReviewResponse(BaseModel):
    guid: str
    user_name: str
    rating: int
    comment: Optional[str]
    created_at: datetime
    reply_comment: Optional[str]
    reply_created_at: Optional[datetime]

    class Config:
        from_attributes = True
