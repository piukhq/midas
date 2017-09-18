from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from decimal import Decimal
import arrow


class TheWorks(RoboBrowserMiner):
    csrf = ''
    barcode = ''
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.open_url('https://wwws-uk2.givex.com/cws30/The_Works/login.html')

        login_form = self.browser.get_form()
        self.csrf = login_form['_csrf'].value

        url = 'https://wwws-uk2.givex.com/cws30/The_Works/login.json'
        data = {
            '_csrf': self.csrf,
            'j_brand': 'The_Works',
            'j_username': credentials['email'],
            'j_password': credentials['password'],
        }
        self.open_url(url, method='post', data=data)

        response = self.browser.response.json()
        if 'errorMessage' in response and response['errorMessage'] == 'Bad Credentials':
            raise LoginError(STATUS_LOGIN_FAILED)

        self.barcode = credentials['barcode']

    def balance(self):
        url = 'https://wwws-uk2.givex.com/cws30/The_Works/checkBalance.json'
        data = {
            'cardNumber': self.barcode,
            '_csrf': self.csrf,
        }

        self.open_url(url, method='post', data=data)
        response = self.browser.response.json()
        points = Decimal(response['pointBalance'])
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row['date'], 'YYYY/MM/DD hh:mm:ss'),
            'description': row['outlet'],
            'points': Decimal(row['amount']),
        }

    def scrape_transactions(self):
        self.open_url('https://wwws-uk2.givex.com/cws30/The_Works/listLoyaltyTransactions.json?colNumber=4'
                      '&cardId=491942751&draw=2&columns%5B0%5D%5Bdata%5D=date&columns%5B0%5D%5Bname%5D=date'
                      '&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=true'
                      '&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false'
                      '&columns%5B1%5D%5Bdata%5D=outlet&columns%5B1%5D%5Bname%5D=outlet'
                      '&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true'
                      '&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false'
                      '&columns%5B2%5D%5Bdata%5D=level&columns%5B2%5D%5Bname%5D=level'
                      '&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=true'
                      '&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false'
                      '&columns%5B3%5D%5Bdata%5D=amount&columns%5B3%5D%5Bname%5D=amount'
                      '&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=true'
                      '&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false'
                      '&order%5B0%5D%5Bcolumn%5D=0&order%5B0%5D%5Bdir%5D=asc&start=0&length=100&search%5Bvalue%5D='
                      '&search%5Bregex%5D=false&_=1447758480356')

        data = self.browser.response.json()
        return data['data']
