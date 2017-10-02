from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError, CONFIRMATION_REQUIRED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class JetBlue(Miner):
    def login(self, credentials):
        self.open_url('https://book.jetblue.com/B6.auth/login?service=https%3A%2F%2Ftrueblue.jetblue.com%2Fc%2Fportal%2'
                      'Flogin%3Fredirect%3D%252Fgroup%252Ftrueblue%252Factivity-history%26p_l_id%3D10514')

        login_form = self.browser.get_form('casLoginForm')
        login_form['username'] = credentials['email']
        login_form['password'] = credentials['password']
        self.browser.submit_form(login_form)

        self.browser.open('https://trueblue.jetblue.com/group/trueblue/my-trueblue-home')

        self.check_error('book.jetblue.com', (('#errorMessage', STATUS_LOGIN_FAILED, ''),), url_part='netloc')

        mtce_message = self.browser.select('#mailing-address > p > legend')
        if mtce_message and mtce_message[0].text == 'PLEASE CONFIRM OR UPDATE YOUR MAILING ADDRESS BELOW':
            raise LoginError(CONFIRMATION_REQUIRED)

        mtce_message = self.browser.select('#optional-fields > p > legend')
        if mtce_message and mtce_message[0].text == ('PLEASE COMPLETE ANY BLANK PROFILE FIELDS '
                                                     'BELOW OR POSTPONE UNTIL LATER'):
            raise LoginError(CONFIRMATION_REQUIRED)

    def balance(self):
        return {
            'points': extract_decimal(self.browser.select('.points-info p')[0].contents[0]),
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal('0'),
        }
        return [t]
