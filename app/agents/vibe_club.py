import re

from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal


class VibeClub(RoboBrowserMiner):
    is_login_successful = False
    points_re = re.compile(r'points balance is [^=.]*')
    balance_re = re.compile(r'cash balance is [^=.]*')

    def check_if_logged_in(self):
        try:
            success_url = "https://boostvibe.boostjuicebars.co.uk/main.py"
            current_url = self.browser.url
            if current_url.startswith(success_url):
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def _login(self, credentials):
        self.open_url('https://boostvibe.boostjuicebars.co.uk/login.py')

        login_form = self.browser.get_form('login')
        login_form['formPosted'].value = '1'
        login_form['uri'].value = ''
        login_form['login_email'].value = credentials['email']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        source = self.browser.parsed.prettify()
        points_text = self.points_re.findall(source)[0]
        points = extract_decimal(points_text)
        value_text = self.balance_re.findall(source)[0]
        value = extract_decimal(value_text)

        return {
            'points': points,
            'value': value,
            'value_label': '${}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
