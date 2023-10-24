import json
from http import HTTPStatus
from unittest.mock import patch
from urllib.parse import urljoin
from app.api import create_app
import os
import httpretty
import pytest
from soteria.configuration import Configuration
from app.journeys.join import attempt_join
import settings
from app.models import RetryTask
from app.scheme_account import SchemeAccountStatus, JourneyTypes, update_pending_join_account
from app.journeys.join import login_and_publish_status

settings.API_AUTH_ENABLED = False


@pytest.fixture
def client():
    """Configures the app for testing
    Can be used to make requests to API end points from unit tests for white box testing

    :return: App for testing
    """
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    yield client


def read_fixture_json():
    path = os.getcwd() + "/app/tests/component/wasabi.json"
    with open(path, "r") as json_fixture:
        data = json.load(json_fixture)
        return data


@pytest.fixture
def retailer_fixture():
    return read_fixture_json()


REQUEST_TYPES = {
    "POST": httpretty.POST,
    "PATCH": httpretty.PATCH,
    "GET": httpretty.GET,
    "PUT": httpretty.PUT,
    "DELETE": httpretty.DELETE,
}


@pytest.fixture
def europa_response(retailer_fixture):
    return {
        "merchant_url": "https://localhost/",
        "retry_limit": 3,
        "log_level": 0,
        "callback_url": "",
        "country": "uk",
        "security_credentials": {
            "inbound": {"service": Configuration.OPEN_AUTH_SECURITY, "credentials": []},
            "outbound": {
                "service": Configuration.OAUTH_SECURITY,
                "credentials": [retailer_fixture["security_credentials"]],
            },
        },
    }


@pytest.fixture
def mock_europa_request():
    def mock_request(response=None):
        uri = "http://mock_europa.com/configuration"
        httpretty.register_uri(
            httpretty.GET,
            uri=uri,
            status=HTTPStatus.OK,
            body=json.dumps(response),
            content_type="text/json",
        )

    return mock_request


@pytest.fixture
def mock_signals(monkeypatch):
    call_list = []

    class Signal:
        def __init__(self, *args, **_):
            self.name = None
            if len(args) > 0:
                self.name = args[0]

        def send(self, *args, **kwargs):
            if self.name:
                call_list.append({"name": self.name, "params": {"args": args, "kwargs": kwargs}})

    class MockSignals:
        def __init__(self, patches=None, base_agent=False):
            if patches:
                for patch in patches:
                    monkeypatch.setattr(patch, Signal)
            if base_agent:
                monkeypatch.setattr("app.agents.base.signal", Signal)

        @property
        def count(self):
            return len(call_list)

        @property
        def full_list(self):
            return call_list

        @property
        def name_list(self):
            return [call["name"] for call in call_list]

        @staticmethod
        def has(name):
            for call in call_list:
                if call.get("name") == name:
                    return True
            return False

        @staticmethod
        def get(name):
            """
            :param name:
            :return: tuple args and kwargs for named signal
            """
            for call in call_list:
                if call.get("name") == name:
                    params = call.get("params", {"args": [], "kwargs": {}})
                    return params.get("args", []), params.get("kwargs", {})
            return None, None

    return MockSignals


@pytest.fixture
def http_pretty_mock():
    class MockRequest:
        def __init__(self, response_body):
            self.response_body = response_body
            self.request_json = None
            self.request_uri = None
            self.request = None
            self.call_count = 0

        def call_back(self, request, uri, response_headers):
            self.request_json = None
            try:
                self.request_json = json.loads(request.body)
            except json.JSONDecodeError:
                pass
            self.request = request
            self.request_uri = uri
            self.call_count += 1
            return [200, response_headers, json.dumps(self.response_body)]

    def mock_setup(url, action=httpretty.GET, status=HTTPStatus.OK, response=None):
        mock_request = MockRequest(response)
        httpretty.register_uri(
            action,
            uri=url,
            status=status,
            body=mock_request.call_back,
            content_type="text/json",
        )
        return mock_request

    return mock_setup


@pytest.fixture
def redis_retry_pretty_fix(monkeypatch):
    """
    Redis connection fails if HTTPPretty is active so the hack is to mock out get_count which uses redis

    """

    def get_count(_):
        return 0

    def inc_count(_):
        pass

    def max_out_count(_):
        pass

    monkeypatch.setattr("app.redis_retry.get_count", get_count)
    monkeypatch.setattr("app.redis_retry.inc_count", inc_count)
    monkeypatch.setattr("app.redis_retry.max_out_count", max_out_count)


@pytest.fixture()
def apply_wasabi_patches(monkeypatch, mock_europa_request, redis_retry_pretty_fix, retailer_fixture, europa_response):
    def patchit():
        monkeypatch.setattr("app.agents.acteol.get_task", lambda *_: RetryTask(request_data={"ctcid": "ctcid"}))

    return patchit


@pytest.fixture()
def apply_bpl_patches(monkeypatch):
    def patchit():
        join_get_task = RetryTask(awaiting_callback=True)
        if "bpl" in retailer_fixture["slug"]:
            join_get_task.request_data = {"credentials": ""}
            monkeypatch.setattr("app.bpl_callback.hash_ids.decode", lambda *_: ["123"])
            monkeypatch.setattr("app.bpl_callback.decrypt_credentials", lambda *_: retailer_fixture["credentials"])
            monkeypatch.setattr("app.bpl_callback.get_task", lambda *_: join_get_task)
            monkeypatch.setattr("app.bpl_callback.delete_task", lambda *_: None)


@pytest.fixture()
def apply_login_patches(monkeypatch, mock_europa_request, redis_retry_pretty_fix, retailer_fixture, europa_response):
    def patchit():
        monkeypatch.setattr("app.resources.decrypt_credentials", lambda *_: retailer_fixture["credentials"])
        monkeypatch.setattr("app.journeys.join.decrypt_credentials", lambda *_: retailer_fixture["credentials"])
        monkeypatch.setattr(settings, "CONFIG_SERVICE_URL", "http://mock_europa.com")
        monkeypatch.setattr(
            Configuration, "get_security_credentials", lambda *_: [retailer_fixture["security_credentials"]]
        )
        monkeypatch.setattr("{}.authenticate".format(retailer_fixture["agent_path"]), lambda *_: None)
        mock_europa_request(europa_response)

    return patchit


@pytest.fixture()
def apply_db_patches(monkeypatch, mock_europa_request, redis_retry_pretty_fix, retailer_fixture):
    def patchit():
        join_get_task = RetryTask()
        monkeypatch.setattr("app.journeys.join.get_task", lambda *_: join_get_task)
        monkeypatch.setattr("app.journeys.join.delete_task", lambda *_: None)

    return patchit


@pytest.fixture
def client():
    """Configures the app for testing
    Can be used to make requests to API end points from unit tests for white box testing

    :return: App for testing
    """
    app = create_app()
    app.config["TESTING"] = True
    client = app.test_client()

    yield client


@pytest.fixture
def apply_mock_end_points(http_pretty_mock, retailer_fixture, europa_response):
    def mocks():
        hermes_mock_status = http_pretty_mock(
            f"{settings.HERMES_URL}/schemes/accounts/123/status", httpretty.POST, 200, {}
        )
        hermes_mock_credentials = http_pretty_mock(
            f"{settings.HERMES_URL}/schemes/accounts/123/credentials", httpretty.PUT, 200, {}
        )
        hermes_mock_consents = http_pretty_mock(
            f"{settings.HERMES_URL}/schemes/user_consent/fake-consent-123",
            httpretty.PUT,
            200,
            {},
        )
        mocks = {
            "hermes_mock_update_status": hermes_mock_status,
            "hermes_mock_update_credentials": hermes_mock_credentials,
            "hermes_mock_consents": hermes_mock_consents,
        }
        responses = retailer_fixture["responses"]
        for k, v in responses.items():
            mocks.update(
                {
                    k: http_pretty_mock(
                        urljoin(europa_response["merchant_url"], v["endpoint"]),
                        REQUEST_TYPES[v["type"]],
                        v["status_code"],
                        v["response"],
                    )
                }
            )
        return mocks

    return mocks


@httpretty.activate
@patch("app.journeys.join.login_and_publish_status", side_effect=login_and_publish_status)
@patch("app.journeys.join.update_pending_join_account", side_effect=update_pending_join_account)
def test_join(
    mock_login_and_publish_status,
    mock_update_pending_join_account,
    apply_login_patches,
    apply_mock_end_points,
    apply_db_patches,
    apply_wasabi_patches,
    retailer_fixture,
):
    apply_login_patches()
    apply_db_patches()
    apply_mock_end_points()
    apply_wasabi_patches()
    user_info = {
        "user_set": "1",
        "bink_user_id": "1",
        "credentials": retailer_fixture["credentials"],
        "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
        "journey_type": JourneyTypes.JOIN.value,
        "scheme_account_id": "123",
        "channel": "bink.com",
    }
    responses = retailer_fixture["responses"]
    attempt_join(user_info["scheme_account_id"], "1", retailer_fixture["slug"], user_info)
    mock_login_and_publish_status.assert_called()
    mock_update_pending_join_account.assert_called()
    # publish.balance called
    # send balance to hades called
    # publish transaction
    # publish status


@httpretty.activate
@patch("app.agents.bpl.get_task")
@patch("app.journeys.join.login_and_publish_status", side_effect=login_and_publish_status)
@patch("app.journeys.join.update_pending_join_account", side_effect=update_pending_join_account)
def test_join_with_callback(
    mock_get_task,
    mock_login_and_publish_status,
    mock_update_pending_join_account,
    apply_login_patches,
    apply_mock_end_points,
    apply_db_patches,
    retailer_fixture,
    client,
):
    apply_login_patches()
    apply_db_patches()
    apply_mock_end_points()
    mock_get_task.return_value = RetryTask(awaiting_callback=True)
    user_info = {
        "user_set": "1",
        "bink_user_id": "1",
        "credentials": retailer_fixture["credentials"],
        "status": SchemeAccountStatus.JOIN_ASYNC_IN_PROGRESS,
        "journey_type": JourneyTypes.JOIN.value,
        "scheme_account_id": "123",
        "channel": "bink.com",
    }
    responses = retailer_fixture["responses"]
    attempt_join(user_info["scheme_account_id"], "1", retailer_fixture["slug"], user_info)
    client.post(
        "/join/bpl/bpl-viator",
        data=json.dumps(
            {
                "UUID": "7e54d768-033e-40fa-999a-76c21bdd9c42",
                "email": "ncostaa@bink.com",
                "account_number": 56789,
                "third_party_identifier": "8v5zjgey0xd7k618x43wmpo2139lq4r8",
            }
        ),
        headers={"Content-type": "application/json"},
    )
    mock_login_and_publish_status.assert_called()
    mock_update_pending_join_account.assert_called()
    # publish.balance called
    # send balance to hades called
    # publish transaction
    # publish status


@httpretty.activate
def test_login(apply_login_patches, apply_mock_end_points, apply_db_patches, retailer_fixture, client):
    retailer_fixture["credentials"]["card_number"] = "123"
    apply_login_patches()
    apply_db_patches()
    apply_mock_end_points()
    scheme_account_id = "123"
    bink_user_id = "1"
    user_id = "1"
    balance_response = client.get(
        f"/{retailer_fixture['slug']}/balance?scheme_account_id={scheme_account_id}"
        f"&user_id={user_id}&bink_user_id={bink_user_id}"
        f"&journey_type=2"
        "&credentials=xxx&token=xxx"
    )
    assert balance_response.status_code == 200
    assert balance_response.json == "{}"
