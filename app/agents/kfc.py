from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError, UNKNOWN

# TODO: add STATUS_ACCOUNT_LOCKED


class Kfc(Miner):
    def login(self, credentials):
        data = {"password": credentials["password"],
                "username": credentials["user_name"],
                "grant_type": "password",
                "client_id": "14_1ympi31f1tk0kco8kkc4cko48gg804csowcs4g4w4ckco80w0k"}

        self.browser.open("https://www.kfc.co.uk/ccapi/oauth/v2/token", method='post', json=data)

        if self.browser.response.status_code != 200:
            if self.browser.response.json().get('error') == 'invalid_grant':
                raise LoginError(STATUS_LOGIN_FAILED)
            raise LoginError(UNKNOWN)

        access_token = self.browser.response.json()["access_token"]
        self.headers = {"Authorization": "Bearer {0}".format(access_token)}

    def balance(self):
        self.open_url("https://www.kfc.co.uk/ccapi/api/me?scope=user_full,card_full,account_full")
        return {
            "amount": Decimal(self.browser.response.json()["_embedded"]["cards"][0]["_embedded"]["account"]["balance"])
        }

    def transactions(self):
        return None
