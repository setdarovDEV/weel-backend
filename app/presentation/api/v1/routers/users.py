from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.user import User
from app.presentation.api.v1.deps import get_current_active_user

router = APIRouter()


@router.get("/me/")
async def get_me(current_user: User = Depends(get_current_active_user)):
    return {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "is_active": current_user.is_active,
        "role": current_user.role,
    }
