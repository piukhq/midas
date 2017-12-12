from app.agents.base import SeleniumMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, UNKNOWN
from app.utils import extract_decimal
from decimal import Decimal


class SpaceNK(SeleniumMiner):
    point_conversion_rate = Decimal('0.05')
    is_login_successful = False

    def check_if_logged_in_and_get_balance(self):
        current_url = self.browser.current_url
        success_login_url = "https://www.spacenk.com/uk/en_GB/account?login=true"
        if current_url == success_login_url:
            self.is_login_successful = True
        else:
            raise LoginError(STATUS_LOGIN_FAILED)

        points_url = "https://www.spacenk.com/uk/en_GB/ndulgeaccount"
        self.browser.get(points_url)
        self.points = extract_decimal(self.browser.find_element_by_id("pointsbalance").text)
        self.balance_value = extract_decimal(self.browser.find_element_by_id("certbalance").text)

    def login(self, credentials):
        self.browser.get('https://www.spacenk.com/uk/en_GB/account')
        self.browser.find_element_by_css_selector("form input[type='email']").send_keys(credentials['email'])
        self.browser.find_element_by_css_selector("form input[type='password']").send_keys(credentials['password'])
        self.browser.find_element_by_name('dwfrm_login_login').click()

        self.check_if_logged_in_and_get_balance()

    def balance(self):
        value = self.calculate_point_value(self.points)
        return {
            'points': self.points,
            'value': value,
            'value_label': '£{}'.format(value),
            'balance': self.balance_value
        }

    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        return []
