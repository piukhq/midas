from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Eurostar(Miner):
    def login(self, credentials):
        self.open_url('https://www.eurostar.com/uk-en/login')

        login_form = self.browser.get_form('user-account-management-login-or-create-account-form')
        login_form['name'].value = credentials['email']
        login_form['pass'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'div.messages.error > ul > li'
        self.check_error('/uk-en/login', ((selector, STATUS_LOGIN_FAILED, 'Sorry'),))

    def balance(self):
        self.open_url('https://www.eurostar.com/uk-en/account')
        point_holder = self.browser.select('div.pane-you-are-epp-member-markup div.pane-content div.row div.right')
        return {
            'points': extract_decimal(point_holder.text)
        }

    def transactions(self):
        return None
