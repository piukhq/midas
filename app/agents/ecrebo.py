import enum

from uuid import uuid4
import requests
import arrow

from app.agents.base import ApiMiner


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

    def register(self, credentials):
        resp = requests.post(
            f"{BASE_URL}/v1/list/append_item/{RETAILER_ID}/assets/membership",
            json={
                "data": {
                    "email": credentials["email"],
                    "validated": True,
                    "first_name": credentials["first_name"],
                    "surname": credentials["last_name"],
                    "join_date": arrow.utcnow().format("YYYY-MM-DD"),
                    "email_marketing": credentials["email_marketing"],
                    "source": "channel",
                }
            },
            headers=self._make_headers(self._authenticate()),
        )

        if resp.status_code == 409:  # user already exists
            # we have to parse the error message to get the user ID out
            merchant_identifier = resp.json()["message"][-37:-1]
        else:
            resp.raise_for_status()
            merchant_identifier = resp.json()["publisher"][0]["message"].split(":")[1]

        self.identifier = {"merchant_identifier": merchant_identifier}
        self.user_info["credentials"]["merchant_identifier"] = merchant_identifier

    def login(self, credentials):
        self.uuid = credentials["merchant_identifier"]

    def balance(self):
        resp = requests.get(
            f"{BASE_URL}/v1/list/query_item/{RETAILER_ID}/assets/membership/uuid/{self.uuid}",
            headers=self._make_headers(self._authenticate()),
        )
        resp.raise_for_status()

        rewards = resp.json()["data"]["membership_data"]["rewards"]

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

        return {
            "points": rewards["balance"],
            "value": 0,
            "value_label": "",
            "vouchers": [
                {"type": VoucherType.ACCUMULATOR.value, "value": rewards["balance"], "target_value": rewards["goal"]},
                *[_voucher_from_json(voucher) for voucher in rewards["vouchers"]],
            ],
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
