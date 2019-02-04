from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
from time import time


class PlayPoints(RoboBrowserMiner):
    is_login_successful = False
    point_conversion_rate = Decimal('0.01')

    def check_if_logged_in(self):
        self.browser.open('https://www.grosvenorcasinos.com')
        username = self.browser.select('p.menu-header-user-placeholder')
        if username:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        url = 'https://www.grosvenorcasinos.com/api/Login'
        data = {
            'username': credentials['username'],
            'password': credentials['password']
        }

        self.browser.open(url, method='post', data=data)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        current_timestamp = time()
        self.browser.open('https://www.grosvenorcasinos.com/api/commonServices/jitpipeline?'
                          'requests%5B0%5D%5BName%5D=GetBalancesAndRingFencedBonuses&_=' + str(current_timestamp))

        points = self.browser.response.json()['GetBalancesAndRingFencedBonuses']['Response']['TotalBalance']
        points = extract_decimal(points)
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
