from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED, MinerError, UNKNOWN, INVALID_MFA_INFO
from app.utils import extract_decimal
import arrow

# TODO: add STATUS_ACCOUNT_LOCKED
# TODO: add negative transaction handling


class Cooperative(Miner):
    def login(self, credentials):
        for x in range(10):
            self.open_url("https://www.secure.membership.coop/")
            question = self.browser.select("#ctl00_ContentPlaceHolder1_lblQues")[0].contents[0].strip()
            if question.startswith("Place of birth"):
                break
        else:
            # There are only four questions but just in case don't loop for ever
            raise MinerError(UNKNOWN)

        signup_form = self.browser.get_form(id='aspnetForm')
        signup_form['ctl00$ContentPlaceHolder1$txtM2'].value = credentials['card_number'][6:10]
        signup_form['ctl00$ContentPlaceHolder1$txtM3'].value = credentials['card_number'][10:14]
        signup_form['ctl00$ContentPlaceHolder1$txtM4'].value = credentials['card_number'][14:18]
        signup_form['ctl00$ContentPlaceHolder1$txtPostCode'].value = credentials['post_code']
        signup_form['ctl00$ContentPlaceHolder1$txtAns'].value = credentials['place_of_birth']
        # self.browser.select("#ctl00_ContentPlaceHolder1_lblError > li > p")[0].get_text().strip()
        self.browser.submit_form(signup_form)

        selector = "#ctl00_ContentPlaceHolder1_lblError > li > p"
        self.check_error("/MemberLogin.aspx",
                         ((selector, STATUS_LOGIN_FAILED, "Please enter a valid  Card Number"),
                          (selector, INVALID_MFA_INFO, "Please enter a valid  Security Answer"), ))

    def balance(self):
        self.open_url("https://www.secure.membership.coop/MemberPointsSearch.aspx")
        return {
            "amount": extract_decimal(
                self.browser.find(id="ctl00_ContentPlaceHolder1_labelCurrentYearPoints").contents[0]),
        }

    @staticmethod
    def parse_transaction(row):
        items = row.find_all("td")
        return {
            "date": arrow.get(items[2].contents[0].strip(), 'DD MMMM YYYY'),
            "description": items[0].contents[0].strip(),
            "location": items[1].contents[0].strip(),
            "points": extract_decimal(items[3].contents[0].strip()),
        }

    def transactions(self):
        self.open_url("https://www.secure.membership.coop/MemberTransactions.aspx")
        rows = self.browser.select("#gridViewMemberTransactions tr")[1:]
        return [self.hashed_transaction(row) for row in rows]
