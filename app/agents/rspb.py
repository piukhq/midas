from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal
import re
import arrow


class RSPB(RoboBrowserMiner):
    is_login_successful = False

    def _check_if_logged_in(self):
        self.open_url('https://wwws-uk1.givex.com/cws/rspb_l/consumer/clp/my_cards.py')

        current_url = self.browser.url
        if current_url == 'https://wwws-uk1.givex.com/cws/rspb_l/consumer/clp/my_cards.py':
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def login(self, credentials):
        self.open_url('https://wwws-uk1.givex.com/cws/rspb_l/consumer/main/home.py')

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
        visit_date = row[1]
        action = row[3].text
        amount_spent = row[4].text
        total_points = row[6].text

        date = visit_date
        date = arrow.get(date, 'MM/DD/YYYY')

        return {
            'date': date,
            'description': action + ' - ' + amount_spent,
            'points': Decimal(total_points),
        }

    def get_transactions_by_year(self, year):
        transaction_list = []
        transaction_objects = []
        url = 'https://wwws-uk1.givex.com/cws/rspb_l/consumer/clp/balance_check.py'
        data = {
            'history_type': 'loyalty',
            'date': year,
            'form_submit': 't',
        }
        self.open_url(url, method='post', data=data)

        transaction_objects.extend(self.browser.select('.autolist-row'))
        transaction_objects.extend(self.browser.select('.autolist-row-alt'))

        for transaction in transaction_objects:
            if transaction:
                split_transaction = transaction.select('td.autolist-col')
                split_transaction[1] = split_transaction[1].text + '/{}'.format(year)
                transaction_list.append(split_transaction)

        return transaction_list

    def scrape_transactions(self):
        current_year = arrow.utcnow().year
        previous_year = arrow.utcnow().year - 1
        years = [current_year, previous_year]
        transaction_detail_rows = []
        current_url = self.browser.url

        cards = self.browser.select('form[action="my_cards.py"] .autolist-row')

        for card_obj in cards:
            card_href = card_obj.select('.autolist-col > a')[1]['href']
            url = re.sub('/my_cards.py', '/', current_url)
            transactions_url = url + card_href

            self.open_url(transactions_url)

            for year in years:
                transaction_detail_rows.extend(self.get_transactions_by_year(year))

        transaction_detail_rows = [transaction for transaction in transaction_detail_rows if not None]
        transaction_detail_rows.sort(key=lambda date: date[1], reverse=True)

        return transaction_detail_rows
