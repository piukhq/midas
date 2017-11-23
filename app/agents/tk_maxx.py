from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal


class TKMaxx(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        self.browser.open('https://www.bigbrandtreasure.com/en/user/')

        current_url = self.browser.url
        login_fail_url = 'https://www.bigbrandtreasure.com/en/login'
        if current_url != login_fail_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def set_headers(self):
        self.headers['Host'] = 'www.bigbrandtreasure.com'
        self.headers['Origin'] = 'https://www.bigbrandtreasure.com'
        self.headers['Referer'] = 'https://www.bigbrandtreasure.com/en/login'
        self.headers['Content-Type'] = 'application/x-www-form-urlencoded'

    def _login(self, credentials):
        self.open_url('https://www.bigbrandtreasure.com/en/login')

        self.set_headers()

        login_form = self.browser.get_form('user-login-form')
        login_form['name'].value = credentials['email']
        login_form['pass'].value = credentials['password']
        self.browser.submit_form(login_form)

    def login(self, credentials):
            self._login(credentials)
            self.check_if_logged_in()

    def balance(self):
        self.browser.open('https://www.bigbrandtreasure.com/en/reward')
        points = self.browser.select('.shops p em')[1].text

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
