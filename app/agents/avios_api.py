from urllib.parse import urlencode
from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import LoginError, UNKNOWN, STATUS_LOGIN_FAILED
from app import sentry
import arrow


class Avios(Miner):

    def __init__(self, retry_count, scheme_id):
        super().__init__(retry_count, scheme_id)
        self.faking_login = False
        self.loyalty_data = {}

    def login(self, credentials):
        if 'card_number' not in credentials:
            sentry.captureMessage('No card_number in Avios agent! Check the card_number_regex on Hermes.')
            self.faking_login = True
            return

        url = 'https://api.avios.com/v1/programmes/ATRP/accounts/{0}'.format(credentials['card_number'])
        query = {
            'date-of-birth': arrow.get(credentials['date_of_birth'], 'DD/MM/YYYY').format('YYYY-MM-DD'),
            'family-name': credentials['last_name'],
            'api_key': 'snkd3k4pvr5agqeeprs7ytqp',
        }

        self.headers['Accept'] = 'application/json'
        self.headers['X-Forward-For'] = '172.128.25.24'

        self.browser.open('{0}?{1}'.format(url, urlencode(query)))
        resp = self.browser.response.json()

        if self.browser.response.status_code >= 500:
            error_code = resp['error']['code']
            if error_code == 'ACCOUNT_NOT_FOUND':
                raise LoginError(STATUS_LOGIN_FAILED)
            elif error_code == 'CUSTOMER_DETAILS_INVALID':
                raise LoginError(STATUS_LOGIN_FAILED)
            elif error_code == 'REQUEST_INVALID':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

        self.loyalty_data = resp

    def balance(self):
        if self.faking_login:
            return None

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

    @staticmethod
    def update_questions(questions):
        # TODO: use the given credentials to obtain the refresh token.
        return {
            'api_key': 'test-api-key'
        }
