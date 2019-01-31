import json
import time
from decimal import Decimal

import arrow

from app.agents.base import ApiMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED


class Enterprise(ApiMiner):
    connect_timeout = 10

    def login(self, credentials):
        form = (
            'https://prd-east.webapi.enterprise.co.uk'
            '/enterprise-ewt/enterprise/profile/login/EP'
            '?locale=en_GB'
            '&{}'.format(int(time.time()))
        )
        self.response = self.make_request(
            form,
            method='post',
            json={
                'username': credentials['username'],
                'password': credentials['password']
            })

        self.account_data = json.loads(self.response.text)

        if self.account_data['messages'] and len(self.account_data['messages']):
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
