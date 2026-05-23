"""FastAPI dependencies wiring application services and authentication."""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AuthenticationException, AuthorizationException
from app.core.logging_config import get_logger
from app.core.security import decode_token
from app.infrastructure.database.connection import AsyncSessionLocal
from app.infrastructure.database.models.user import User
from app.application.services.auth_service import AuthApplicationService

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/user/client/login/verify/")


async def get_db() -> AsyncSession:
    """Dependency that yields an async DB session with auto-commit/rollback."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthApplicationService:
    """Factory dependency injecting AuthApplicationService."""
    return AuthApplicationService(db)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user: User | None = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exception
    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def require_role(role: str):
    """Dependency factory to enforce a specific user role.

    Returns an async callable that FastAPI can use with Depends().
    """

    async def _checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' required",
            )
        return current_user

    return _checker


get_current_client = require_role("client")
get_current_partner = require_role("partner")
get_current_admin = require_role("admin")
