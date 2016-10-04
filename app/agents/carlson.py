from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Carlson(Miner):
    def login(self, credentials):
        url = "https://www.clubcarlson.com/secure/login.do"
        data = {
            "accountEmail": "",
            "linkToken": "",
            "successURL": "https://www.clubcarlson.com/myaccount/secure/?login=true",
            "rightSide": "",
            "userId": credentials["username"],
            "password": credentials["password"],
            "rememberMe": "true",
        }
        self.open_url(url, method="post", data=data)

        self.check_error("/secure/login.do",
                         (("div.globalerrors", STATUS_LOGIN_FAILED, "Your email or password"), ))

    def balance(self):
        points = extract_decimal(self.browser.select("span.goldpointsBalance")[0].text)

        reward = self.calculate_tiered_reward(points, [
            (105000, "Premium award night, category 7"),
            (45000, "Premium award night, category 6"),
            (70000, "Standard award night, category 7"),
            (66000, "Premium award night, category 5"),
            (50000, "Standard award night, category 6"),
            (44000, "Standard award night, category 5"),
            (42000, "Premium award night, category 3"),
            (38000, "Standard award night, category 4"),
            (24000, "Standard award night, category 3"),
            (22500, "Premium award night, category 2"),
            (15000, "Standard award night, category 2"),
            (13500, "Premium award night, category 1"),
            (9000, "Standard award night, category 1"),
        ])

        return {
            "points": points,
            "value": Decimal("0"),
            "value_label": reward,
        }

    # TODO: Parse transactions. Not done yet because there"s no transaction data in the account.
    @staticmethod
    def parse_transaction(row):
        return row

    def scrape_transactions(self):
        # self.open_url("https://www.clubcarlson.com/myaccount/secure/loyalty/transactionHistory.do")
        t = {
            "date": arrow.get(0),
            "description": "placeholder",
            "points": Decimal(0),
        }
        return [t]
