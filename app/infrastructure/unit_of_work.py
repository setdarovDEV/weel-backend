"""SQLAlchemy Unit of Work implementation."""

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.base import IUnitOfWork


class SqlAlchemyUnitOfWork(IUnitOfWork):
    """Transactional boundary using SQLAlchemy async session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()

    async def __aenter__(self) -> "SqlAlchemyUnitOfWork":
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type:
            await self.rollback()
        else:
            await self.commit()
