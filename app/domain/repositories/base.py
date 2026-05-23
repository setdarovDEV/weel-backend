"""Abstract repository interfaces (ports) defining the contract for persistence.

Following the Dependency Inversion Principle (DIP), domain and application layers
depend on these abstractions, not concrete implementations.
"""

from typing import Generic, List, Optional, Protocol, TypeVar

T = TypeVar("T")
ID = TypeVar("ID")


class IRepository(Protocol, Generic[T, ID]):
    """Generic repository interface (Port)."""

    async def get_by_id(self, entity_id: ID) -> Optional[T]: ...

    async def list_all(self, *, skip: int = 0, limit: int = 100) -> List[T]: ...

    async def add(self, entity: T) -> T: ...

    async def update(self, entity: T) -> T: ...

    async def delete(self, entity: T) -> None: ...


class IUnitOfWork(Protocol):
    """Unit of Work interface for transactional boundary."""

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...

    async def __aenter__(self) -> "IUnitOfWork": ...

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
