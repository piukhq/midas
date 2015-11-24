from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Monsoon(Miner):
    def login(self, credentials):
        self.open_url('https://uk.monsoon.co.uk/view/secured/content/myaccount?activeTab=cs_myaccounttab3',
                          verify=False)

        login_form = self.browser.get_form(action='/j_spring_security_check')
        login_form['j_username'].value = credentials['email']
        login_form['j_password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error('/view/secured/content/login',
                         (('div.login_main_error_box.generic_form_error', STATUS_LOGIN_FAILED, 'Sign In Failed'), ))

    def balance(self):
        value = extract_decimal(self.browser.select('div.reward-points dl dd')[2].text)
        return {
            'points': extract_decimal(self.browser.select('div.reward-points dl dd')[1].text),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        # self.open_url('https://uk.monsoon.co.uk/view/secured/content/myaccount?activeTab=cs_myaccounttab')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
