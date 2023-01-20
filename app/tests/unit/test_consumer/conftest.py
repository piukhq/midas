import kombu
import pytest
from olympus_messaging import JoinApplication
from pytest_mock import mocker  # noqa

from consumer import TaskConsumer


@pytest.fixture()
def mock(mocker):  # noqa
    return mocker


@pytest.fixture()
def task_consumer():
    conn = kombu.Connection("memory://")
    consumer = TaskConsumer(connection=conn)
    return consumer


@pytest.fixture()
def message():
    return JoinApplication(
        channel="test",
        transaction_id="123",
        bink_user_id="1234",
        request_id=123,
        loyalty_plan="1234",
        account_id="456",
        join_data={"abc": "def"},
    )


@pytest.fixture()
def mock_db(mock):
    return mock.patch("app.messaging.consumer.db")


@pytest.fixture()
def mock_create_task(mock):
    return mock.patch("app.messaging.consumer.create_task")


@pytest.fixture()
def mock_enqueue_task(mock):
    return mock.patch("app.messaging.consumer.enqueue_retry_task")


@pytest.fixture()
def message_encrypted_credentials():
    return JoinApplication(
        channel="test",
        transaction_id="123",
        bink_user_id="1234",
        request_id=123,
        loyalty_plan="1234",
        account_id="456",
        join_data={"encrypted_credentials": {"abc": "def"}},
    )


@pytest.fixture()
def user_info():
    return {
        "bink_user_id": "1234",
        "channel": "test",
        "credentials": {"abc": "def"},
        "journey_type": 0,
        "scheme_account_id": 123,
        "status": 442,
        "user_set": "1234"
    }
