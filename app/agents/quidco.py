from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
import arrow


class Quidco(Miner):
    def login(self, credentials):
        self.open_url('https://www.quidco.com/sign-in/?sign_in_redirect_path=%2Factivity%2F')

        login_form = self.browser.get_form('sign-in-page-form')
        login_form['username'].value = credentials['email']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'div.alert'
        self.check_error('/sign-in/', ((selector, STATUS_LOGIN_FAILED, 'Invalid username'),))

    def balance(self):
        points = extract_decimal(self.browser.select('div.earnings p.amount')[0].text)
        return {
            'points': points,
            'value': points,
            'value_label': '£{}'.format(points),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        # Most descriptions are links, some are not.
        description_holder = data[1].select('a.name')
        if len(description_holder) == 0:
            description_holder = data[1].select('span.name')

        return {
            'date': arrow.get(data[0].select('span')[0].contents[0].strip(), 'DD MMM YY'),
            'description': description_holder[0].contents[0].strip(),
            'points': extract_decimal(data[3].contents[0].strip()),
        }

    def transactions(self):
        rows = self.browser.select('#activity-table tbody tr')
        # Every second row is a hidden element we can't parse, so skip it.
        return [self.hashed_transaction(row) for row in rows[0::2]]
