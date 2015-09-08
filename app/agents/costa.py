from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED
# TODO: add negative transaction handling


class Costa(Miner):
    def login(self, credentials):
        self.open_url("https://www.costa.co.uk/coffee-club/login/")
        signup_form = self.browser.get_form(id='menuSearchForm')
        signup_form['ctl00$ctl00$ctl00$ContentPlaceHolderDefault$ContentPlaceHolder'
                    'Body$LoginRegister_9$txtUsernameLoginForm'].value = credentials['user_name']
        signup_form['ctl00$ctl00$ctl00$ContentPlaceHolderDefault$ContentPlaceHolder'
                    'Body$LoginRegister_9$txtPasswordLoginForm'].value = credentials['password']

        submit = signup_form.submit_fields["ctl00$ctl00$ctl00$ContentPlaceHolderDefault$ContentPlaceHolderBody$LoginRegister_9$btnCCLogin"]
        self.browser.submit_form(signup_form, submit=submit)

        self.check_error("/coffee-club/login/", (
            ("#ResponseMessage p", STATUS_LOGIN_FAILED, "Sorry, your username and password are incorrect"),
            ("#lblCaptcha", STATUS_LOGIN_FAILED, "reCAPTCHA selection is invalid"), ))

    def balance(self):
        return {
            "amount": extract_decimal(self.browser.find(id="txtCounterValue").attrs["value"]),
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].contents[0], 'DD-MM-YYYY'),
            "description": "{0} - {1}".format(items[1].contents[0], items[2].contents[0]),
            "points": extract_decimal(items[3].contents[0].strip()),
        }

    def transactions(self):
        self.open_url("https://www.costa.co.uk/coffee-club/card-usage/")

        rows = self.browser.select("#grdHistory tr")[1:]
        return [self.hashed_transaction(row) for row in rows]
