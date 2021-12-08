from decimal import Decimal
from typing import Optional

from soteria.configuration import Configuration
from user_auth_token import UserTokenStore

import settings
from app.agents.base import ApiMiner, Balance
from app.reporting import get_logger
from app.scheme_account import TWO_PLACES
from uuid import uuid4
from app.encryption import hash_ids

log = get_logger("iceland")


class Iceland(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        self.config = Configuration(
            scheme_slug,
            Configuration.JOIN_HANDLER,
            settings.VAULT_URL,
            settings.VAULT_TOKEN,
            settings.CONFIG_SERVICE_URL,
        )
        self.credentials = user_info["credentials"]
        self.base_url = self.config.merchant_url
        self.auth = self.config.security_credentials["outbound"]["credentials"][0]["value"]
        self.token_store = UserTokenStore(settings.REDIS_URL)
        self.token = {}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    def login(self, credentials):
        url = f"{self.base_url}validate"
        payload = {
            "card_number": credentials["card_number"],
            "last_name": credentials["card_number"],
            "postcode": credentials["card_number"],
            "message_uid": str(uuid4()),
            "record_uid": self.record_uid,
            "callback_url": self.config.callback_url,
            "merchant_scheme_id1": hash_ids.encode(sorted(map(int, self.user_info["user_set"].split(",")))[0]),
            "merchant_scheme_id2": credentials.get("merchant_identifier"),
        }
        self.result = self.make_request(url, method="post", json=payload)

    def balance(self) -> Optional[Balance]:
        value = Decimal(self.result["balance"]).quantize(TWO_PLACES)
        return Balance(
            points=value,
            value=value,
            value_label="£{}".format(value),
        )
