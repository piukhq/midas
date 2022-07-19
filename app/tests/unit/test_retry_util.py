import unittest
from datetime import datetime

from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import create_database, database_exists, drop_database

from app import db
from app.db import Base, engine
from app.models import RetryTaskStatuses
from app.retry_util import (
    create_task,
    delete_task,
    fail_callback_task,
    reset_task_for_callback_attempt,
    update_callback_attempt,
    update_task_for_retry,
)


class TestRetryUtil(unittest.TestCase):
    def setUp(self):
        if engine.url.database != "midas_test":
            raise ValueError(f"Unsafe attempt to recreate database: {engine.url.database}")
        SessionMaker = sessionmaker(bind=engine)
        if database_exists(engine.url):
            drop_database(engine.url)
        create_database(engine.url)
        Base.metadata.create_all(bind=engine)
        self.db_session = SessionMaker()

    def tearDown(self) -> None:
        self.db_session.close()
        drop_database(engine.url)

    def test_update_task_for_retry(self):
        with db.session_scope() as session:
            retry_task = create_task(
                db_session=session,
                user_info={},
                journey_type="journey",
                message_uid="123",
                scheme_identifier="scheme",
                scheme_account_id="123",
            )
            update_task_for_retry(
                session, retry_task=retry_task, retry_status=RetryTaskStatuses.PENDING, next_attempt_time=datetime.now()
            )
            self.assertEqual(retry_task.attempts, 1)
            self.assertEqual(retry_task.status, RetryTaskStatuses.PENDING)
            self.assertIsNotNone(retry_task.next_attempt_time)
            delete_task(session, retry_task)

    def test_reset_task_for_callback_attempt(self):
        with db.session_scope() as session:
            retry_task = create_task(
                db_session=session,
                user_info={},
                journey_type="journey",
                message_uid="123",
                scheme_identifier="scheme",
                scheme_account_id="123",
            )
            update_task_for_retry(
                session, retry_task=retry_task, retry_status=RetryTaskStatuses.PENDING, next_attempt_time=datetime.now()
            )
            reset_task_for_callback_attempt(
                session, retry_task, retry_status=RetryTaskStatuses.FAILED, next_attempt_time=datetime.now()
            )
            self.assertEqual(retry_task.attempts, 0)
            self.assertEqual(retry_task.callback_retries, 1)
            self.assertEqual(retry_task.status, RetryTaskStatuses.FAILED)
            delete_task(session, retry_task)

    def test_update_callback_attempt(self):
        with db.session_scope() as session:
            retry_task = create_task(
                db_session=session,
                user_info={},
                journey_type="journey",
                message_uid="123",
                scheme_identifier="scheme",
                scheme_account_id="123",
            )
            update_callback_attempt(session, retry_task=retry_task, next_attempt_time=datetime.now())
            self.assertEqual(retry_task.callback_retries, 1)
            self.assertEqual(retry_task.status, RetryTaskStatuses.PENDING)
            delete_task(session, retry_task)

    def test_fail_callback_task(self):
        with db.session_scope() as session:
            retry_task = create_task(
                db_session=session,
                user_info={},
                journey_type="journey",
                message_uid="123",
                scheme_identifier="scheme",
                scheme_account_id="123",
            )
            fail_callback_task(session, retry_task=retry_task)
            self.assertEqual(retry_task.status, RetryTaskStatuses.FAILED)
            delete_task(session, retry_task)
