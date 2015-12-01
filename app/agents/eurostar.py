from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED, STATUS_ACCOUNT_LOCKED, IP_BLOCKED
from app.utils import extract_decimal
from decimal import Decimal, ROUND_DOWN


class Eurostar(Miner):
    point_conversion_rate = 1 / Decimal('300')

    def determine_login_failure(self, credentials):
        self.open_url('http://www.eurostar.com/uk-en/loyalty-programmes')
        login_form = self.browser.get_form('user-account-management-member-login-form')
        login_form['name'] = credentials['email']
        login_form['pass'] = credentials['password']
        self.browser.submit_form(login_form)

        # URLs for correct and incorrect login are identical, so check_error won't work.
        message_box = self.browser.select('#content > div > div.panel-pane.pane-page-messages > div > div')
        if message_box:
            message = message_box[0].text.strip()
            if message.startswith('Error message\nSorry, we don\'t recognise that username or password.'):
                raise LoginError(STATUS_LOGIN_FAILED)
            elif message.startswith('Error message\nSorry, there have been more than 5 failed login'):
                raise LoginError(STATUS_ACCOUNT_LOCKED)
            elif message.startswith('Error message\nSorry, too many failed login attempts'):
                raise LoginError(IP_BLOCKED)

    def login(self, credentials):
        data = {
            'form_build_id': 'form-e_ry4AzklRERsn0JlnLv6a7YeffGMmj9Llrgbb2ozaM',
            'form_id': 'user_account_management_login_or_create_account_form',
            'name': credentials['email'],
            'login_or_create': 'login',
            'pass': credentials['password'],
            'login_form_submit': 'Continue',
        }
        self.open_url('https://www.eurostar.com/uk-en/login', method='post', data=data)

        # If we've failed to log in, figure out why.
        message_box = self.browser.select('div.item-list > ul.element-errors > li')
        if message_box:
            message = message_box[0].text.strip()
            if message.startswith('Sorry') or message.startswith('You have been locked out of your account.'):
                self.determine_login_failure(credentials)

    def balance(self):
        points = extract_decimal(
            self.browser.select('div.pane-you-are-epp-member-markup div.pane-content div.row div.right')[1].text)
        value = self.calculate_point_value(points).quantize(0, ROUND_DOWN)

        return {
            'points': points,
            'value': value,
            'value_label': self.format_label(value, '£20 e-voucher')
        }

    def scrape_transactions(self):
        return None
