from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from decimal import Decimal
import arrow


class Paperchase(Miner):
    def login(self, credentials):
        self.open_url('https://www.paperchase.co.uk/treat-me/balance/account/')

        login_form = self.browser.get_form('login-form')
        login_form['login[username]'].value = credentials['email']
        login_form['login[password]'].value = credentials['password']
        self.browser.submit_form(login_form)

        json = self.browser.response.json()

        if json['error']:
            message = json['message']

            if message == 'Invalid login or password.':
                raise LoginError(STATUS_LOGIN_FAILED)
            else:
                raise LoginError(UNKNOWN)

    def balance(self):
        self.open_url('https://www.paperchase.co.uk/treat-me/balance/account/')

        stamps = self.browser.select('#spend-more-block-id > div > div')[0].select('span')
        num_spent = len([stamp for stamp in stamps if 'spent' in stamp.attrs['class']])

        return {
            'points': Decimal(num_spent),
            'value': Decimal('0'),
            'value_label': '{}/10 stamps towards your next treat'.format(num_spent),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://www.paperchase.co.uk/sales/order/history')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
