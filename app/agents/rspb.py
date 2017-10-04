from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal
import re
import arrow


class RSPB(RoboBrowserMiner):
    is_login_successful = False

    def _check_if_logged_in(self):
        try:
            self.open_url("https://wwws-uk1.givex.com/cws/rspb_l/consumer/clp/my_cards.py")

            current_url = self.browser.url
            if current_url == "https://wwws-uk1.givex.com/cws/rspb_l/consumer/clp/my_cards.py":
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def login(self, credentials):
        self.open_url("https://wwws-uk1.givex.com/cws/rspb_l/consumer/main/home.py")

        login_form = self.browser.get_forms()[0]
        login_form['username'] = credentials['email']
        login_form['password'] = credentials['password']

        self.browser.submit_form(login_form)
        self._check_if_logged_in()

    def balance(self):
        value = extract_decimal(self.browser.select('.autolist-col')[1].text)
        points = extract_decimal(self.browser.select('.autolist-col')[2].text)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        current_year = row[1]
        visit_date = row[0].select('.autolist-col')[1].text
        action = row[0].select('.autolist-col')[3].text.strip()
        total_points = row[0].select('.autolist-col')[6].text

        date = visit_date + '/' + current_year
        date = arrow.get(date, 'MM/DD/YYYY')

        return {
            'date': date,
            'description': action,
            'points': Decimal(total_points)
        }

    def scrape_transactions(self):
        transaction_detail_rows = []
        current_url = self.browser.url

        transaction_rows = self.browser.select('form[action="my_cards.py"] .autolist-row')

        for transaction_row in transaction_rows:
            transaction_href = transaction_row.select('.autolist-col > a')[1]['href']
            url = re.sub('/my_cards.py', '/', current_url)
            transactions_url = url + transaction_href

            self.open_url(transactions_url)
            current_year = self.browser.select('select[name=date] option')[0].text

            transaction_detail_rows.append(self.browser.select('.autolist-row')[0])
            transaction_detail_rows.append(current_year)

        return [transaction_detail_rows]
