from app.agents.base import Miner
from app.utils import extract_decimal
from decimal import Decimal


class Virgin(Miner):
    def login(self, credentials):
        self.open_url('https://www.virgin-atlantic.com/en/gb/frequentflyer/youraccount/index.jsp?isBooking=false')

        login_form = self.browser.get_form('flyClubLogin')
        login_form['login_uname'] = credentials['username']
        login_form['login_pwd'] = credentials['password']
        self.browser.submit_form(login_form)

    def balance(self):
        points = extract_decimal(self.browser.select('#mainContent div.boxOutsideIndent.boxCopy')[1].contents[0])
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

#    def transactions(self):
#        rows = self.browser.select('#account table.centerTable.tableCopy.borderPurple.boxContainer')