from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow

class Qantas(Miner):
    def login(self, credentials):
        self.open_url('https://www.qantas.com.au/fflyer/do/dyns/auth/youractivity/yourActivity')

        login_form = self.browser.get_form('FFLoginForm')
        login_form['login_ffNumber'].value = credentials['card_number']
        login_form['login_surname'].value = credentials['last_name']
        login_form['login_pin'].value = credentials['pin']

        self.browser.submit_form(login_form)

        selector = '#errormsgs ul li'
        self.check_error('/fflyer/do/dyns/dologin',
                         ((selector, STATUS_LOGIN_FAILED, 'The details do not match our records'),))

    def balance(self):
        return {
            'points': extract_decimal(self.browser.select('div.guts div.clearit strong')[2].text),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        return {
            'date': arrow.get(data[0].text.strip(), 'DD MMM YY'),
            'description': data[1].text.strip(),
            'points': extract_decimal(data[2].text.strip()),
        }

    def transactions(self):
        rows = self.browser.select('#ffactivity tbody tr')
        return [self.hashed_transaction(row) for row in rows if row.select('td')[2].text.strip() != '-']
