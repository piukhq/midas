from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import LoginError, UNKNOWN, STATUS_LOGIN_FAILED, END_SITE_DOWN
from app.my360endpoints import SCHEME_API_DICTIONARY


class My360(Miner):
    points = None

    def is_login_successful(self):
        return self.points is not None

    def get_points(self, loyalty_data):
        if not loyalty_data['valid']:
            raise LoginError(STATUS_LOGIN_FAILED)

        return loyalty_data['points']

    def _get_balance(self, url):
        loyalty_data = None

        self.browser.open(url)
        try:
            loyalty_data = self.browser.response.json()
        except:
            if self.browser.response.status_code == 404:
                raise ValueError('Scheme ID not found')

            raise LoginError(END_SITE_DOWN)

        if 'error' in loyalty_data or not self._validate_response_keys(loyalty_data):
            raise LoginError(UNKNOWN)

        return loyalty_data

    def login(self, credentials):
        user_identifier = credentials.get('barcode') or credentials.get('card_number')
        if not user_identifier:
            raise ValueError('No valid user details found (Expected: Barcode or card number)')

        scheme_api_identifier = SCHEME_API_DICTIONARY[self.scheme_slug]
        url = 'https://rewards.api.mygravity.co/v2/reward_scheme/{0}/user/{1}/check_balance'.format(
            scheme_api_identifier,
            user_identifier
        )
        self.loyalty_data = self._get_balance(url)

        if self.loyalty_data:
            self.points = self.get_points(self.loyalty_data)
            self.user_id = self.loyalty_data['uid']

    def balance(self):
        return {
            'points': Decimal(self.points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []

    @staticmethod
    def _validate_response_keys(loyalty_data):
        return all(key in loyalty_data.keys() for key in ['points', 'valid'])
