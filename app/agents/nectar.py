import arrow
from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Nectar(Miner):
    # TODO: REPLACE WITH REAL LIMIT
    retry_limit = 3

    def login(self, credentials):
        self.open_url("https://www.nectar.com/login")

        login_form = self.browser.get_form(id='loginform')
        login_form['username'].value = credentials['barcode'][-11:]  # we dont need the card prefix
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error("/login", (('.login-error > p > strong', STATUS_LOGIN_FAILED,  "Sorry"), ))

    def balance(self):
        points_container = self.browser.find("div", {'class': "points-summary"}).select(".fr-reg")
        points = points_container[0].text.lstrip('You have:').rstrip(' PTS').replace(',', '')
        value = extract_decimal(points_container[1].text.lstrip('You can spend:£'))

        return {
            "points": extract_decimal(points),
            "value": value,
            'value_label': '£{}'.format(value)
        }

    # TODO: Redeem points to check points balance goes negative.
    @staticmethod
    def parse_transaction(row):
        extra_details = row.find('div', {'class': 'more-transactional-details'})

        try:
            location = extra_details.select('.location')[0].text
        except IndexError:
            location = None

        partner = row.select('.partner')[0].text.strip()
        collector = extra_details.select('.collector')[0].text

        transaction = {
            'date': arrow.get(row.select('.date')[0].text, 'MMM D, YYYY'),
            'description': 'Partner: {0}, {1},'.format(partner, collector),
            'points': extract_decimal(row.select('.points')[0].text.strip().rstrip('pts')),
        }

        if location:
            transaction['location'] = location

        return transaction

    def transactions(self):
        # Nectar return the last 10 transactions
        self.open_url("https://www.nectar.com/my-nectar/manage-account/transactions")
        transactions = self.browser.select('ul.transactions-list li.transaction')
        return self.hash_transactions(self.parse_transaction(transaction) for transaction in transactions)
