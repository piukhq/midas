import pytest

from app.db import redis_raw
from app.exceptions import BaseError


def test_on_join_application_success(task_consumer, message, mock_db, mock_create_task, mock_enqueue_task, user_info):
    task_consumer.on_join_application(message)
    mock_create_task.assert_called_with(
        journey_type="attempt-join",
        message_uid="123",
        scheme_account_id=123,
        scheme_identifier="1234",
        user_info=user_info,
        db_session=mock_db.session_scope().__enter__(),
    )
    mock_enqueue_task.assert_called_with(connection=redis_raw, retry_task=mock_create_task.return_value)


def test_on_join_application_join_data_in_encrypted_credentials(
    task_consumer, message_encrypted_credentials, mock_db, mock_create_task, mock_enqueue_task, user_info
):
    task_consumer.on_join_application(message_encrypted_credentials)
    mock_create_task.assert_called_with(
        journey_type="attempt-join",
        message_uid="123",
        scheme_account_id=123,
        scheme_identifier="1234",
        user_info=user_info,
        db_session=mock_db.session_scope().__enter__(),
    )
    mock_enqueue_task.assert_called_with(connection=redis_raw, retry_task=mock_create_task.return_value)


def test_on_join_application_raises_base_error(
    task_consumer, message_encrypted_credentials, mock_db, mock_create_task, mock_enqueue_task, user_info, mocker
):
    mock_sentry = mocker.patch("app.messaging.consumer.sentry_sdk.capture_exception")
    mock_create_task.side_effect = BaseError()
    with pytest.raises(BaseError) as e:
        assert task_consumer.on_join_application(message_encrypted_credentials) is None
        mock_create_task.assert_called_with(
            journey_type="attempt-join",
            message_uid="123",
            scheme_account_id=123,
            scheme_identifier="1234",
            user_info=user_info,
            db_session=mock_db.session_scope().__enter__(),
        )
        assert (
            mock_enqueue_task.assert_called_with(connection=redis_raw, retry_task=mock_create_task.return_value)
            is False
        )
        mock_sentry.assert_called_with(e)

