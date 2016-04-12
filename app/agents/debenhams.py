from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
import arrow
from decimal import Decimal


class Debenhams(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        url = ('https://portal.prepaytec.com/chopinweb/scareMyLogin.do?customerCode=452519111525&loc=en'
               '&brandingCode=myscare_uk')
        self.open_url(url)

        login_form = self.browser.get_form('login')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        # Obtain the memorable date form.
        date_form = self.browser.get_form('login')

        # The first 12 cells are just for formatting.
        date_table = self.browser.select("table.memorable tr td")[12:]
        correct = credentials['memorable_date']

        for index, cell in enumerate(date_table):
            # Cells with an input field contain three elements, others just one.
            if len(cell.contents) == 3:
                input_field = cell.contents[1]
                date_form[input_field.attrs['name']] = correct[index]

        self.browser.submit_form(date_form)

        selector = '#login > p.error'
        self.check_error('/chopinweb/scareMyLogin.do',
                         ((selector, STATUS_LOGIN_FAILED, 'Please correct the following errors'), ))

        self.open_url('https://portal.prepaytec.com/chopinweb/scareMyStatement.do')

    def balance(self):
        points = extract_decimal(self.browser.select("td#clearedBalance span.balanceValue")[1].text)
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row.select('td')[0].text.strip(), 'DD/MM/YY'),
            'description': ' '.join(row.select('td')[2].text.split()[1:]),
            'points': Decimal(row.select('td')[3].text.strip()),
        }

    def scrape_transactions(self):
        transactions = self.browser.select('table.txnHistory > tr')[2::2]

        # switch to the 'Points' tab
        search_form = self.browser.get_form('searchForm')
        search_form['selectedTab'].value = 'WALLET1'
        self.browser.submit_form(search_form)

        transactions += self.browser.select('table.txnHistory > tr')[2::2]

        return sorted(transactions, key=lambda t: arrow.get(t.select('td')[0].text.strip(), 'DD/MM/YY'))
