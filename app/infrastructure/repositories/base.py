from typing import Generic, List, Optional, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")


class SqlAlchemyRepository(Generic[T]):
    """Generic SQLAlchemy repository implementing common CRUD operations.

    Follows the Repository Pattern and Open/Closed Principle (OCP):
    new entities extend this class without modifying existing code.
    """

    def __init__(self, session: AsyncSession, model_class: Type[T]) -> None:
        self._session = session
        self._model_class = model_class

    async def get_by_id(self, entity_id: str) -> Optional[T]:
        result = await self._session.execute(
            select(self._model_class).where(self._model_class.guid == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> List[T]:
        result = await self._session.execute(
            select(self._model_class).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: T) -> T:
        await self._session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()


class SqlAlchemyIntRepository(Generic[T]):
    """Generic repository for integer PK models."""

    def __init__(self, session: AsyncSession, model_class: Type[T]) -> None:
        self._session = session
        self._model_class = model_class

    async def get_by_id(self, entity_id: int) -> Optional[T]:
        result = await self._session.execute(
            select(self._model_class).where(self._model_class.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> List[T]:
        result = await self._session.execute(
            select(self._model_class).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def add(self, entity: T) -> T:
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def update(self, entity: T) -> T:
        await self._session.flush()
        return entity

    async def delete(self, entity: T) -> None:
        await self._session.delete(entity)
        await self._session.flush()
