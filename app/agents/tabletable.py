from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN
import arrow


class Tabletable(Miner):
    point_conversion_rate = Decimal('0.002')

    def login(self, credentials):
        self.open_url('https://www.tastyrewards.co.uk/')

        login_form = self.browser.get_form('_58_fm')
        login_form['_58_login'].value = credentials['email']
        login_form['_58_password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'div.portlet-msg-error'
        self.check_error('/home', ((selector, STATUS_LOGIN_FAILED, 'You have entered invalid data'),))

    def balance(self):
        points = extract_decimal(self.browser.select('div.yellow h3 span')[0].text)
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': value,
            'value_label': self.format_label(value, 'discount voucher'),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.find_all('td')
        return {
            'date': arrow.get(data[4].contents[0].strip(), 'DD/MM/YY'),
            'description': data[2].contents[0].strip(),
            'points': extract_decimal(data[3].contents[0].strip()),
        }

    def transactions(self):
        self.open_url('https://www.tastyrewards.co.uk/group/tasty-rewards/your-account')

        rows = self.browser.select('div.pointsTransaction tr.portlet-section-body.results-row')[1:]
        return [self.hashed_transaction(row) for row in rows]
