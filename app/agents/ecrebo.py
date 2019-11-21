from decimal import Decimal
from uuid import uuid4
import enum
import time

import arrow
import requests

from app.agents.base import ApiMiner
from app.utils import JourneyTypes


@enum.unique
class VoucherType(enum.Enum):
    JOIN = 0
    ACCUMULATOR = 1


BASE_URL = "https://london-capi-test.ecrebo.com:2361"
RETAILER_ID = "94"


class Ecrebo(ApiMiner):
    def _authenticate(self):
        """
        Returns an Ecrebo API auth token to use in subsequent requests.
        """
        resp = requests.post(
            f"{BASE_URL}/v1/auth/login", json={"name": "fatface_external_staging", "password": "c5tzCv5ms2k8eFR6"}
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def _make_headers(self, token):
        return {"Token": token, "Audit-Tag": str(uuid4())}

    def _get_card_number_and_uid(self, message):
        card_number, uid, *_ = message.split(":")
        return card_number, uid

    def register(self, credentials):
        consents = {c["slug"]: c["value"] for c in credentials["consents"]}
        resp = requests.post(
            f"{BASE_URL}/v1/list/append_item/{RETAILER_ID}/assets/membership",
            json={
                "data": {
                    "email": credentials["email"],
                    "validated": True,
                    "first_name": credentials["first_name"],
                    "surname": credentials["last_name"],
                    "join_date": arrow.utcnow().format("YYYY-MM-DD"),
                    "email_marketing": consents["email_marketing"],
                    "source": "channel",
                }
            },
            headers=self._make_headers(self._authenticate()),
        )

        if resp.status_code == 409:  # user already exists
            # we have to parse the error message to get the user ID out
            message = resp.json()["message"]
            paren_idx = message.rindex("(")
            message = message[paren_idx + 1 : -1]
        else:
            resp.raise_for_status()
            message = resp.json()["publisher"][0]["message"]

        card_number, uid = self._get_card_number_and_uid(message)

        self.identifier = {"card_number": card_number, "merchant_identifier": uid}
        self.user_info["credentials"]["merchant_identifier"] = uid

    def login(self, credentials):
        self.uuid = credentials["merchant_identifier"]

    def balance(self):
        attempts = 5
        while attempts > 0:
            attempts -= 1
            resp = requests.get(
                f"{BASE_URL}/v1/list/query_item/{RETAILER_ID}/assets/membership/uuid/{self.uuid}",
                headers=self._make_headers(self._authenticate()),
            )

            try:
                resp.raise_for_status()
                rewards = resp.json()["data"]["membership_data"]["rewards"]
            except (requests.RequestException, KeyError):
                if attempts == 0:
                    raise
                else:
                    time.sleep(3)
            else:
                break

        # if we got this far without crashing, and the journey type is "link"...
        # then we are doing the first valid balance update since the join first occurred.
        # in this case, we must tell hermes to set the join date, not the link date.
        # if we just set the create journey to "join", hermes will set the card to pending,
        # and then attempt to get a balance update. i added the "join-with-balance" identifier
        # to allow hermes to simply set the join date, and stop there.
        if self.journey_type == JourneyTypes.LINK:
            self.create_journey = "join-with-balance"

        def _voucher_type_from_reason(reason: str) -> str:
            return {"EARN": VoucherType.ACCUMULATOR.value, "JOIN": VoucherType.JOIN.value}[reason]

        def _voucher_from_json(json):
            voucher = {
                "type": _voucher_type_from_reason(json["reason"]),
                "issue_date": arrow.get(json["issued"], "YYYY-MM-DD").timestamp,
                "code": json["code"],
            }

            if "redeemed" in json:
                voucher["redeem_date"] = json["redeemed"]

            return voucher

        value = Decimal(rewards["balance"]) / 5
        return {
            "points": value,
            "value": value,
            "value_label": "",
            "vouchers": [
                {
                    "type": VoucherType.ACCUMULATOR.value,
                    "value": Decimal(rewards["balance"]) / 5,
                    "target_value": Decimal(rewards["goal"]) / 5,
                },
                *[_voucher_from_json(voucher) for voucher in rewards["vouchers"]],
            ],
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
