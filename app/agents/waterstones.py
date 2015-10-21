from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal


class Waterstones(Miner):
    def login(self, credentials):
        self.open_url('https://www.waterstones.com/signin')

        login_form = self.browser.get_form('loginForm')
        login_form['email'].value = credentials['email']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = 'p.error'
        self.check_error('/signin', ((selector, STATUS_LOGIN_FAILED, 'Your login details are invalid'),))

    def balance(self):
        self.open_url('https://www.waterstones.com/account/waterstonescard')
        point_holder = self.browser.select('div.span4 span')[0]
        value_holder = self.browser.select('div.span12 h2')[0]
        return {
            'points': extract_decimal(point_holder.text),
            'value': extract_decimal(point_holder.text)
        }

    def transactions(self):
        raise None