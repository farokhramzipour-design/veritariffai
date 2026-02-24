from __future__ import annotations
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost:5432/tce",
    pool_pre_ping=True,
)

AsyncSessionMaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

async def get_session() -> AsyncSession:
    async with AsyncSessionMaker() as session:
        yield session
