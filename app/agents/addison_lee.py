from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal


class AddisonLee(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        json_response = self.browser.response.json()
        if json_response['isSuccessful']:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def set_headers(self):
        self.browser.open('https://beta.addisonlee.com/al/api/config')

        xsrf_token = self.browser.response.cookies['XSRF-TOKEN']
        self.headers['Accept'] = 'application/json, text/plain, */*'
        self.headers['Host'] = 'beta.addisonlee.com'
        self.headers['Origin'] = 'https://beta.addisonlee.com'
        self.headers['Referer'] = 'https://beta.addisonlee.com/al/sign-in'
        self.headers['Content-Type'] = 'application/json;charset=UTF-8'
        self.headers['X-XSRF-TOKEN'] = xsrf_token

    def _login(self, credentials):
        self.set_headers()

        url = 'https://beta.addisonlee.com/al/api/login?rememberMe=false'
        data = {
            'username': credentials['email'],
            'password': credentials['password'],
            'captchaSolution': None
        }
        self.browser.open(url, method='POST', headers=self.headers, json=data)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        self.browser.open('https://beta.addisonlee.com/al/api/user/loyalty/info',  headers=self.headers)
        points = self.browser.response.json()['data']['card']['points']

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
