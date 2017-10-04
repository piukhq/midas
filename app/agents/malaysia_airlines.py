from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class MalaysiaAirlines(RoboBrowserMiner):
    def login(self, credentials):
        self.open_url('https://www.enrich.malaysiaairlines.com/EnrichWebsite/index')

        login_form = self.browser.get_form('loginForm')
        login_form['username'].value = credentials['card_number']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        if self.browser.url.startswith('https://www.enrich.malaysiaairlines.com/EnrichWebsite/index?badcredential='):
            raise LoginError(STATUS_LOGIN_FAILED)

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

    def scrape_transactions(self):
        # This request is incredibly slow to return, we need to wait ~40 seconds to actually get a response back.
        self.open_url('https://www.enrich.malaysiaairlines.com/EnrichWebsite/mymiles-myactivity', read_timeout=40)
        return self.browser.select('table.table.table-miles.spacing-top-10 > tbody > tr')[1:]
