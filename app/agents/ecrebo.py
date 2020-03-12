from decimal import Decimal
from uuid import uuid4
import typing as t
import enum
import time

import arrow
import requests

from app import constants
from app.configuration import Configuration
from app.agents.base import ApiMiner
from app.agents.exceptions import LoginError, RegistrationError, STATUS_LOGIN_FAILED, ACCOUNT_ALREADY_EXISTS


@enum.unique
class VoucherType(enum.Enum):
    JOIN = 0
    ACCUMULATOR = 1
    STAMPS = 2


class Ecrebo(ApiMiner):
    def __init__(self, retry_count, user_info, scheme_slug=None):
        config = Configuration(scheme_slug, Configuration.JOIN_HANDLER)
        self.base_url = config.merchant_url
        self.auth = config.security_credentials["outbound"]["credentials"][0]["value"]
        super().__init__(retry_count, user_info, scheme_slug=scheme_slug)

    def _authenticate(self):
        """
        Returns an Ecrebo API auth token to use in subsequent requests.
        """
        resp = requests.post(
            f"{self.base_url}/v1/auth/login", json={"name": self.auth["username"], "password": self.auth["password"]}
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def _make_headers(self, token):
        return {"Token": token, "Audit-Tag": str(uuid4())}

    def _get_card_number_and_uid(self, message):
        card_number, uid, *_ = message.split(":")
        return card_number, uid

    def _get_membership_data(self, endpoint: str) -> dict:
        url = f"{self.base_url}{endpoint}"
        headers = self._make_headers(self._authenticate())

        # TODO: this retry loop can be removed when Ecrebo finish making their API synchronous.
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
        consents = {c["slug"]: c["value"] for c in credentials.get("consents", {})}
        resp = requests.post(
            f"{self.base_url}/v1/list/append_item/{self.RETAILER_ID}/assets/membership",
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

    def login(self, credentials):
        self.credentials = credentials

        if "merchant_identifier" not in credentials:
            endpoint = f"/v1/list/query_item/{self.RETAILER_ID}/assets/membership/token/{credentials['card_number']}"
            membership_data = self._get_membership_data(endpoint)

            # TODO: do we actually need all three of these
            self.credentials["merchant_identifier"] = membership_data["uuid"]
            self.identifier = {"merchant_identifier": membership_data["uuid"]}
            self.user_info["credentials"].update(self.identifier)

    def _make_issued_voucher(self, voucher_type: VoucherType, json: dict, target_value: Decimal) -> dict:
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
        self, voucher_type: VoucherType, value: Decimal, target_value: Decimal, issued_vouchers: t.List[dict]
    ) -> dict:
        return {
            "points": value,
            "value": value,
            "value_label": "",
            "vouchers": [
                {"type": voucher_type.value, "value": value, "target_value": target_value},
                *[self._make_issued_voucher(voucher_type, voucher, target_value) for voucher in issued_vouchers],
            ],
        }

    def _accumulator_balance(self, json: dict) -> dict:
        value = Decimal(json["config"]["pot_total"]) / 5
        target_value = Decimal(json["config"]["pot_goal"]) / 5
        issued_vouchers = json["vouchers"]
        return self._make_balance_response(VoucherType.ACCUMULATOR, value, target_value, issued_vouchers)

    def _stamps_balance(self, json: dict) -> dict:
        value = Decimal(json["stamps"])
        target_value = Decimal(json["stamp_goal"])
        issued_vouchers = json["vouchers"]
        return self._make_balance_response(VoucherType.STAMPS, value, target_value, issued_vouchers)

    def balance(self):
        endpoint = (
            f"/v1/list/query_item/{self.RETAILER_ID}/assets/membership/uuid/{self.credentials['merchant_identifier']}"
        )
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

        campaign_type = rewards["type"]

        if campaign_type == "thresholdmarketing":
            return self._accumulator_balance(rewards)
        elif campaign_type == "punchcard":
            return self._stamps_balance(rewards)
        else:
            raise ValueError(f"Unsupported Ecrebo campaign type: {campaign_type}")

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []


class FatFace(Ecrebo):
    RETAILER_ID = "94"

    def _get_registration_credentials(self, credentials: dict, consents: dict) -> dict:
        return {
            "email": credentials[constants.EMAIL],
            "first_name": credentials[constants.FIRST_NAME],
            "surname": credentials[constants.LAST_NAME],
            "join_date": arrow.utcnow().format("YYYY-MM-DD"),
            "email_marketing": consents["email_marketing"],
            "source": "channel",
            "validated": True,
        }


class BurgerKing(Ecrebo):
    RETAILER_ID = "95"

    def _get_registration_credentials(self, credentials: dict, consents: dict) -> dict:
        return {
            "email": credentials[constants.EMAIL],
            "first_name": credentials[constants.FIRST_NAME],
            "last_name": credentials[constants.LAST_NAME],
            "postcode": credentials[constants.POSTCODE],
            "phone": credentials[constants.PHONE],
            "validated": True,
        }
