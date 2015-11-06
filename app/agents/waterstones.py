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
        points = extract_decimal(self.browser.select('div.span4 span')[0].text)
        value = extract_decimal(self.browser.select('div.span12 h2')[0].text)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    def transactions(self):
        return None