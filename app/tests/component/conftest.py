import json
import os
from http import HTTPStatus
from urllib.parse import urljoin

import httpretty
import pytest
from soteria.configuration import Configuration

import settings
from app.api import create_app
from app.models import RetryTask

REQUEST_TYPES = {
    "POST": httpretty.POST,
    "PATCH": httpretty.PATCH,
    "GET": httpretty.GET,
    "PUT": httpretty.PUT,
    "DELETE": httpretty.DELETE,
}


def pytest_addoption(parser):
    parser.addoption(
        "--stringinput",
        action="append",
        default=[],
        help="list of stringinputs to pass to test functions",
    )


def pytest_generate_tests(metafunc):
    if "stringinput" in metafunc.fixturenames:
        metafunc.parametrize("stringinput", metafunc.config.getoption("stringinput"))


@pytest.fixture
def retailer_fixture(request):
    filename = request.param
    path = os.getcwd() + f"/app/tests/component/retailer_fixtures/{filename}.json"
    with open(path, "r") as json_fixture:
        data = json.load(json_fixture)
        return data


# GENERIC PATCHES


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


@pytest.fixture()
def apply_login_patches(monkeypatch, mock_europa_request, retailer_fixture, europa_response):
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
def apply_db_patches(monkeypatch):
    def patchit():
        join_get_task = RetryTask()
        monkeypatch.setattr("app.journeys.join.get_task", lambda *_: join_get_task)
        monkeypatch.setattr("app.journeys.join.delete_task", lambda *_: None)

    return patchit


@pytest.fixture()
def apply_hermes_patches(monkeypatch, http_pretty_mock, retailer_fixture, europa_response):
    def mocks():
        return [
            http_pretty_mock(f"{settings.HERMES_URL}/schemes/accounts/123/status", httpretty.POST, 200, {}),
            http_pretty_mock(f"{settings.HERMES_URL}/schemes/accounts/123/credentials", httpretty.PUT, 200, {}),
            http_pretty_mock(
                f"{settings.HERMES_URL}/schemes/user_consent/fake-consent-123",
                httpretty.PUT,
                200,
                {},
            ),
        ]

    return mocks


@pytest.fixture
def apply_mock_end_points(http_pretty_mock, retailer_fixture, europa_response):
    def mocks():
        responses = retailer_fixture["responses"]
        mocks = []
        for response in responses:
            mocks.append(
                http_pretty_mock(
                    urljoin(europa_response["merchant_url"], response["endpoint"]),
                    REQUEST_TYPES[response["type"]],
                    response["status_code"],
                    response["response"],
                )
            )
        return mocks

    return mocks


# RETAILER-SPECIFIC PATCHES


@pytest.fixture()
def apply_wasabi_patches(monkeypatch):
    def patchit():
        monkeypatch.setattr("app.agents.acteol.get_task", lambda *_: RetryTask(request_data={"ctcid": "ctcid"}))

    return patchit


@pytest.fixture()
def apply_bpl_patches(monkeypatch, retailer_fixture):
    def patchit():
        join_get_task = RetryTask(awaiting_callback=True, request_data={"credentials": ""})
        join_get_task.request_data = {"credentials": ""}
        monkeypatch.setattr("app.bpl_callback.hash_ids.decode", lambda *_: ["123"])
        monkeypatch.setattr("app.bpl_callback.decrypt_credentials", lambda *_: retailer_fixture["credentials"])
        monkeypatch.setattr("app.bpl_callback.get_task", lambda *_: join_get_task)
        monkeypatch.setattr("app.agents.bpl.get_task", lambda *_: join_get_task)
        monkeypatch.setattr("app.bpl_callback.delete_task", lambda *_: None)

    return patchit


# OTHER
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
