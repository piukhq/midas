from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
from app.utils import extract_decimal


class Victoria(RoboBrowserMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        json_response = self.browser.response.json()
        if json_response == '/en-us/client-area':
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def set_headers(self):
        self.headers['Host'] = "www.flytap.com"
        self.headers['Origin'] = "https://www.flytap.com"
        self.headers['Referer'] = "https://www.flytap.com/en-us/login"
        self.headers['Content-Type'] = "application/json"
        self.headers['X-Requested-With'] = "XMLHttpRequest"

    def _login(self, credentials):
        self.set_headers()
        url = "https://www.flytap.com/api/LoginPage?sc_mark=US&sc_lang=en-US"
        data = {
          "formModel": {
            "FormData": {
              "LoginFormID": 0,
              "Email": credentials['email'],
              "clientNumber": None,
              "Password": credentials['password'],
              "Remember": True,
              "SocialUserId": None,
              "SocialProvider": None
            }
          }
        }
        self.open_url(url, method="post", json=data)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

    def balance(self):
        self.browser.open("https://www.flytap.com/en-us/client-area")
        points = self.browser.select('.center-mode')[0].text
        points = extract_decimal(points)

        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
