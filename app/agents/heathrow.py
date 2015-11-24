from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import arrow


class Heathrow(Miner):
    use_tls_v1 = True
    point_conversion_rate = Decimal('0.002')

    def login(self, credentials):
        self.open_url('https://rewards.heathrow.com')

        login_form = self.browser.get_form('loginForm')
        login_form['login'].value = credentials['email']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = '#loginForm.errors'
        self.check_error('/web/lhr/heathrow-rewards', ((selector, STATUS_LOGIN_FAILED, 'Invalid login or password'),))

    def balance(self):
        points = extract_decimal(self.browser.select('div.rightCol span')[0].text)
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': value,
            'value_label': self.format_label(value, '£5 voucher'),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')
        return {
            'date': arrow.get(data[0].contents[0].strip(), 'DD/MM/YYYY'),
            'description': data[3].select('div')[0].contents[0].strip(),
            'points': extract_decimal(data[4].contents[0].strip())
        }

    def transactions(self):
        self.open_url('https://rewards.heathrow.com/group/lhr/my-transactions')
        rows = self.browser.select('div.transaction-history-table-container tr')
        return [self.hashed_transaction(row) for row in rows]
