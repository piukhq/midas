import re
from decimal import Decimal, ROUND_DOWN

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED


class Eurostar(RoboBrowserMiner):
    is_login_successful = False
    api_key = None
    point_conversion_rate = 1 / Decimal('300')

    def get_api_key(self):
        self.browser.open('https://accounts.eurostar.com/uk-en/')
        source = self.browser.parsed
        apikey_holder = source.select('#config')[0].text
        self.api_key = re.search(r'"key":"([a-z0-9]+)"', apikey_holder, re.M).group(1)

    def option_request(self):
        self.headers['host'] = 'api.prod.eurostar.com'
        self.headers['origin'] = 'https://accounts.eurostar.com'
        self.headers['referer'] = 'https://accounts.eurostar.com/'
        self.headers['authority'] = 'api.prod.eurostar.com'
        self.headers['method'] = 'OPTIONS'
        self.headers['path'] = '/auth/login?market=uk-en'
        self.headers['scheme'] = 'https'
        self.headers['access-control-request-headers'] = 'content-type,x-apikey'
        self.headers['access-control-request-method'] = 'POST'

        self.browser.open('https://api.prod.eurostar.com/auth/login?market=uk-en', method="OPTIONS")

    def get_bearer_token(self, credentials):
        self.get_api_key()
        self.option_request()

        self.headers['content-type'] = "application/json"
        self.headers['method'] = 'POST'
        self.headers['x-apikey'] = self.api_key
        self.headers['Accept'] = 'application/json'

        data = {
            "username": credentials['email'],
            "password": credentials['password']
        }

        self.browser.open('https://api.prod.eurostar.com/auth/login?market=uk-en',
                          method='post', headers=self.headers, json=data)

        return self.browser.response.json()

    def _login(self, credentials):
        response_json = self.get_bearer_token(credentials)

        if 'message' in response_json.keys():
            raise LoginError(STATUS_LOGIN_FAILED)

        auth_key = response_json['accessToken']
        auth_type = response_json['tokenType']
        auth_token = auth_type + ' ' + auth_key
        account_id = response_json['cid']

        self.headers['authorization'] = auth_token

        self.browser.open('https://api.prod.eurostar.com/accounts/' + account_id + '?market=uk-en',
                          headers=self.headers)

    def _check_if_logged_in(self):
        json_response = self.browser.response.json()
        if 'membership' in json_response.keys():
            self.is_login_successful = True

    def login(self, credentials):
        self._login(credentials)
        self._check_if_logged_in()

    def balance(self):
        points = Decimal(self.browser.response.json()['membership']['points']['redeemablePoints'])
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': value,
            'value_label': self.format_label(value, '£20 e-voucher')
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
