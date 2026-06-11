import contextlib
from collections.abc import AsyncGenerator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    poolclass=NullPool,
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    },
)



class DatabaseConnection:
    def __init__(self, connection: AsyncConnection):
        self.connection = connection
        self._transaction = None

    async def execute(self, statement, parameters=None):
        return await self.connection.execute(statement, parameters)

    async def scalar(self, statement, parameters=None):
        return await self.connection.scalar(statement, parameters)

    async def commit(self) -> None:
        if self._transaction:
            await self._transaction.commit()
            self._transaction = None
        else:
            await self.connection.commit()

    async def rollback(self) -> None:
        if self._transaction:
            await self._transaction.rollback()
            self._transaction = None
        else:
            await self.connection.rollback()

    async def flush(self) -> None:
        # Flush is a no-op for core connections since SQL commands execute immediately
        pass

    @contextlib.asynccontextmanager
    async def begin(self):
        async with self.connection.begin() as trans:
            self._transaction = trans
            try:
                yield trans
            except Exception:
                await trans.rollback()
                self._transaction = None
                raise
            else:
                self._transaction = None

    @contextlib.asynccontextmanager
    async def begin_nested(self):
        async with self.connection.begin_nested() as trans:
            yield trans


async def get_db() -> AsyncGenerator[DatabaseConnection, None]:
    async with engine.connect() as connection:
        db_conn = DatabaseConnection(connection)
        yield db_conn


@contextlib.asynccontextmanager
async def get_db_session() -> AsyncGenerator[DatabaseConnection, None]:
    async with engine.connect() as connection:
        db_conn = DatabaseConnection(connection)
        yield db_conn

