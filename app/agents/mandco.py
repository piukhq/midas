from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class MandCo(Miner):
    def login(self, credentials):
        self.open_url('https://www.mandco.com/sign-in')
        login_form = self.browser.get_form('dwfrm_login')

        # The email field name is partially scrambled.
        for k, v in login_form.fields.items():
            if v.name.startswith('dwfrm_login_username'):
                login_form[k].value = credentials['email']
                break

        login_form['dwfrm_login_password'].value = credentials['password']

        post_data = {}
        post_data['dwfrm_login_login'] = 'Login'
        for k, v in login_form.fields.items():
            post_data[k] = v.value

        self.browser.open(login_form.action, method='post', data=post_data)

        #self.check_error('/sign-in', (('#dwfrm_login div.error-form',
        #                               STATUS_LOGIN_FAILED, 'Oops, this email address and password'), ))

    def balance(self):
        return {
            'points': extract_decimal(self.browser.select('.loyalty-card-content-wraper p strong')[0].text)
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [self.hashed_transaction(t)]
