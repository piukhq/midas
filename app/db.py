import json
import typing as t

import sqlalchemy as s
from retry_tasks_lib.db.models import load_models_to_metadata
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound  # noqa
from sqlalchemy.pool import NullPool

import settings
from app.reporting import get_logger

engine = s.create_engine(
    settings.POSTGRES_DSN,
    poolclass=NullPool,
    json_serializer=json.dumps,
    json_deserializer=json.loads,
)

SessionMaker = sessionmaker(bind=engine)
db_session = SessionMaker()
Base = declarative_base()  # type: t.Any
load_models_to_metadata(Base.metadata)

log = get_logger("db")