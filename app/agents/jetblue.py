from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
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

        self.check_error('book.jetblue.com', (('#errorMessage', STATUS_LOGIN_FAILED, ''),), url_part='netloc')

    def balance(self):
        return {
            'points': extract_decimal(self.browser.select('p.points')[0].contents[2])
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
