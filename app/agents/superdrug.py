from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal

# TODO: add STATUS_ACCOUNT_LOCKED


class Superdrug(Miner):
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
        value = extract_decimal(self.browser.select(".greybg")[0].contents[0])
        return {
            "points": extract_decimal(self.browser.select(".bc_points")[0].contents[0]),
            "value": value,
            'value_label': '£{}'.format(value),
        }

    def transactions(self):
        return None
