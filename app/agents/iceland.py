from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Iceland(Miner):
    is_login_successful = False

    def _check_if_logged_in(self):

        try:
            logged_in_sign = self.browser.select("#bonus-card-bar div .right p span")[0].text.strip()
            if logged_in_sign.startswith("Hi"):
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def _check_error(self):
        card_number_error_selector = ".contact .alertInfo p"

        try:
            card_number_error = self.browser.select(card_number_error_selector)[0].text

            if card_number_error == "Sorry, that does not appear to be a valid Bonus Card number":
                raise LoginError(STATUS_LOGIN_FAILED)
            elif card_number_error == "Please check your password":
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception
        except:
            pass

    def login(self, credentials):
        self.open_url('https://www.iceland.co.uk/bonus-card/my-bonus-card/')

        login_form = self.browser.get_forms()[2]
        login_form['cardNumber'].value = credentials['card_number']
        self.browser.submit_form(login_form)
        self._check_error()

        login_form = self.browser.get_forms()[2]
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)
        self._check_error()

        self._check_if_logged_in()

    def balance(self):
        self.open_url("https://www.iceland.co.uk/bonus-card/my-bonus-card/card-balance/")

        card_balance_selector = ".alertInfo p strong"
        card_balance = self.browser.select(card_balance_selector)[0].text
        card_balance = extract_decimal(card_balance)
        return {
            'points': card_balance,
            'value': card_balance,
            'value_label': '£{}'.format(card_balance)
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
