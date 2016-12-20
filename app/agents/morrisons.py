import re
from decimal import Decimal
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
        self.open_url('https://my.morrisons.com/more/js/apigeeService.js')

        pretty_html = self.browser.parsed.prettify()
        api_key = self.api_key_pattern.findall(pretty_html)[0]
        creds = {'username':credentials['email'], 'password':credentials['password'],}

        self.browser.open('https://auth.morrisons.com/login?apikey={}&response_type=token&state=123&redirect_uri=https://my.morrisons.com/more/callback.html'.format(api_key), method='post', data=creds, allow_redirects=False)

        try:
            rheaders = self.browser.response.headers['Location']
            self.access_token = self.access_token_pattern.findall(rheaders)

            if not len(self.access_token):
                raise LoginError(STATUS_LOGIN_FAILED)
        except KeyError:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):

        headers = {'Referer':'https://my.morrisons.com/more/account.html', 'Authorization':'Bearer ' + self.access_token[0], }
        self.browser.open('https://api.morrisons.com/customer/v2/customers/@me', method='get', headers=headers)

        pretty_html = self.browser.parsed.prettify()
        self.card_number = self.card_number_pattern.findall(pretty_html)[0]

        url = 'https://api.morrisons.com/card/v1/cards/{}/balance'.format(self.card_number)
        self.browser.open(url, method='get', headers=headers)

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
        headers = {'Referer': 'https://my.morrisons.com/more/account.html',
                   'Authorization': 'Bearer ' + self.access_token[0], }
        self.browser.open('https://api.morrisons.com/card/v1/cards/{}/transactions?pageLength=50&pageNumber=1&includeLinkedCards=true'.format(self.card_number),
                      method='get', headers=headers)
        return self.browser.response.json()['transactions']
