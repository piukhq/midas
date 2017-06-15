from app.agents.base import Miner
from app.agents.exceptions import LoginError, STATUS_LOGIN_FAILED
from app.utils import extract_decimal
from decimal import Decimal
import arrow


class Harrods(Miner):
    point_conversion_rate = Decimal('0.01')

    def login(self, credentials):
        self.open_url('https://secure.harrods.com/account/en-gb/signin')

        login_form = self.browser.get_forms()[2]
        login_form['EmailAddress'] = credentials['email']
        login_form['Password'] = credentials['password']

        self.headers['Host'] = 'secure.harrods.com'
        self.headers['Origin'] = 'https://secure.harrods.com'
        self.headers['Referer'] = 'https://secure.harrods.com/' \
                                  'account/en-gb/signin'
        self.headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) ' \
                                     'AppleWebKit/537.36 (KHTML, like Gecko)' \
                                     ' Chrome/53.0.2785.143 Safari/537.36'

        self.browser.submit_form(login_form)

        if self.is_login_successful() is False:
            raise LoginError(STATUS_LOGIN_FAILED)

    def is_login_successful(self):
        return 'is-authenticated' in self.browser.select('body')[
            0].attrs['class']

    def balance(self):
        points = extract_decimal(self.browser.select(
            '.rewards-status_item-value--points')[0].contents[0])
        value = self.calculate_point_value(points)

        return {
            'points': points,
            'value': value,
            'value_label': '£{}'.format(value)
        }

    @staticmethod
    def parse_transaction(row):
        return {
            'date': arrow.get(row[0], 'DD/MM/YYYY'),
            'description': row[1],
            'points': row[2],
        }

    def scrape_transactions(self):
        self.open_url('https://secure.harrods.com/account/en-gb/your-orders/index')
        transactions = self.browser.select('li.table_item')
        transaction_list = []
        for transaction in transactions:
            data = transaction.select('ul.order_detail-list > li.order_detail-item > div.order_detail-value')
            status = data[5].contents[0].strip()
            order_number = data[1].contents[0].strip()
            detail_page_prefix = 'https://secure.harrods.com/account/en-gb/your-orders/getorderdetails?orderNumber='
            order_detail_page = detail_page_prefix + order_number

            self.open_url(order_detail_page)
            date = data[0].contents[0].strip()
            description = order_number + ' - ' + status
            total_selector = 'li.oitem_detail-item--total > div.oitem_detail-value > div.price > span.price_amount'
            total_value = extract_decimal(self.browser.select(total_selector)[0].contents[0])
            points = round(total_value, 0)

            transaction_list.append([
                date,
                description,
                points,
            ])

        return transaction_list
