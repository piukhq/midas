from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import re


class Krisflyer(RoboBrowserMiner):
    is_login_successful = False
    points_reg_ex = r"^(\d)+"

    def check_if_logged_in(self):
        logged_in_url = "https://www.singaporeair.com/en_UK/ppsclub-krisflyer/account-summary/"
        if self.browser.url == logged_in_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        self.open_url('https://www.singaporeair.com/kfLogin.form?filterFlowExecutionURL=kfDashBoardPPS.form')
        login_form = self.browser.get_form('kfLoginForm')
        login_form['kfNumber'].value = credentials['card_number']
        login_form['pin'].value = credentials['pin']
        self.browser.submit_form(login_form)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        points_sel = self.browser.select('.slide__text--style-2')[0].text
        points = re.match(r"^(\d)+", points_sel).group()
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
