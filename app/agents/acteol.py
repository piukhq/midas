import enum
import json
import time
from decimal import Decimal
from typing import Dict, List
from uuid import uuid4

import arrow
import requests
from app.agents.base import ApiMiner
from app.agents.exceptions import (
    ACCOUNT_ALREADY_EXISTS,
    STATUS_LOGIN_FAILED,
    LoginError,
    RegistrationError,
)
from app.configuration import Configuration
from gaia.user_token import UserTokenStore
from settings import REDIS_URL, logger


@enum.unique
class VoucherType(enum.Enum):
    JOIN = 0
    ACCUMULATOR = 1
    STAMPS = 2


class Acteol(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.token_store = UserTokenStore(REDIS_URL)
        self.retry_limit = 9  # tries 10 times overall
        self.token = {}
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    # TODO: these 3 are from cooperative
    def _token_is_valid(self, token: Dict) -> bool:
        current_timestamp = arrow.utcnow().timestamp
        return (current_timestamp - token["timestamp"]) < self.AUTH_TOKEN_TIMEOUT

    def _refresh_access_token(self, scheme_id: int, credentials: Dict) -> Dict:
        """
        Returns an Acteol API auth token to use in subsequent requests.
        """
        payload = {
            "grant_type": "password",
            "username": credentials["email"],
            "password": credentials["password"],
        }
        token_url = f"{self.base_url}/token"
        resp = requests.post(token_url, data=payload)
        resp.raise_for_status()
        token = resp.json()["access_token"]

        return token

    def _make_headers(self, token):
        # application/x-www-form-urlencoded
        return {"Token": token, "Audit-Tag": str(uuid4())}

    def _get_card_number_and_uid(self, message):
        card_number, uid, *_ = message.split(":")
        return card_number, uid

    def _get_membership_data(self, endpoint: str) -> Dict:
        url = f"{self.base_url}{endpoint}"
        headers = self._make_headers(self._authenticate())

        # TODO: this retry loop can be removed when Acteol finish making their API synchronous.
        attempts = 5
        while attempts > 0:
            attempts -= 1

            resp = requests.get(url, headers=headers)

            try:
                resp.raise_for_status()
                return resp.json()["data"]
            except requests.HTTPError as ex:
                if ex.response.status_code == 404:
                    raise LoginError(STATUS_LOGIN_FAILED)
                else:
                    raise  # base agent will convert this to an unknown error
            except (requests.RequestException, KeyError):
                # non-http errors will be retried a few times
                if attempts == 0:
                    raise
                else:
                    time.sleep(3)
            else:
                break

    def register(self, credentials):
        # TODO: this /token URL is almost certainly wrong
        consents = {c["slug"]: c["value"] for c in credentials.get("consents", {})}
        registration_url = f"{self.base_url}/token"
        resp = requests.post(
            registration_url,
            json={"data": self._get_registration_credentials(credentials, consents)},
            headers=self._make_headers(self._authenticate()),
        )

        if resp.status_code == 409:
            raise RegistrationError(ACCOUNT_ALREADY_EXISTS)
        else:
            resp.raise_for_status()
            json = resp.json()
            message = json["publisher"][0]["message"]

        card_number, uid = self._get_card_number_and_uid(message)

        self.identifier = {"card_number": card_number, "merchant_identifier": uid}
        self.user_info["credentials"].update(self.identifier)

    def _store_token(self, acteol_access_token):
        current_timestamp = arrow.utcnow().timestamp
        token = {"token": acteol_access_token, "timestamp": current_timestamp}
        self.token_store.set(self.scheme_id, json.dumps(token))

        return token

    def login(self, credentials):
        """
        get token from redis if we have one, otherwise login to get one and store in cache
        """
        have_valid_token = False  # Assume no good token to begin with
        try:
            token = json.loads(self.token_store.get(self.scheme_id))
            try:  # Token may be in bad format and needs refreshing
                if self._token_is_valid(token=token):
                    have_valid_token = True
                    self.token = token
            except (KeyError, TypeError) as e:
                logger.exception(e)
        except (KeyError, self.token_store.NoSuchToken):
            pass  # have_token is still False

        if not have_valid_token:
            acteol_access_token = self._refresh_access_token(
                scheme_id=self.scheme_id, credentials=credentials
            )
            token = self._store_token(acteol_access_token)
            self.token = token

    def _make_issued_voucher(
        self, voucher_type: VoucherType, json: dict, target_value: Decimal
    ) -> dict:
        voucher = {
            "type": voucher_type.value,
            "issue_date": arrow.get(json["issued"], "YYYY-MM-DD").timestamp,
            "expiry_date": arrow.get(json["expiry_date"], "YYYY-MM-DD").timestamp,
            "code": json["code"],
            "value": target_value,
            "target_value": target_value,
        }

        if "redeemed" in json:
            voucher["redeem_date"] = arrow.get(json["redeemed"], "YYYY-MM-DD").timestamp

        return voucher

    def _make_balance_response(
        self,
        voucher_type: VoucherType,
        value: Decimal,
        target_value: Decimal,
        issued_vouchers: List[dict],
    ) -> dict:
        return {
            "points": value,
            "value": value,
            "value_label": "",
            "vouchers": [
                {
                    "type": voucher_type.value,
                    "value": value,
                    "target_value": target_value,
                },
                *[
                    self._make_issued_voucher(voucher_type, voucher, target_value)
                    for voucher in issued_vouchers
                ],
            ],
        }

    def _accumulator_balance(self, json: dict) -> dict:
        value = Decimal(json["config"]["pot_total"]) / 5
        target_value = Decimal(json["config"]["pot_goal"]) / 5
        issued_vouchers = json["vouchers"]
        return self._make_balance_response(
            VoucherType.ACCUMULATOR, value, target_value, issued_vouchers
        )

    def _stamps_balance(self, json: dict) -> dict:
        value = Decimal(json["config"]["stamps"])
        target_value = Decimal(json["config"]["stamps_goal"])
        issued_vouchers = json["vouchers"]
        return self._make_balance_response(
            VoucherType.STAMPS, value, target_value, issued_vouchers
        )

    def balance(self):
        merchant_identifier = self.credentials['merchant_identifier']
        endpoint = f"/v1/list/query_item/{self.RETAILER_ID}/assets/membership/uuid/{merchant_identifier}"
        rewards = self._get_membership_data(endpoint)["membership_data"]
        # sometimes this data is in a sub-object called "rewards", so use that if it's present.
        if "rewards" in rewards:
            rewards = rewards["rewards"]

        # if we got this far without crashing, and the journey type is "link"...
        # then we are doing the first valid balance update since the join first occurred.
        # in this case, we must tell hermes to set the join date, not the link date.
        # if we just set the create journey to "join", hermes will set the card to pending,
        # and then attempt to get a balance update. i added the "join-with-balance" identifier
        # to allow hermes to simply set the join date, and stop there.
        if self.user_info.get("from_register") is True:
            self.create_journey = "join-with-balance"

        campaign_type = rewards["type"].strip()

        if campaign_type == "thresholdmarketing":
            return self._accumulator_balance(rewards)
        elif campaign_type == "punchcard":
            return self._stamps_balance(rewards)
        else:
            raise ValueError(f"Unsupported Acteol campaign type: {campaign_type}")

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
