from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal


class AirAsia(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        logged_in_url = 'https://assistive.airasia.com/h5/assistive/r/member/profile-landing.aspx'
        current_url = self.browser.url

        if current_url == logged_in_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        self.browser.open('https://assistive.airasia.com/h5/assistive/r/member/login.aspx')

        login_form = self.browser.get_forms()[0]
        login_form['username'] = credentials['email']
        login_form['password'] = credentials['password']
        self.browser.submit_form(login_form)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        user_details = self.browser.select('.userdetails')[0]
        points = user_details.select('b')[2].text
        points = extract_decimal(points)

        return {
            'points': Decimal(points),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError('Implement when scraping transactions.')

    def scrape_transactions(self):
        return []
