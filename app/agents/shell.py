from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow
# TODO: add STATUS_ACCOUNT_LOCKED
# TODO: add transaction handling


class Shell(Miner):
    point_conversion_rate = Decimal('0.005')

    def login(self, credentials):
        """
        user name is card number
        """
        self.open_url("https://www.shellsmart.com/smart/login?site=en-en")
        signup_form = self.browser.get_form(id='login_page_form')
        signup_form['cardnumber'].value = credentials['email']
        signup_form['password'].value = credentials['password']

        self.browser.submit_form(signup_form)

        selector = "#error_message_container_u49"
        self.check_error("/smart/login",
                         ((selector, STATUS_LOGIN_FAILED, "We do not recognise the details you have input"), ))

    def balance(self):
        points = extract_decimal(self.browser.select("#detail_point_amount")[0].contents[0])
        value = self.calculate_point_value(points)

        return {
            "points": points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[0].select("span")[0].contents[0].strip(), 'DD/MM/YYYY'),
            "description": items[1].select("span")[0].contents[0].strip(),
            "points": extract_decimal(items[2].select("span")[0].contents[0].strip()),
        }

    def scrape_transactions(self):
        return self.browser.select("#points_collected_table tr")[1:]
