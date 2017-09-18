from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED


class Superdrug(RoboBrowserMiner):
    def login(self, credentials):
        self.open_url("https://www.superdrug.com/login")
        signup_form = self.browser.get_form(id='loginForm')
        signup_form['j_username'].value = credentials['email']
        signup_form['j_password'].value = credentials['password']

        headers = {'Referer': 'https://www.superdrug.com/login'}
        self.browser.submit_form(signup_form, headers=headers)

        errors = (("#globalMessages > div > div > p", STATUS_LOGIN_FAILED, "Your username or password was incorrect"), )
        self.check_error("loginError=true", errors, url_part="query")

    def balance(self):
        value_box = self.browser.select(".greybg")

        if value_box:
            value = extract_decimal(value_box[0].contents[0])
        else:
            value = Decimal('0')

        return {
            "points": extract_decimal(self.browser.select(".bc_points")[0].contents[0]),
            "value": value,
            'value_label': '£{}'.format(value),
        }

    # TODO: Parse transactions. Not done yet because there's no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url('https://www.superdrug.com/my-account/orders?acc=1&bc=1')
        t = {
            'date': arrow.get(0),
            'description': 'placeholder',
            'points': Decimal(0),
        }
        return [t]
