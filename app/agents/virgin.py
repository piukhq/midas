from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Virgin(Miner):
    def login(self, credentials):
        self.open_url('https://www.virgin-atlantic.com/en/gb/frequentflyer/youraccount/index.jsp?isBooking=false')

        login_form = self.browser.get_form('flyClubLogin')
        login_form['login_uname'] = credentials['username']
        login_form['login_pwd'] = credentials['password']
        self.browser.submit_form(login_form)

        self.check_error('www.virgin-atlantic.com:443',
                         (('#mainContent > div > div > span.errorMessage', STATUS_LOGIN_FAILED, 'Your details'),),
                         'netloc')

    def balance(self):
        points = extract_decimal(self.browser.select('#mainContent div.boxOutsideIndent.boxCopy')[1].contents[0])
        return {
            'points': points,
            'value': Decimal('0'),
            'value_label': '',
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row.contents[1].text.strip(), 'DD MMM YYYY'),
            'description': row.contents[3].text.strip(),
            'points': extract_decimal(row.contents[7].text.strip()),
        }

    def transactions(self):
        rows = self.browser.select('#account table.centerTable.tableCopy.borderPurple.boxContainer tr')[1:]
        return [self.hashed_transaction(row) for row in rows]
