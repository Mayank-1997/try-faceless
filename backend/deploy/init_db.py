"""One-shot DB schema init for fresh deploys.

The app's lifespan only runs ``create_all`` in development mode; production
relies on Alembic — but migration ``0002_business_domain`` has foreign keys
to ``users`` (auth tables), which have no migration. On a fresh DB this
script runs the same ``create_all`` the dev path uses; the container CMD
then runs ``alembic stamp head`` so future ``upgrade head`` runs are no-ops.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import src.persistence.models  # noqa: E402,F401 — register all models on the metadata
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config import get_settings
from src.persistence.models.base import Base


async def main() -> None:
    engine = create_async_engine(get_settings().database.url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("database schema initialised")


if __name__ == "__main__":
    asyncio.run(main())
