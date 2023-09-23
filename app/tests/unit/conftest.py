import json
from http import HTTPStatus

import httpretty
import pytest

from app.api import create_app


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
    """
    Useful to generic mock to trap signals.
    Will need to be instantiated giving patches list and or base_agent=True
    see test_itsu_pepper conftest.py which shows use eg
    @pytest.fixture
        def mock_itsu_signals(mock_signals):
            return mock_signals(patches=["app.agents.itsu.signal"], base_agent=True)
    then just add mock_itsu_signals as a fixture and then use asserts such as;
          mock_itsu_signals.has("signal name")
          args, kwargs = mock_itsu_signals.get("signal name")
    Unlike unit test patching this does not require multiple decorators and gives call data as trapped (no call wrapper)

    :param monkeypatch:
    :return:
    """
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

    monkeypatch.setattr("app.redis_retry.get_count", get_count)
