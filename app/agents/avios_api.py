from urllib.parse import urlencode
from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import LoginError, UNKNOWN, STATUS_LOGIN_FAILED


class Avios(Miner):
    loyalty_data = {}

    def login(self, credentials):
        url = 'https://api.avios.com/test/v1/programmes/ATRP/accounts/{0}'.format(credentials['card_number'])
        query = {
            'date-of-birth': credentials['date_of_birth'],
            'family-name': credentials['last_name'],
            'api_key': 'gra5b3qbkc4zphy8jxarrq43',
        }

        self.headers['Accept'] = 'application/json'

        self.browser.open('{0}?{1}'.format(url, urlencode(query)))
        resp = self.browser.response.json()

        if self.browser.response.status_code >= 500:
            error_code = resp['error']['code']
            if error_code == 'ACCOUNT_NOT_FOUND':
                raise LoginError(STATUS_LOGIN_FAILED)
            elif error_code == 'CUSTOMER_DETAILS_INVALID':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

        self.loyalty_data = resp

    def balance(self):
        return {
            'points': Decimal(self.loyalty_data['loyaltyProgramAccount']['balance']['amount']),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return None

    def scrape_transactions(self):
        return None
