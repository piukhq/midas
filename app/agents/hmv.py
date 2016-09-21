from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
from decimal import Decimal


import arrow


class HMV(Miner):
    retry_limit = 3

    def login(self, credentials):
        self.open_url("https://purehmv.com/gb/Pages/Login.html")

        signup_form = self.browser.get_form(id='form')

        signup_form['Root$Main$ctl00$txtEmail'].value = credentials['email']
        signup_form['Root$Main$ctl00$txtPassword'].value = credentials['password']

        self.browser.submit_form(signup_form, submit=signup_form['Root$Main$ctl00$btnLogin'])

        if self.browser.url != 'https://purehmv.com/gb/Pages/Home.html':
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):

        points = extract_decimal(self.browser.find('div', {'class': 'rightside balance'}).text)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': ''
            }

    # assumption here is that row is one element of the list that is returned by scrape_transactions
    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].text.strip(), 'DD/MM/YYYY'),
            "description": items[2].text.strip(),
            "points": extract_decimal(items[1].text.strip()),
        }

    def scrape_transactions(self):
        self.open_url("https://purehmv.com/gb/Pages/Member/Profile/Balance.html")
        if self.browser.find('table', {'id': 'Main_ctl01_gridList'}).select('tr')[0].text.strip() == \
                "There is no transaction to display.":
            return []
        return self.browser.find('table', {'id': 'Main_ctl01_gridList'}).select('tr')
