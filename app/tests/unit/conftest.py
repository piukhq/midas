import pytest


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
        def call_count(self):
            return len(call_list)

        @property
        def calls(self):
            return call_list

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
