from app.agents.base import Miner
from app.agents.exceptions import LoginError, END_SITE_DOWN, STATUS_LOGIN_FAILED
from decimal import Decimal

class Greggs(Miner):
    def login(self, credentials):
        url = 'https://www.greggs.co.uk/Security/login?BackURL=%2Fhome%2F&ajax=1'
        self.open_url(url)

        if self.browser.response.status_code != 200:
            raise LoginError(END_SITE_DOWN)

        login_form = self.browser.get_form(id='AccountLoginForm_LoginForm')
        login_form['Email'].value = credentials['email']
        login_form['Password'].value = credentials['password']

        self.browser.submit_form(login_form)

        selector = '#AccountLoginForm_LoginForm_error'
        self.check_error('/Security/login', ((selector, STATUS_LOGIN_FAILED, "The details you entered don't seem"),))

    def balance(self):
        self.open_url('https://www.greggs.co.uk/my-account/my-coffees#content_start')
        coffees = self.browser.select('ul#coffee li')
        return {
            'points': Decimal(len([x for x in coffees if 'done' in x.attrs['class']])),
        }

    def transactions(self):
        return None
