from app.agents.base import ApiMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal


class EsquiresCoffee(ApiMiner):
    is_login_successful = False

    def check_if_logged_in(self):
        login_fail = self.response.json()['error']

        if not login_fail:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def authorization(self):
        try:
            api_key = self.response.json()['apiKey']

            self.headers['Accept'] = "application/json, text/plain, */*"
            self.headers['Authorisation'] = api_key
            self.headers['Host'] = 'www.loylap.com'
            self.headers['Referer'] = 'https://www.loylap.com/customer_portal/'
            self.headers['Source'] = 'web'
            self.make_request('https://www.loylap.com/api/v1/user', headers=self.headers)
        except Exception:
            raise LoginError(STATUS_LOGIN_FAILED)

    def _login(self, credentials):
        url = "https://www.loylap.com/api/v1/userLogin"
        data = {
            "email": credentials['email'],
            "password": credentials['password']
        }
        self.response = self.make_request(url, method="post", data=data)

    def login(self, credentials):
        self._login(credentials)
        self.check_if_logged_in()

        if self.is_login_successful:
            self.authorization()

    def balance(self):
        response = self.make_request('https://www.loylap.com/api/v1/groupsByUserLoyalty',
                                     headers=self.headers)
        json_response = response.json()
        value = json_response['loyalty'][0]['cash_balance']

        return {
            'points': Decimal(value),
            'value': Decimal(value),
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
