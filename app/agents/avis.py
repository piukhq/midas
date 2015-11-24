from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
from urllib.parse import urlsplit
import arrow


class Avis(Miner):
    def login(self, credentials):
        query = 'https://www.avis.co.uk/loyalty-statement'
        data = {
            'require-login': 'true',
            'login-email': credentials['email'],
            'login-hidtext': credentials['password'],
        }

        self.open_url(query, method='post', data=data)

        parts = urlsplit(self.browser.url)
        if getattr(parts, 'query').startswith('require-login=true'):
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        value = extract_decimal(self.browser.select('.loyal-spend-text p strong')[1].text)
        return {
            'points': extract_decimal(self.browser.select('.loyal-spend-text p strong')[0].text),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
