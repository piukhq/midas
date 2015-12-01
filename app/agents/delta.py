from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow


class Delta(Miner):
    dashboard_data = {}

    def login(self, credentials):
        url = 'https://www.delta.com/custlogin/login.action'
        data = {
            'loginpath': '//www.delta.com',
            'usernameType': 'skymiles',
            'passwordType': 'PW',
            'homePg': '',
            'refreshURL': '/acctactvty/myskymiles.action',
            'username': credentials['username'],
            'password': credentials['password'],
            'rememberMe': 'true',
            'BAUParams': '',
            'formNameSubmitted': 'LoginPage',
            'fromapp': '',
            'usernm': credentials['username'],
            'rememberme': 'on',
            'pwd': credentials['password'],
            'errorMsg': '',
            'Submit': '',
        }

        self.open_url(url, data=data, method='post')

        self.open_url('https://www.delta.com/custlogin/getDashBrdData.action', method='post')
        self.dashboard_data = self.browser.response.json()

        if not self.dashboard_data['authenticated']:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        return {
            'points': Decimal(self.dashboard_data['smBalance']),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://www.delta.com/acctactvty/manageacctactvty.action')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
