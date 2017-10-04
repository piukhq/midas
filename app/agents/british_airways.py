import arrow
import re
from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, TRIPPED_CAPTCHA
from app.utils import extract_decimal
from decimal import Decimal


class BritishAirways(RoboBrowserMiner):
    # TODO: REPLACE WITH REAL LIMIT
    retry_limit = 3

    def login(self, credentials):
        self.open_url("https://www.britishairways.com/travel/loginr/public/en_gb")

        login_form = self.browser.get_form(id='loginrForm')
        login_form['membershipNumber'].value = credentials['username']
        login_form['password'].value = credentials['password']
        login_form.action = '?eId=109001'
        self.browser.submit_form(login_form)
        self.check_error("/travel/loginr/public/en_gb",
                         (('#blsErrosContent > div > ul > li', STATUS_LOGIN_FAILED,  "We are not able to"),
                          ('#t-main-fragment > div > h1', TRIPPED_CAPTCHA, 'Validation question')))

    def balance(self):
        points_span = self.browser.select('.nowrap')[0]
        points = Decimal(points_span.text.strip('My Avios:  |').strip().replace(',', ''))

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': ''
        }

    def scrape_transactions(self):
        self.open_url("https://www.britishairways.com/travel/viewtransaction/execclub/_gf/en_gb?eId=172705")
        self.open_url("https://www.britishairways.com/travel/viewtransaction/execclub/_gf/en_gb?eId=172705")

        table_body = self.browser.find("table", {"id": "recentTransTbl"}).find('tbody')
        return table_body.select('tr')[:-1]  # The last row is a summary row

    @staticmethod
    def parse_transaction(row):
        columns = row.select('td')
        if columns[4].text.strip() == '-':
            points = extract_decimal('0')
        else:
            points = extract_decimal(columns[4].text)
        return {
            'date': arrow.get(columns[0].text.strip(), 'DD-MMM-YY'),
            'description': re.sub(r'\s+', ' ', columns[2].text).strip(),
            'points': points
        }
