from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal


class JetBlue(SeleniumMiner):
    is_successful_login = False

    def _login(self, credentials):
        self.browser.get('https://book.jetblue.com/B6.auth/login?intcmp=hd_signin'
                         '&service=https://www.jetblue.com/default.aspx')
        self.browser.find_element_by_name('username').send_keys(credentials['email'])
        self.browser.find_element_by_name('password').send_keys(credentials['password'])
        self.browser.find_element_by_css_selector('#casLoginForm button').click()

    def check_login(self):
        account_url = 'https://trueblue.jetblue.com/group/trueblue/my-trueblue-home'

        self.browser.get(account_url)
        self.wait_for_page_load(timeout=15)
        # repeat above call to account_url to get past one time redirect
        self.browser.get(account_url)
        current_url = self.browser.current_url
        if current_url == account_url:
            self.is_successful_login = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        try:
            self._login(credentials)
        except Exception:
            raise LoginError(UNKNOWN)

        self.check_login()
        self.points = self.browser.find_element_by_class_name('points-info').text

    def balance(self):

        return {
            'points': extract_decimal(self.points),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
