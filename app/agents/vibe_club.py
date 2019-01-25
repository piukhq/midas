import re
from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal


class VibeClub(RoboBrowserMiner):
    is_login_successful = False
    points_re = re.compile(r'points balance is [^=.]*')
    balance_re = re.compile(r'cash balance is [^=.]*')

    def login(self, credentials):
        form = 'https://www.boostjuicebars.co.uk/api/vibe/user.php'
        headers = {
            'email': credentials['email'],
            'pass': credentials['password'],
            'X-Requested-With': 'XMLHttpRequest'
        }
        self.open_url(
            form,
            method='post',
            headers=headers)
        self.check_if_logged_in()

    def check_if_logged_in(self):
        status = self.browser.response.json()['Success']
        if status == 1:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        points_text = self.browser.response.json()['Points']
        points = extract_decimal(points_text)
        value_text = self.browser.response.json()['Money']
        value = extract_decimal(value_text)

        return {
            'points': points,
            'value': value,
            'value_label': '${}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
