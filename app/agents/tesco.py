import json
from decimal import Decimal

import arrow
import requests

import settings
from app.agents.base import ApiMiner
from app.agents.exceptions import UNKNOWN, AgentError, LoginError, errors
from app.encryption import AESCipher
from app.utils import TWO_PLACES


class Tesco(ApiMiner):
    is_login_successful = False

    @staticmethod
    def encrypt_credentials(credentials: dict) -> str:
        aes = AESCipher(settings.AES_KEY.encode())
        return aes.encrypt(json.dumps(credentials)).decode()

    def login(self, credentials):
        url = "".join(
            [
                settings.AGENT_PROXY_URL,
                "/agent_proxy/account_balance/tesco-clubcard",
                "?credentials=",
                self.encrypt_credentials(credentials),
            ]
        )

        resp = requests.get(
            url,
            headers={
                "Authorization": "Token {}".format(settings.SERVICE_API_KEY)
            },
        )
        self.account_data = resp.json()

        if not self.account_data["success"]:
            for name, args in errors.items():
                if args["code"] == resp.status_code:
                    raise LoginError(name)
            else:
                raise AgentError(UNKNOWN)

        self.is_login_successful = True

    def balance(self):
        points_balance = self.account_data["balance"]["points"]
        value = Decimal(points_balance["value"]).quantize(TWO_PLACES)
        return {
            "points": Decimal(points_balance["points"]),
            "value": value,
            "balance": Decimal(points_balance["balance"]),
            "value_label": "£{}".format(value),
            "reward_tier": points_balance["reward_tier"],
        }

    @staticmethod
    def parse_transaction(row):
        return {
            "date": arrow.get(row["date"]),
            "description": row["description"],
            "points": Decimal(row["points"]),
            "value": Decimal(row["value"]),
            "location": row["location"],
        }

    def scrape_transactions(self):
        return self.account_data["balance"]["transactions"]
