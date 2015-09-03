from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
import arrow
# TODO: add STATUS_ACCOUNT_LOCKED
# TODO: add transaction handling


class Shell(Miner):
    def login(self, credentials):
        """
        user name is card number
        """
        self.open_url("https://www.shellsmart.com/smart/login?site=en-en")
        signup_form = self.browser.get_form(id='login_page_form')
        signup_form['cardnumber'].value = credentials['user_name']
        signup_form['password'].value = credentials['password']

        self.browser.submit_form(signup_form)

        self.check_error("/smart/login", "#error_message_container_u49",
                         ((STATUS_LOGIN_FAILED, "The password is incorrect"),
                          (STATUS_LOGIN_FAILED, "This account does not exist"), ))

    def balance(self):
        return {
            "amount": extract_decimal(self.browser.select("#detail_point_amount")[0].contents[0]),
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].select("span")[0].contents[0].strip(), 'DD/MM/YYYY'),
            "title": items[1].select("span")[0].contents[0].strip(),
            "points": extract_decimal(items[2].select("span")[0].contents[0].strip()),
        }

    def transactions(self):

        rows = self.browser.select("#points_collected_table tr")[1:]
        return [self.hashed_transaction(row) for row in rows]

    def account_overview(self):
        return {
            'balance': self.balance(),
            'transactions': self.transactions()
        }
