from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError, UNKNOWN
from decimal import Decimal


class JetBlue(RoboBrowserMiner):
    def login(self, credentials):
        form = 'https://prd.b6prdeng.net/iam/login'
        self.open_url(
            form,
            method='post',
            json={
                'id': credentials['email'],
                'pwd': credentials['password']
            })

        json = self.browser.response.json()

        if 'error' in json:
            if json['error']['code'] == 'JB_INVALID_CREDENTIALS':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

    def balance(self):

        return {
            'points': Decimal(self.browser.response.json()['points']),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
