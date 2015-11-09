from decimal import Decimal
from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from urllib.parse import parse_qs, urlsplit
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED


class Morrisons(Miner):
    card_number = None
    point_conversion_rate = Decimal('0.001')

    def login(self, credentials):
        # this url is built from the values found in https://www.morrisons.com/matchandmore/js/apigeeService.js
        self.open_url('https://auth.morrisons.com/login?apikey=mDuA4s8AUAiS0l43QO3LKsfn8Tw7egWH'
                      '&response_type=token&state=123'
                      '&redirect_uri=https://www.morrisons.com/matchandmore/callback.html')
        signup_form = self.browser.get_form(id='login')
        signup_form['username'].value = credentials['email']
        signup_form['password'].value = credentials['password']

        self.browser.submit_form(signup_form, verify=False)
        self.check_error('/login', (('.error-message', STATUS_LOGIN_FAILED, 'Wrong username or password'), ))

        # get the access token and the card number
        access_token = parse_qs(urlsplit(self.browser.url).fragment)['access_token'][0]
        self.headers = {'Authorization': 'Bearer {0}'.format(access_token)}
        self.open_url('https://api.morrisons.com/customer/v2/customers/@me')
        self.card_number = self.browser.response.json()['cardNumber']

    def balance(self):
        self.open_url('https://api.morrisons.com/card/v1/cards/{0}/balance'.format(self.card_number))
        points = Decimal(self.browser.response.json()['currentPoints'])
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['dateTime']),
            'description': 'transaction',
            'location': row['siteName'].strip(),
            'points': Decimal(row['points']),
        }

    def transactions(self):
        self.open_url('https://api.morrisons.com/card/v1/cards/{0}/transactions?'
                      'pageLength=50&pageNumber=1&includeLinkedCards=true'.format(self.card_number))
        rows = self.browser.response.json()['transactions']
        return [self.hashed_transaction(row) for row in rows]
