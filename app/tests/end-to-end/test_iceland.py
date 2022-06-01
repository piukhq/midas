import json
from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, mock
from unittest.mock import ANY, MagicMock, call
import responses

import arrow
import httpretty
import requests

import settings
from app.encryption import AESCipher, get_aes_key
from app.urls import api
from flask import Flask
from flask_testing import TestCase as FlaskTestCase
from requests import Response
from soteria.configuration import Configuration

from app.agents.base import Balance, BaseAgent
from app.agents.exceptions import (
    CARD_NUMBER_ERROR,
    NO_SUCH_RECORD,
    SERVICE_CONNECTION_ERROR,
    AgentError,
    JoinError,
    LoginError,
    errors,
)
from app.agents.iceland import Iceland
from app.agents.schemas import Transaction
from app.api import create_app
from app.journeys.common import agent_login
from app.journeys.join import agent_join
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes, SchemeAccountStatus
from app.security.rsa import RSA
from app.tasks.resend_consents import ConsentStatus
from app.tests.unit.fixtures.rsa_keys import PRIVATE_KEY, PUBLIC_KEY

encrypted_credentials = (
    AESCipher(get_aes_key("aes-keys"))
    .encrypt(
        json.dumps({"card_number": "6332040030541927282", "last_name": "Gouws", "postcode": "kt130bz", "consents": []})
    )
    .decode("utf-8")
)

europa_config_add = {
    "id": 101,
    "merchant_id": "iceland-bonus-card",
    "merchant_url": "http://127.0.0.1:6502/mock/api/v1/bink/link",
    "handler_type": 2,
    "integration_service": 0,
    "callback_url": None,
    "retry_limit": 0,
    "log_level": 0,
    "country": "GB",
    "security_credentials": {
        "inbound": {"service": 1, "credentials": []},
        "outbound": {
            "service": 1,
            "credentials": [
                {
                    "credential_type": "compound_key",
                    "storage_key": "887a96f3cebfa598b459bafc39653c9bc5cd5597a7b00eb55b9011380cc7d719",
                }
            ],
        },
    },
}


class TestIcelandAdd(FlaskTestCase):
    def create_app(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        api.init_app(app)
        return app

    # @responses.activate
    def test_add_journey_success(self):
        # Europa config
        # responses.add(responses.GET, settings.CONFIG_SERVICE_URL + "/configuration", json=europa_config_add, status=200)
        parameters = {
            "scheme_account_id": 159779,
            "credentials": encrypted_credentials,
            "user_set": "40776",
            "status": 1001,
            "journey_type": 1,
        }
        headers = {"transaction": "ad6d704c-e0c7-11ec-929b-acde48001122", "User-agent": "Hermes on C02DK4ZLMD6M"}
        self.client.get("/iceland-bonus-card/balance", headers=headers, query_string=parameters)
        pass
