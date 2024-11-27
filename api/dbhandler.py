import typing
from datetime import datetime
from typing import Annotated
import psycopg2
import sqlalchemy as sa
from sqlalchemy.orm import (
    DeclarativeBase,
    mapped_column
)
from sqlalchemy.dialects.postgresql import psycopg2
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

intpk = Annotated[int, mapped_column(primary_key=True, index=True)]
null_str = Annotated[str, mapped_column(nullable=True)]
indexed_str = Annotated[str, mapped_column(index=True)]
intr_id = Annotated[int, mapped_column(sa.ForeignKey('main.internal_req_id'))]
create_date = Annotated[datetime, mapped_column(default=datetime.now)]


class SqlAlchemyBase(DeclarativeBase):
    pass


factory = None

__engine = None


def global_init(password, host_ip, port, database_name):
    global factory, __engine
    if factory:
        return

    try:
        conn_str = f'postgresql+asyncpg://postgres:{password}@{host_ip}:{port}/{database_name}'
        print(f"Подключение к базе данных по адресу {conn_str}")
    except psycopg2.OperationalError:
        return "Bad request. Failed to connection to "

    __engine = create_async_engine(conn_str,
                                   echo=True,
                                   pool_pre_ping=True,
                                   pool_recycle=2,
                                   use_insertmanyvalues=True)

    factory = async_sessionmaker(bind=__engine, expire_on_commit=False, autocommit=False, autoflush=False, )

    from . import __all_models


async def initialize_tables():
    global __engine
    async with __engine.begin() as conn:
        await conn.run_sync(SqlAlchemyBase.metadata.create_all)


async def create_session() -> typing.AsyncGenerator[AsyncSession, None]:
    global factory

    async with factory() as session:
        yield session
