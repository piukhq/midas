from decimal import Decimal
from typing import Optional
from uuid import uuid4

import requests
from soteria.configuration import Configuration
from tenacity import retry, stop_after_attempt, wait_exponential

import settings
from app.agents.base import ApiMiner, Balance
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
        handler_type = JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]]
        self.config = Configuration(
            scheme_slug,
            handler_type,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.token = ''
        self.balance = 0.0
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    @retry(
        stop=stop_after_attempt(RETRY_LIMIT),
        wait=wait_exponential(multiplier=1, min=3, max=12),
        reraise=True,
    )
    def _get_oauth_token(self) -> None:
        url = self.config.security_credentials["outbound"]["credentials"][0]["value"]["url"]
        payload = {
            "grant_type": "client_credentials",
            "client_secret": self.config.security_credentials["outbound"]["credentials"][0]["value"]["payload"][
                "client_secret"
            ],
            "client_id": self.config.security_credentials["outbound"]["credentials"][0]["value"]["payload"][
                "client_id"
            ],
        }
        resp = requests.post(url, data=payload)
        self.token = resp.json()["access_token"]

    def login(self, credentials) -> None:
        self._get_oauth_token()
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
        self.headers = {"Authorization": f"Bearer {self.token}"}
        response = self.make_request(url=f"{self.config.merchant_url}", method="post", json=payload)
        self.balance = response.json()["balance"]

    def balance(self) -> Optional[Balance]:
        amount = Decimal(self.balance).quantize(TWO_PLACES)
        return Balance(
            points=amount,
            value=amount,
            value_label="£{}".format(amount),
        )
