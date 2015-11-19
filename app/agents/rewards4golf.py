from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Rewards4Golf(Miner):
    def login(self, credentials):
        self.open_url('https://www.rewards4golf.com/Home/')

        login_form = self.browser.get_form('form1')
        login_form['ctl00$txtUsername'].value = credentials['email']
        login_form['ctl00$txtPassword'].value = credentials['password']
        self.browser.submit_form(login_form, submit=login_form.submit_fields['ctl00$btnSignIn'])

        self.check_error('/Home/',
                         (('#custLogin div.alert.alert-danger', STATUS_LOGIN_FAILED, 'Error logging into account'), ))

    def balance(self):
        point_holder = self.browser.select('#mainmenu span')[0]
        value = extract_decimal(point_holder.contents[2])

        return {
            'points': extract_decimal(point_holder.contents[0].text),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        # self.open_url('https://www.rewards4golf.com/MyAccount/PointsStatement/')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
