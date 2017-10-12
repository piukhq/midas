from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal


class AerClub(RoboBrowserMiner):
    is_login_successful = False
    login_login_json_response = None

    def _check_if_logged_in(self):
        try:
            self.login_json_response = self.browser.response.json()
            status = self.login_json_response['statusCode']
            if status == 'success':
                self.is_login_successful = True
            else:
                raise LoginError(STATUS_LOGIN_FAILED)
        except LoginError as exception:
            raise exception

    def _login(self, credentials):
        url = "https://www.aerlingus.com/api/profile/loyalty/login"
        data = {
            'userName': credentials['email'],
            'password': credentials['password']
        }
        import pdb; pdb.set_trace()
        self.browser.open(url, method='POST', json=data)

    def login(self, credentials):
        self._login(credentials=credentials)
        self._check_if_logged_in()

    def balance(self):
        points = Decimal(self.login_json_response['data'][0]['frequentFlyer']['balance'])
        balance = Decimal(self.login_json_response['data'][0]['frequentFlyer']['tierCredits'])

        return {
            'points': points,
            'value': balance,
            'value_label': ''
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        self.open_url('https://www.aerlingus.com/api/profile/transactions')

        return self.browser.response.json()['data'][0]['transactions']
