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
        login_form['username'].value = credentials['card_number'][7:] # we dont need the card prefix
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error("/login", (('.login-error > p > strong', STATUS_LOGIN_FAILED,  "Sorry"), ))

    def balance(self):
        points_container = self.browser.find("div", {'class': "points-summary"}).select(".fr-reg")
        points = points_container[0].text.lstrip('You have:').rstrip(' PTS').replace(',', '')
        value = points_container[1].text.lstrip('You can spend:£')
        return {
            "points": extract_decimal(points),
            "value": extract_decimal(value)
        }


    @staticmethod
    def parse_transaction(row):
        extra_details = row.find('div', {'class':'more-transactional-details'})
        # TODO: Redeem points to check points balance goes negative.
        transaction_data = {}
        transaction_data['date'] = arrow.get(row.select('.date')[0].text, 'MMM D, YYYY')
        try:
            location = transaction_data['location'] = extra_details.select('.location')[0].text
        except IndexError:
            location = None
        transaction_data['points'] = extract_decimal(row.select('.points')[0].text.strip().rstrip('pts'))
        partner = row.select('.partner')[0].text.strip()

        collector = extra_details.select('.collector')[0].text
        status = row.select('.status')[0].text.strip()
        process_date = extra_details.select('.date')[0].text

        transaction_data['description'] = 'partner:{}, collector:{},'.format(partner, collector)

        return transaction_data


    def transactions(self):
        # Nectar return the last 10 transactions
        self.open_url("https://www.nectar.com/my-nectar/manage-account/transactions")
        transactions = self.browser.find('ul', {'class': 'full-transaction-statement'}).find_all('li')
        return [self.hashed_transaction(transaction) for transaction in transactions]