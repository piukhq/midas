import json
from decimal import Decimal
from http import HTTPStatus
from unittest import TestCase, mock
from unittest.mock import ANY, MagicMock, call
import responses

import arrow
import httpretty
import requests
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


class TestIcelandAdd(TestCase):

    def create_app(self):
        return create_app(
            self,
        )
