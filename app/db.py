import json
import typing as t
from contextlib import contextmanager
from uuid import uuid4

import sqlalchemy as s
from redis import Redis
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound  # noqa
from sqlalchemy.pool import NullPool

import settings
from app.reporting import get_logger

redis_raw = Redis.from_url(
    settings.REDIS_URL,
    socket_connect_timeout=3,
    socket_keepalive=True,
    retry_on_timeout=False,
)

engine = s.create_engine(
    settings.POSTGRES_DSN,
    connect_args=settings.POSTGRES_CONNECT_ARGS,
    poolclass=NullPool,
    json_serializer=json.dumps,
    json_deserializer=json.loads,
)

SessionMaker = sessionmaker(bind=engine)
db_session = SessionMaker()
Base = declarative_base()  # type: t.Any

log = get_logger("db")


@contextmanager
def session_scope() -> t.Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = SessionMaker()
    sid = str(uuid4())
    log.debug(f"Session {sid} created.")
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        log.warning(f"Session {sid} rolled back.")
        raise
    finally:
        session.close()
        log.debug(f"Session {sid} closed.")
