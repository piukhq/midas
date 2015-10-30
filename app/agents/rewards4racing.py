from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
import re


class Rewards4Racing(Miner):
    point_balance_pattern = re.compile(r'(\d+) points')
    point_value_pattern = re.compile(r'Worth £(\d.\d\d)')

    def login(self, credentials):
        self.open_url('https://www.rewards4racing.com/Home/')

        login_form = self.browser.get_form('form1')
        login_form['ctl00$txtUsername'].value = credentials['email']
        login_form['ctl00$txtPassword'].value = credentials['password']
        self.browser.submit_form(login_form, submit=login_form.submit_fields['ctl00$btnSignIn'])

        self.check_error('/Home/',
                         (('#custLogin div.alert.alert-danger', STATUS_LOGIN_FAILED, 'Error logging into account'), ))

    def balance(self):
        # Despite the fact that this site is a copy-paste job identical to two others, they somehow managed to end up
        # with malformed HTML in this one's point balance, so we have to regex it.
        pretty_html = self.browser.parsed.prettify()
        return {
            'points': extract_decimal(self.point_balance_pattern.findall(pretty_html)[0]),
            'value': extract_decimal(self.point_value_pattern.findall(pretty_html)[0]),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        #self.open_url('https://www.rewards4racing.com/MyAccount/PointsStatement/')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]