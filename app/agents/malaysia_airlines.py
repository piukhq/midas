from app.agents.base import Miner
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class MalaysiaAirlines(Miner):
    def login(self, credentials):
        self.open_url('https://www.enrich.malaysiaairlines.com/EnrichWebsite/index')

        login_form = self.browser.get_form('loginForm')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

    def balance(self):
        return {
            'points': extract_decimal(self.browser.select('div.sidebar-content.spacing-top-50 > p')[0].text),
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        return {
            'date': arrow.get(data[0].text, 'DD.MM.YYYY'),
            'description': data[1].text,
            'points': Decimal(data[2].text),
        }

    def transactions(self):
        self.open_url('https://www.enrich.malaysiaairlines.com/EnrichWebsite/mymiles-myactivity')

        rows = self.browser.select('table.table.table-miles.spacing-top-10 > tbody > tr')[1:]
        return [self.hashed_transaction(row) for row in rows]
