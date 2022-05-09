from unittest import mock

import pytest
import sqlalchemy as s
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import db
from app.db import Base


class TestModel(Base):
    __tablename__ = "test_table"
    id = s.Column(s.Integer, primary_key=True)
    key = s.Column(s.String(100), nullable=False, index=True, unique=True)
    value = s.Column(s.String(100), nullable=False)


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    connection = engine.connect()
    TestModel.metadata.create_all(engine)
    session = Session(bind=connection)
    transaction = connection.begin_nested()
    try:
        yield session
    finally:
        transaction.rollback()
        session.close()
        Base.metadata.drop_all(engine)


def test_get_or_create(db_session):
    assert db._get_one_or_none(TestModel, key="potato", session=db_session) is None

    ci, created = db.get_or_create(TestModel, key="potato", defaults={"value": "mashed"}, session=db_session)
    assert created is True
    assert ci.value == "mashed"

    ci, created = db.get_or_create(TestModel, key="potato", defaults={"value": "baked"}, session=db_session)
    assert created is False
    assert ci.value == "mashed"


def test_get_or_create_integrity_error(db_session):
    with mock.patch("app.db.run_query") as mock_run_query:
        mock_run_query.side_effect = [
            None,
            IntegrityError("<...statement...>", params=(), orig=Exception()),
            TestModel(key="potato", value="boiled"),
        ]
        ci, created = db.get_or_create(TestModel, key="potato", defaults={"value": "chipped"}, session=db_session)
        assert created is False
        assert ci.value == "boiled"
