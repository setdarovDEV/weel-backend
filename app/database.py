"""Database configuration re-exporting from infrastructure layer."""

from app.infrastructure.database.connection import Base, create_engine, AsyncSessionLocal


async def get_db():
    """Dependency to get async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
