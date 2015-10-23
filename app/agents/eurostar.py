from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Eurostar(Miner):
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

        selector = 'div.messages.error > ul > li'
        self.check_error('/uk-en/login', ((selector, STATUS_LOGIN_FAILED, 'Sorry'),))

    def balance(self):
        point_holder = self.browser.select('div.pane-you-are-epp-member-markup div.pane-content div.row div.right')[1]
        return {
            'points': extract_decimal(point_holder.text)
        }

    def transactions(self):
        return None
