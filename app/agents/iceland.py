from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, WRONG_CREDENTIAL_TYPE
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

    def _get_card_number(self, credentials):
        if 'barcode' in credentials:
            card_number = credentials['barcode']
        elif 'card_number' in credentials:
            card_number = credentials['card_number']
        else:
            raise LoginError(WRONG_CREDENTIAL_TYPE)

        if len(card_number) == 24:
            card_number = card_number[:-5]

        generic_card_prefix = "63320400"
        if card_number.startswith(generic_card_prefix):
            card_number = card_number[len(generic_card_prefix):]

        return card_number

    def login(self, credentials):
        self.open_url('https://www.iceland.co.uk/bonus-card/my-bonus-card/')

        card_number = self._get_card_number(credentials)
        login_form = self.browser.get_forms()[2]
        login_form['cardNumber'].value = card_number
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
