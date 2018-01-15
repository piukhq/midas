from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import re


class CoffeeOne(RoboBrowserMiner):
    is_login_successful = False
    token = ''

    def check_if_logged_in(self):
        json_response = self.browser.response.json()

        for result in json_response:
            if result != 'ErrorMessage':
                self.is_login_successful = True
            else:
                self.is_login_successful = False
        if not self.is_login_successful:
            raise LoginError(STATUS_LOGIN_FAILED)

    def get_token(self):
        html_scripts = str(self.browser.select('script'))
        start_of_token = '/?token='
        end_of_token = '&pin='
        find_token = re.search('{}(.*){}'.format(
            start_of_token, end_of_token), html_scripts)
        self.token = find_token.group(1)

    def _login(self, credentials):
        self.browser.open('https://www.coffee1.co.uk/one-card/')
        self.get_token()

        url = 'https://www.coffee1.co.uk/api/loyalty/balance/{}/'.format(credentials['card-number'])
        query_string = {
            'pin': credentials['pin'],
            'token': self.token

        }

        self.browser.open(url, params=query_string)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        json_response = self.browser.response.json()
        value = json_response[0]['Balance']
        points = json_response[1]['Balance']

        return {
            'points': Decimal(points),
            'value': Decimal(value),
            'value_label': '£{}'.format(value)
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
