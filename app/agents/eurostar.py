from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN


class Eurostar(Miner):
    point_conversion_rate = 1 / Decimal('300')

    def login(self, credentials):
        data = {
            'form_build_id': 'form-e_ry4AzklRERsn0JlnLv6a7YeffGMmj9Llrgbb2ozaM',
            'form_id': 'user_account_management_login_or_create_account_form',
            'name': credentials['email'],
            'login_or_create': 'login',
            'pass': credentials['password'],
            'login_form_submit': 'Continue',
        }
        self.browser.open('https://www.eurostar.com/uk-en/login', method='post', data=data)

        # We can't differentiate between a locked account and an incorrect password, because the site shows the same
        # error message for both.
        selector = 'div.item-list > ul.element-errors > li'
        self.check_error('/uk-en/login',
                         ((selector, STATUS_LOGIN_FAILED, 'Sorry'),
                          (selector, STATUS_LOGIN_FAILED, 'You have been locked out of your account.')))

    def balance(self):
        points = extract_decimal(
            self.browser.select('div.pane-you-are-epp-member-markup div.pane-content div.row div.right')[1].text)
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': value,
            'value_label': self.format_label(value, '£20 e-voucher')
        }

    def transactions(self):
        return None
