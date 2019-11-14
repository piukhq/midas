import arrow
from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Nectar(RoboBrowserMiner):
    # TODO: REPLACE WITH REAL LIMIT
    retry_limit = 3

    def login(self, credentials):
        self.open_url("https://www.nectar.com/login")

        if 'barcode' in credentials:
            username = credentials['barcode'][-11:]
        else:
            username = credentials['card_number'][-11:]

        login_form = self.browser.get_form(id='signinform')
        login_form['username'].value = username
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error("/login", (('.login-error > p > strong', STATUS_LOGIN_FAILED, "Sorry"), ))

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
            location = extra_details.select('.location')[0].text[9:]
        except IndexError:
            location = None

        partner = row.select('.partner')[0].text.strip()
        collector = extra_details.select('.collector')[0].text[10:]

        transaction = {
            'date': arrow.get(row.select('.date')[0].text, 'D MMM YYYY'),
            'description': 'Partner: {0}, Collector: {1},'.format(partner, collector),
            'points': extract_decimal(row.select('.points')[0].text.strip().rstrip('pts')),
        }

        if location:
            transaction['location'] = location

        return transaction

    def scrape_transactions(self):
        self.open_url("https://www.nectar.com/my-nectar/manage-account/transactions")
        return self.browser.select('ul.transactions-list li.transaction')
