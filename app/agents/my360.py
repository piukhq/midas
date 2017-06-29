from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import LoginError, UNKNOWN, STATUS_LOGIN_FAILED, END_SITE_DOWN
from app.my360endpoints import SCHEME_API_DICTIONARY


# list_of_active_my360_schemes = [my360_scheme for scheme in AGENTS if AGENTS[scheme] == 'my360.My360']
class My360(Miner):
    points = None

    def is_login_successful(self):
        if self.points:
            return True

        else:
            return False

    def get_points(self, loyalty_data):
        if not loyalty_data['valid']:
            raise LoginError(STATUS_LOGIN_FAILED)

        elif loyalty_data['valid']:
            return(loyalty_data['points'])

    def email_api_conversion(self, email):
        keyStr = "123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz._-+"
        ord_email = []
        encoded_email = ''

        for character in list(email):
            ord_email.append(ord(character))

        for x in ord_email:
            if 48 <= x <= 57 or 65 <= x <= 90 or 97 <= x <= 122:
                encoded_email += '2' + keyStr[x-65]
            else:
                encoded_email += keyStr[x-65] + '~'

        return encoded_email

    def check_complete_api_response_and_try_again(self, url):
        count = 0
        while count < 5:
            self.browser.open(url)
            try:
                self.loyalty_data = self.browser.response.json()

            except:
                if self.browser.response.status_code == 404:
                    raise ValueError('Scheme ID not found')

                else:
                    raise LoginError(END_SITE_DOWN)

            if all(key in self.loyalty_data.keys() for key in ['points', 'valid']):
                return True

            else:
                self.browser.open(url)
                count += 1
        return False

    def login(self, credentials):
        if credentials.get('barcode'):
            user_identifier = credentials['barcode']

        elif credentials.get('email'):
            user_identifier = self.email_api_conversion(credentials['email'])

        else:
            raise ValueError('No valid user details found (Expected: Barcode or Email)')

        scheme_api_identifier = SCHEME_API_DICTIONARY[self.scheme_slug]
        url = 'https://rewards.api.mygravity.co/v2/reward_scheme/{0}/user/{1}/check_balance'.format(
            scheme_api_identifier,
            user_identifier
        )

        # Rarely the api fails and returns incomplete information so we try a few times
        if self.check_complete_api_response_and_try_again(url):
            self.points = self.get_points(self.loyalty_data)
            self.user_id = self.loyalty_data['uid']

        elif 'error' in self.loyalty_data:
            if (self.browser.response.status_code == 401 or
               self.loyalty_data['error'].startswith('500')):
                # Different schemes use different error responses
                # so can't make specific LoginErrors
                raise ValueError('Invalid Scheme ID or User ID')

        else:
            raise LoginError(UNKNOWN)

    def balance(self):
        return {
            'points': Decimal(self.points),
            'value': Decimal('0'),
            'value_label': '',
            'data': self.user_id
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
