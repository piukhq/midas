import re
from decimal import Decimal
from urllib.parse import parse_qs, urlsplit
from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED


class Morrisons(Miner):
    card_number = None
    api_key_pattern = re.compile(r'apikey:"([A-z0-9]+)"')
    card_number_pattern = re.compile(r'"cardNumber":"([0-9]+)"')
    access_token_pattern = re.compile(r'access_token=([A-z0-9]+)')
    current_points_pattern = re.compile(r'"currentPoints":([0-9]+)')

    def login(self, credentials):
        self.open_url('https://auth.morrisons.com/login?apikey=mDuA4s8AUAiS0l43QO3LKsfn8Tw7egWH'
                      '&response_type=token&state=123'
                      '&redirect_uri=https://www.morrisons.com/matchandmore/callback.html')

        signup_form = self.browser.get_form(id='login')
        signup_form['username'].value = credentials['email']
        signup_form['password'].value = credentials['password']
        self.browser.submit_form(signup_form, verify=False, allow_redirects=False)
        if self.browser.response.status_code == 401:
            raise LoginError(STATUS_LOGIN_FAILED)

        # get the access token
        self.access_token = parse_qs(urlsplit(self.browser.response.headers['location']).fragment)['access_token'][0]
        self.browser.open(self.browser.response.headers['location'])
        # get the card number
        self.headers = {'Authorization': 'Bearer {0}'.format(self.access_token)}
        self.open_url('https://api.morrisons.com/customer/v2/customers/@me', headers=self.headers)
        self.card_number = self.browser.response.json()['cardNumber']

    def balance(self):

        url = 'https://api.morrisons.com/card/v1/cards/{}/balance'.format(self.card_number)
        self.browser.open(url, method='get', headers=self.headers)

        pretty_html = self.browser.parsed.prettify()
        points = Decimal(self.current_points_pattern.findall(pretty_html)[0])

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['dateTime']),
            'description': 'transaction',
            'location': row['siteName'].strip(),
            'points': Decimal(row['points']),
        }

    def scrape_transactions(self):
        self.browser.open('https://api.morrisons.com/card/v1/cards/{}/transactions?pageLength=50&pageNumber=1&includeLinkedCards=true'.format(self.card_number),
                      method='get', headers=self.headers)
        return self.browser.response.json()['transactions']
