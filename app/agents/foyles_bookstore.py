from app.agents.base import Miner
from app.agents.exceptions import STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class FoylesBookstore(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.open_url('http://www.foyalty.co.uk/Default.aspx')

        login_form = self.browser.get_form('aspnetForm')
        login_form['ctl00$HeaderInfo$txtUserID'].value = credentials['barcode']
        login_form['ctl00$HeaderInfo$txtPassword'].value = credentials['email']
        self.browser.submit_form(login_form)

        self.check_error('/default.aspx',
                         (('#ctl00_HeaderInfo_lblErrors', STATUS_LOGIN_FAILED, 'Incorrect Username or Password'), ))

    def balance(self):
        points = extract_decimal(self.browser.select('#ctl00_ctl00_HeaderInfo_lblUserLogged')[0].text.strip())
        value = self.calculate_point_value(points)
        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')

        return {
            'date': arrow.get(data[1].text, 'DD/MM/YYYY'),
            'description': data[7].text,
            'points': extract_decimal(data[5].text),
            'value': extract_decimal(data[4].text),
            'location': data[3].text,
        }

    def scrape_transactions(self):
        self.open_url('http://www.foyalty.co.uk/MyCards_Transactions.aspx')
        return self.browser.select('#ctl00_ctl00_HeaderInfo_PageDetails_GridView1 > tr')[1:]
