from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal


class Avis(Miner):
    def login_failed(self, credentials):
        query = "https://secure.avis.co.uk/JsonProviderServlet/" \
                "?requestType=updateTncStatus"
        data = {"id": credentials["email"], "password": credentials["password"]}
        self.open_url(query, method="POST", data=data)
        response = self.browser.response.json()
        key = "errorMessage"
        if key not in response.keys():
            raise ValueError(
                "The response does not contain mandatory key \"%s\"." % key)
        else:
            if response[key] is None:
                # empty error= successful login
                return False

        expected_error_message = "Sorry, your email address and password " \
                                 "don't match."
        error = response[key]
        if expected_error_message in error:
            return True
        else:
            raise ValueError(
                "Error message does not contain \"%s\"." % expected_error_message)

    @staticmethod
    def get_value_from_balance_response(response, key, fallback):
        if key not in response.keys():
            raise ValueError("The response does not contain mandatory key "
                             "\"%s\" and cannot continue without it." % key)
        else:
            value = response[key]
            if value is None:
                value = fallback
        return value

    def login(self, credentials):
        query = 'https://www.avis.co.uk/loyalty-statement'
        data = {
            'require-login': 'true',
            'login-email': credentials['email'],
            'login-hidtext': credentials['password'],
        }

        self.open_url(query, method='post', data=data)

        if self.login_failed(credentials):
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        self.browser.open(
            "https://secure.avis.co.uk/JsonProviderServlet/?requestType=userdetails")
        response = self.browser.response.json()
        points = self.get_value_from_balance_response(response, "rentals", 0.0)
        value = self.get_value_from_balance_response(response, "rentalsSpent",
                                                     "0.00")

        return {
            'points': Decimal(points),
            'value': extract_decimal(value),
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
