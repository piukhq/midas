from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, INVALID_MFA_INFO
from app.utils import extract_decimal
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED


class Tesco(Miner):
    retry_limit = 3

    def login(self, credentials):
        self.open_url("https://secure.tesco.com/register/default.aspx")

        signup_form = self.browser.get_form(id='fSignin')
        signup_form['loginID'].value = credentials['email']
        signup_form['password'].value = credentials['password']

        self.browser.submit_form(signup_form)

        self.check_error("/register/default.aspx",
                         (('#fSignin > fieldset > div > div > p', STATUS_LOGIN_FAILED,
                           "Sorry the email and/or password"), ))

        # cant just go strait to url as its just a meta refresh
        self.browser.open("https://secure.tesco.com/clubcard/myaccount/home.aspx")

        digit_form = self.browser.get_form(id='aspnetForm')

        fields = self.browser.select(".security_questions .textfield")
        card_number = credentials['card_number']
        digit_form['ctl00$PageContainer$txtSecurityAnswer1'].value = card_number[self.digit_index(fields[0])]
        digit_form['ctl00$PageContainer$txtSecurityAnswer2'].value = card_number[self.digit_index(fields[1])]
        digit_form['ctl00$PageContainer$txtSecurityAnswer3'].value = card_number[self.digit_index(fields[2])]

        self.browser.submit_form(digit_form)

        self.check_error("/Clubcard/MyAccount/SecurityStage/HomeSecurityLayer.aspx",
                         (("#ctl00_PageContainer_spnError", INVALID_MFA_INFO, "The details you have entered do not"), ))

    @staticmethod
    def digit_index(field):
        return int(field.select("span")[0].contents[0]) - 1

    def balance(self):
        balances = self.browser.select(".pointsbox h4")

        return {
            "points": extract_decimal(balances[0].contents[0].strip()),
            "value": extract_decimal(balances[1].contents[2].strip())
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[1].contents[0].strip(), 'DD/MM/YYYY'),
            "description": items[2].contents[0].strip(),
            "points": extract_decimal(items[4].contents[0].strip()),
        }

    def transactions(self):
        self.open_url("https://secure.tesco.com/Clubcard/MyAccount/Points/PointsDetail.aspx")
        rows = self.browser.select("table.tbl tr")[1:-1]
        return [self.hashed_transaction(row) for row in rows]



