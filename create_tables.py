"""Create all database tables from SQLAlchemy models.

Usage:
    python create_tables.py

This script initializes an empty database by creating all tables
defined in the SQLAlchemy models. Run this once on a fresh database.
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.infrastructure.database.connection import Base

# Import all models so they are registered in Base.metadata
from app.infrastructure.database.models import (
    user,
    location,
    property as property_module,
    booking,
    payment,
    review,
    chat,
    story,
    notification,
)


async def create_tables():
    engine = create_async_engine(
        settings.database_url,
        echo=True,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("All tables created successfully!")


if __name__ == "__main__":
    asyncio.run(create_tables())
