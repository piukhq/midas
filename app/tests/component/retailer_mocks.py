import pytest

from app.models import RetryTask


@pytest.fixture()
def apply_wasabi_patches(monkeypatch, mock_europa_request, redis_retry_pretty_fix, retailer_fixture, europa_response):
    def patchit():
        monkeypatch.setattr("app.agents.acteol.get_task", lambda *_: RetryTask(request_data={"ctcid": "ctcid"}))

    return patchit
