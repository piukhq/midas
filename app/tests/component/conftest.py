from urllib.parse import urljoin

import pytest
from soteria.configuration import Configuration
import settings
import json


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


@pytest.fixture()
def mock_itsu_endpoints(http_pretty_mock):
    def mocks(test, customer_details_response_body, customer_details_response_status):
        mocks_dict = {
            "mock_find_customer_details": http_pretty_mock(
                urljoin(test.MERCHANT_URL, "api/Customer/FindCustomerDetails"),
                customer_details_response_status,
                customer_details_response_body,
            ),
            "mock_customer_patch": http_pretty_mock(
                urljoin(test.MERCHANT_URL, "api/Customer/Patch"),
                customer_details_response_status,
                customer_details_response_body,
            ),
        }
