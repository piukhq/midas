from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from decimal import Decimal


class Showcase(RoboBrowserMiner):
    is_login_successful = False
    json_response = None

    def check_if_logged_in(self):
        self.json_response = self.browser.response.json()

        if self.json_response['StatusCode'] == 200:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        url = "https://www.showcasecinemas.co.uk/umbraco/surface/loyalty/login"
        model = {
            "Email": credentials['email'],
            "Password": credentials['password']
        }
        self.browser.open(url, method="post", json=model)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        points = self.json_response['MemberDetails']['Balances'][0]['Total']

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
