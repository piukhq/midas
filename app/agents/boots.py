from app.agents.base import Miner
from app.agents.exceptions import STATUS_ACCOUNT_LOCKED, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
import arrow


class Boots(Miner):
    def login(self, credentials):
        url = "https://www.boots.com/webapp/wcs/stores/servlet/ADCAccountSummary?" \
              "storeId=10052&langId=-1&catalogId=10552"
        self.open_url(url)

        signup_form = self.browser.get_form(id='Logon')
        signup_form['logonId'].value = credentials['user_name']
        signup_form['logonPassword'].value = credentials['password']

        # we need to change the action url or else it uses javascript
        signup_form.action = "https://www.boots.com/webapp/wcs/stores/servlet/LoginRequestDispatcher"
        self.browser.submit_form(signup_form)

        selector = "#formErrorContainer > div > div > ul > li > a"
        self.check_error("/webapp/wcs/stores/servlet/LoginRequestDispatcher",
                         ((selector, STATUS_LOGIN_FAILED, "The email address and password you entered has not been"),
                          (selector, STATUS_ACCOUNT_LOCKED, "You have exceeded the maximum number of attempts")))

    def balance(self):
        return {
            "amount": extract_decimal(self.browser.select(".pointsValue")[0].contents[0]),
            "value": extract_decimal(self.browser.select(".pointsValue")[1].contents[0])
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].contents[0], 'DD/MM/YYYY'),
            "title": items[1].contents[0],
            "points": extract_decimal(items[3].contents[0]),
        }

    def transactions(self):
        rows = self.browser.select(".transactionsList tr")[1:]
        return [self.hashed_transaction(row) for row in rows]

    def account_overview(self):
        return {
            'balance': self.balance(),
            'transactions': self.transactions()
        }