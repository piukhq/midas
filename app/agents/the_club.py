from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal


class TheClub(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        logged_in_url = 'https://account.theclub.macdonaldhotels.co.uk/customer/myaccount.aspx?action=loginwelcome'
        current_url = self.browser.url
        if current_url == logged_in_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        self.open_url('https://account.theclub.macdonaldhotels.co.uk/customer/login.aspx')

        login_form = self.browser.get_forms()[0]
        login_form['ctl00$Main$txtEmail'].value = credentials['email']
        login_form['ctl00$Main$txtPassword'].value = credentials['password']
        self.browser.submit_form(login_form, submit=login_form.submit_fields['ctl00$Main$cmdLogin'])

    def login(self, credentials):
            self._login(credentials)
            self.check_if_logged_in()

    def balance(self):
        points = self.browser.select('#ctl00_myAccountLinks_MemberPanel div div h5')[1].text
        points = extract_decimal(points)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
