from unittest import TestCase, mock

import kombu
from olympus_messaging import JoinApplication, LoyaltyCardRemoved

from app.db import redis_raw
from app.exceptions import UnknownError
from consumer import TaskConsumer


class TestConsumer(TestCase):
    def setUp(self) -> None:
        conn = kombu.Connection("memory://")
        self.consumer = TaskConsumer(connection=conn)
        self.user_info = {
            "bink_user_id": "1234",
            "channel": "test",
            "credentials": {"abc": "def"},
            "journey_type": 0,
            "scheme_account_id": 123,
            "status": 442,
            "user_set": "1234",
        }
        self.join_application_message = JoinApplication(
            channel="test",
            transaction_id="123",
            bink_user_id="1234",
            request_id=123,
            loyalty_plan="1234",
            account_id="456",
            join_data={"abc": "def"},
        )

        self.loyalty_card_removed_message = LoyaltyCardRemoved(
            channel="test.com",
            transaction_id="123",
            bink_user_id="99999",
            request_id="1223232",
            account_id="12345678989",
            loyalty_plan="10",
        )

    @mock.patch("app.messaging.consumer.db")
    @mock.patch("app.messaging.consumer.create_task")
    @mock.patch("app.messaging.consumer.enqueue_retry_task")
    def test_join_on_application_success(self, mock_enqueue_task, mock_create_task, mock_db):
        self.consumer.on_join_application(self.join_application_message)
        mock_create_task.assert_called_with(
            journey_type="attempt-join",
            message_uid="123",
            scheme_account_id=123,
            scheme_identifier="1234",
            user_info=self.user_info,
            db_session=mock_db.session_scope().__enter__(),
        )
        mock_enqueue_task.assert_called_with(connection=redis_raw, retry_task=mock_create_task.return_value)

    @mock.patch("app.messaging.consumer.sentry_sdk.capture_exception")
    @mock.patch("app.messaging.consumer.db")
    @mock.patch("app.messaging.consumer.create_task")
    @mock.patch("app.messaging.consumer.enqueue_retry_task")
    def test_on_join_application_raises_base_error(self, mock_enqueue_task, mock_create_task, mock_db, mock_sentry):
        mock_create_task.side_effect = UnknownError()
        self.assertEqual(self.consumer.on_join_application(self.join_application_message), None)
        mock_create_task.assert_called_with(
            journey_type="attempt-join",
            message_uid="123",
            scheme_account_id=123,
            scheme_identifier="1234",
            user_info=self.user_info,
            db_session=mock_db.session_scope().__enter__(),
        )
        self.assertFalse(mock_enqueue_task.called)
        self.assertTrue(mock_sentry.assert_called)

    @mock.patch("app.messaging.consumer.db")
    @mock.patch("app.messaging.consumer.create_task")
    @mock.patch("app.messaging.consumer.enqueue_retry_task")
    def test_on_join_application_join_data_in_encrypted_credentials(self, mock_enqueue_task, mock_create_task, mock_db):
        message = JoinApplication(
            channel="test",
            transaction_id="123",
            bink_user_id="1234",
            request_id=123,
            loyalty_plan="1234",
            account_id="456",
            join_data={"encrypted_credentials": {"abc": "def"}},
        )

        self.consumer.on_join_application(message)
        mock_create_task.assert_called_with(
            journey_type="attempt-join",
            message_uid="123",
            scheme_account_id=123,
            scheme_identifier="1234",
            user_info=self.user_info,
            db_session=mock_db.session_scope().__enter__(),
        )
        mock_enqueue_task.assert_called_with(connection=redis_raw, retry_task=mock_create_task.return_value)

    @mock.patch("app.messaging.consumer.attempt_loyalty_card_removed")
    def test_loyalty_card_removed_success(self, mock_removed_task):
        self.consumer.on_loyalty_card_removed(self.loyalty_card_removed_message)
        mock_removed_task.assert_called_with(
            "10",
            {
                "user_set": "99999",
                "bink_user_id": "99999",
                "scheme_account_id": 1223232,
                "channel": "test.com",
                "account_id": "12345678989",
                "message_uid": "123",
                "credentials": {},
                "journey_type": 4,
            },
        )

    @mock.patch("app.messaging.consumer.sentry_sdk.capture_exception")
    @mock.patch("app.messaging.consumer.attempt_loyalty_card_removed")
    def test_loyalty_card_removed_raises_base_error(self, mock_removed_task, mock_sentry):
        mock_removed_task.side_effect = UnknownError()
        self.assertEqual(self.consumer.on_loyalty_card_removed(self.loyalty_card_removed_message), None)
        mock_removed_task.assert_called_with(
            "10",
            {
                "user_set": "99999",
                "bink_user_id": "99999",
                "scheme_account_id": 1223232,
                "channel": "test.com",
                "account_id": "12345678989",
                "message_uid": "123",
                "credentials": {},
                "journey_type": 4,
            },
        )
        # Sentry error should be raised if message has errors but the called removed journey will not raise a
        # sentry error if the agent has not been configured for removed handler
        self.assertTrue(mock_sentry.called)
