import httpretty
import pytest
from requests.exceptions import RetryError

from app.requests_retry import requests_retry_session


@httpretty.activate
def test_retry_session():
    httpretty.register_uri(
        method=httpretty.GET,
        uri="https://httpbin.org/get",
        responses=[httpretty.Response(body="", status=200)],
    )
    s = requests_retry_session()
    resp = s.get("https://httpbin.org/get")
    assert resp.status_code == 200


@httpretty.activate
def test_retries_on_error():
    httpretty.register_uri(
        method=httpretty.GET,
        uri="https://httpbin.org/get",
        responses=[httpretty.Response(body="", status=502)],
    )
    s = requests_retry_session(retries=3)
    with pytest.raises(RetryError):
        s.get("https://httpbin.org/get")
    assert len(httpretty.latest_requests()) == 4
