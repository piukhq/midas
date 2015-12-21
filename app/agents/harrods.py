from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import json
import arrow


class Harrods(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        query = 'https://www.harrods.com/UIServices/Account/AccountService.svc/Signin'
        data = {
            'email': credentials['email'],
            'password': credentials['password'],
        }

        self.open_url(query, method='post', json=data, read_timeout=15)
        response = json.loads(self.browser.response.text)

        if not response['d']['isValid']:
            raise LoginError(STATUS_LOGIN_FAILED)

        self.open_url('https://www.harrods.com/Pages/Account/Secure/AccountHome.aspx')

    def balance(self):
        points = extract_decimal(self.browser.select('div.myaccount_option_boxes_inner p')[2].contents[10])
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        data = row.select('td')
        return {
            'date': arrow.get(data[0].contents[0], 'DD-MM-YYYY'),
            'description': data[1].contents[0],
            'points': extract_decimal(data[4].contents[0]),
        }

    def scrape_transactions(self):
        self.open_url('https://www.harrods.com/Pages/Account/Secure/StatementTransactions.aspx')

        search_form = self.browser.get_form('aspnetForm')
        search_form['__EVENTTARGET'].value = 'ctl00$ContentPlaceHolder1$btnSearchTransactions'
        search_form['ctl00$ContentPlaceHolder1$ddlTransactionType'].value = 'PurchasesAndRefunds'
        search_form['ctl00$ContentPlaceHolder1$txtDateFrom'].value = '01/01/2007'
        search_form['ctl00$ContentPlaceHolder1$txtDateTo'].value = arrow.utcnow().replace(days=-1).format('DD/MM/YYYY')
        self.browser.submit_form(search_form)

        return self.browser.select('table.statements > tr')[1::2]
