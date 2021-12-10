from decimal import Decimal
from typing import Optional
from uuid import uuid4

import requests
import sentry_sdk
import requests
from soteria.configuration import Configuration
from tenacity import retry, stop_after_attempt, wait_exponential

import settings
from app.agents.base import ApiMiner, Balance
from app.agents.exceptions import (
    CARD_NOT_REGISTERED,
    CARD_NUMBER_ERROR,
    CONFIGURATION_ERROR,
    GENERAL_ERROR,
    LINK_LIMIT_EXCEEDED,
    SERVICE_CONNECTION_ERROR,
    STATUS_LOGIN_FAILED,
    AgentError,
)
from app.encryption import hash_ids
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES, JourneyTypes

RETRY_LIMIT = 3
log = get_logger("iceland")


JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING = {
    JourneyTypes.JOIN: Configuration.JOIN_HANDLER,
    JourneyTypes.LINK: Configuration.VALIDATE_HANDLER,
    JourneyTypes.ADD: Configuration.VALIDATE_HANDLER,
    JourneyTypes.UPDATE: Configuration.UPDATE_HANDLER,
}


class Iceland(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)
        handler_type = JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]]
        self.config = Configuration(
            scheme_slug,
            handler_type,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.security_credentials = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self._balance_amount = 0.0
        self.errors = {
            STATUS_LOGIN_FAILED: "VALIDATION",
            CARD_NUMBER_ERROR: "CARD_NUMBER_ERROR",
            LINK_LIMIT_EXCEEDED: "LINK_LIMIT_EXCEEDED",
            CARD_NOT_REGISTERED: "CARD_NOT_REGISTERED",
            GENERAL_ERROR: "GENERAL_ERROR",
        }

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _get_oauth_token(self) -> str:
        url = self.security_credentials["url"]
        payload = {
            "grant_type": "client_credentials",
            "client_secret": self.security_credentials["payload"]["client_secret"],
            "client_id": self.security_credentials["payload"]["client_id"],
            "resource": self.security_credentials["payload"]["resource"],
        }

        try:
            response = requests.post(url, data=payload)
        except requests.RequestException as e:
            sentry_sdk.capture_message(f"Failed request to get oauth token from {url}. exception: {e}")
            raise AgentError(SERVICE_CONNECTION_ERROR) from e
        except (KeyError, IndexError) as e:
            raise AgentError(CONFIGURATION_ERROR) from e

        return response.json()["access_token"]

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _login(self, payload):
        return self.make_request(url=self.config.merchant_url, method="post", json=payload)

    def login(self, credentials) -> None:
        token = self._get_oauth_token()
        payload = {
            "card_number": credentials["card_number"],
            "last_name": credentials["last_name"],
            "postcode": credentials["postcode"],
            "message_uid": str(uuid4()),
            "record_uid": hash_ids.encode(self.scheme_id),
            "callback_url": self.config.callback_url,
            "merchant_scheme_id1": hash_ids.encode(sorted(map(int, self.user_info["user_set"].split(",")))[0]),
            "merchant_scheme_id2": credentials.get("merchant_identifier"),
        }
        self.headers = {"Authorization": f"Bearer {token}"}

        response = self._login(payload)
        response_json = response.json()

        error = response_json.get("error_codes")
        if error:
            self.handle_errors(error[0]["code"])

        self.identifier = {
            "barcode": response_json.get("barcode"),
            "card_number": response_json.get("card_number"),
            "merchant_identifier": response_json.get("merchant_scheme_id2"),
        }
        self.user_info["credentials"].update(self.identifier)

        self._balance_amount = response_json["balance"]

    def balance(self) -> Optional[Balance]:
        amount = Decimal(self._balance_amount).quantize(TWO_PLACES)
        return Balance(
            points=amount,
            value=amount,
            value_label="£{}".format(amount),
        )
