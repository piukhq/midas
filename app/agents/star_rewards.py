from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class StarRewards(RoboBrowserMiner):

    def login(self, credentials):
        self.open_url("https://starrewardapps.valero.com/Account/Login")
        signup_form = self.browser.get_form(action="/Account/Login")
        signup_form['CardNumber'].value = credentials['card_number']
        signup_form['Password'].value = credentials['password']

        self.browser.submit_form(signup_form)

        selector = ".alert"

        if self.browser.url == 'https://starrewardapps.valero.com/Account/LoginSuccess':
            self.open_url("https://starrewardapps.valero.com/Profile/Index")
        self.check_error("/Account/Login",
                         ((selector, STATUS_LOGIN_FAILED, "×\r\n            Member not found"), ))

    def balance(self):
        points = extract_decimal(self.browser.select(".points-balance")[0].contents[0])

        return {
            'points': points,
            'value': Decimal(0),
            'value_label': "",
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].contents[0].strip(), 'DD/MM/YYYY'),
            "description": items[1].contents[0].strip(),
            "points": extract_decimal(items[2].contents[0].strip()),
        }

    def scrape_transactions(self):
        self.open_url("https://starrewardapps.valero.com/Rewards/History")

        return self.browser.select("tr")[1:]
