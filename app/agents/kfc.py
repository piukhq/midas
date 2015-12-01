from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError, UNKNOWN

# TODO: add STATUS_ACCOUNT_LOCKED


class Kfc(Miner):
    def login(self, credentials):
        data = {"password": credentials["password"],
                "username": credentials["email"],
                "grant_type": "password",
                "client_id": "14_1ympi31f1tk0kco8kkc4cko48gg804csowcs4g4w4ckco80w0k"}

        self.browser.open("https://www.kfc.co.uk/ccapi/oauth/v2/token", method='post', json=data)

        if self.browser.response.status_code != 200:
            if self.browser.response.json().get('error') == 'invalid_grant':
                raise LoginError(STATUS_LOGIN_FAILED)
            raise LoginError(UNKNOWN)

        access_token = self.browser.response.json()["access_token"]
        self.headers = {"Authorization": "Bearer {0}".format(access_token)}

    def calculate_label(self, points):
        return self.calculate_tiered_reward(points, [
            (11, '£5 off'),
            (7, 'free snack'),
            (3, 'free side'),
        ])

    def balance(self):
        self.open_url("https://www.kfc.co.uk/ccapi/api/me?scope=user_full,card_full,account_full")
        points = Decimal(self.browser.response.json()["_embedded"]["cards"][0]["_embedded"]["account"]["balance"])

        # Points are calculated on a milestone system that wraps around at 11 points.
        # We are only interested in showing what the remaining points are worth.
        points %= 11

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': self.calculate_label(points),
        }

    def scrape_transactions(self):
        return None
