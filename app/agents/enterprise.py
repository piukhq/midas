from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow
import json


class Enterprise(Miner):
    def login(self, credentials):
        url = 'https://prd.webapi.enterprise.co.uk/enterprise-ewt/ecom-service/login/EP?locale=en_GB'
        login_data = {
            'username': credentials['username'],
            'password': credentials['password'],
            'remember_credentials': 'false',
        }

        self.open_url(url, method='post', json=login_data)

        self.account_data = json.loads(self.browser.response.text)

        if len(self.account_data['messages']):
            message = self.account_data['messages'][0]['message']
            if message.startswith('We') or message.startswith('Please'):
                raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        return {
            'points': Decimal(self.account_data['profile']['basic_profile']['loyalty_data']['points_to_date']),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
