import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from src.database import Base
from src.papers.models import Paper, Tag  # noqa: F401

_container = None
_db_url = None


def pytest_configure(config):
    global _container, _db_url
    _container = PostgresContainer("postgres:16-alpine")
    _container.start()
    sync_url = _container.get_connection_url()
    _db_url = sync_url.replace("postgresql+psycopg2://", "postgresql+asyncpg://")
    os.environ["DATABASE_URL"] = _db_url


def pytest_unconfigure(config):
    global _container
    if _container:
        _container.stop()


@pytest.fixture(scope="session")
def database_url() -> str:
    return _db_url


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine(database_url):
    eng = create_async_engine(database_url, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session(engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as sess:
        yield sess
        await sess.rollback()


@pytest_asyncio.fixture(loop_scope="session")
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    from src.database import create_session_factory
    from src.main import create_app

    app = create_app()

    session_factory = create_session_factory(engine)
    app.state.session_factory = session_factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
