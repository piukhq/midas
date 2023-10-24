import pytest
import json

# RETAILER SPECIFIC PATCHES #


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
