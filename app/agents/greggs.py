from app.agents.base import Miner
from app.agents.exceptions import LoginError, PASSWORD_EXPIRED, UNKNOWN, STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow


class Greggs(Miner):
    access_details = {}

    def login(self, credentials):
        self.browser.open('https://api.greggs.co.uk/1.0/user/login', method='post', json=credentials)
        response = self.browser.response.json()

        if 'error' in response:
            if response['error_description'] == 'Migrated user':
                raise LoginError(PASSWORD_EXPIRED)
            elif response['error_description'] == 'Invalid username and password combination':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)
        # this is likely (but perhaps not necessarily?) going to be invalid credentials.
        # this could mean to long/short password, or no capital letters, or something like that.
        elif 'status' in response:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.headers['Authorization'] = 'Bearer {}'.format(response['access_token'])

    def balance(self):
        self.open_url('https://api.greggs.co.uk/1.0/wallet')
        response = self.browser.response.json()

        stamp_details = next(x for x in response['results'] if x['type'] == 'STAMP')
        debit_details = next(x for x in response['results'] if x['type'] == 'DEBIT')

        points = stamp_details['balance']['points']

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '{}/7 coffees'.format(points),
            'balance': Decimal(debit_details['balance']['available']) / 100,
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'YYYY-MM-DD hh:mm:ss'),
            'description': 'PURCHASE',
            'points': Decimal('1'),
            'value': Decimal(row['value']) / 100,
        }

    def scrape_transactions(self):
        self.open_url('https://api.greggs.co.uk/1.0/wallet/receipts')
        receipts = self.browser.response.json()

        # returns transactions that do not represent in-store purchases. we may need this in the future.
        # self.open_url('https://api.greggs.co.uk/1.0/wallet/transactions')
        # transactions = self.browser.response.json()

        data = [{
                'date': x['transactionDate'],
                'value': x['total'],
                } for x in receipts['results']]

        return data
