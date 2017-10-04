from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from decimal import Decimal
import arrow


class TheGardenClub(RoboBrowserMiner):
    is_login_successful = False

    def _check_if_logged_in(self):
        response = self.browser.response.json()

        if response:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        self.open_url("https://www.wyevalegardencentres.co.uk/sign-in/")

        self.headers['Host'] = "api.wyevalegardencentres.co.uk"
        self.headers['Origin'] = "https://www.wyevalegardencentres.co.uk"
        self.headers['Referer'] = "https://www.wyevalegardencentres.co.uk/sign-in/"

        data = {
            "username": credentials['email'],
            "password": credentials['password']
        }

        self.open_url("https://api.wyevalegardencentres.co.uk/v1/authentication", method="post", json=data)
        self._check_if_logged_in()
        self.login_json_response = self.browser.response.json()

    def balance(self):

        self.headers['Referer'] = "https://www.wyevalegardencentres.co.uk/my-account/"
        self.headers['Authorization'] = self.login_json_response['token']

        base_points_url = "https://api.wyevalegardencentres.co.uk/v1/users/{}/loyalty_card"
        points_url = base_points_url.format(self.login_json_response['user']['id'])

        self.open_url(points_url)

        balance_json_response = self.browser.response.json()
        points = Decimal(balance_json_response['total_points'])

        return {
            'points': points,
            'value': points,
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['created']),
            'description': str(row['transaction_number']) + " - " + str(row['total']) + row['currency'],
            'points': Decimal(row['points']),
        }

    def scrape_transactions(self):
        transaction_list = []
        self.headers['Referer'] = "https://www.wyevalegardencentres.co.uk/my-account/"
        self.headers['Authorization'] = self.login_json_response['token']

        base_transaction_url = "https://api.wyevalegardencentres.co.uk/v1/users/{}/sales"
        transaction_url = base_transaction_url.format(self.login_json_response['user']['id'])

        self.open_url(transaction_url)
        transaction_json_response = self.browser.response.json()
        transaction_list = transaction_json_response['transactions']

        return transaction_list
