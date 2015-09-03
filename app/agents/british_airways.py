from decimal import Decimal
import time
from app.agents.base import Miner

class BritishAirways(Miner):
    # TODO: REPLACE WITH REAL LIMIT
    retry_limit = 3

    def login(self, credentials):
        self.open_url("https://www.britishairways.com/travel/loginr/public/en_gb")

        login_form = self.browser.get_form(id='loginrForm')
        login_form['membershipNumber'].value = credentials['card_number']
        login_form['password'].value = credentials['password']
        login_form.action = '?eId=109001'
        self.browser.submit_form(login_form)

    def balance(self):
        points_span = self.browser.select('.nowrap')[0]
        points = points_span.text.strip('My Avios:  |').strip().replace(',', '')
        points_amount = Decimal(points)

        return {
            "amount": points_amount
        }

    def transactions(self):
        self.browser.session.headers['Accept'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        self.browser.session.headers['Accept-Encoding'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        self.browser.session.headers['Accept-Language'] = "en-US,en;q=0.8"
        self.browser.session.headers['Connection'] = "keep-alive"
        self.browser.session.headers['Host'] = "www.britishairways.com"
        self.browser.session.headers['Referer'] = "https://www.britishairways.com/travel/viewtransaction/execclub/_gf/en_gb?eId=172705"
        self.browser.session.headers['Upgrade-Insecure-Requests'] = "1"
        self.browser.session.headers['User-Agent'] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
        self.open_url("https://www.britishairways.com/travel/viewtransaction/execclub/_gf/en_gb")
        self.view()
        time.sleep(5)
        self.browser.session.headers['Accept'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        self.browser.session.headers['Accept-Encoding'] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
        self.browser.session.headers['Accept-Language'] = "en-US,en;q=0.8"
        self.browser.session.headers['Connection'] = "keep-alive"
        self.browser.session.headers['Host'] = "www.britishairways.com"
        self.browser.session.headers['Referer'] = "https://www.britishairways.com/travel/viewtransaction/execclub/_gf/en_gb?eId=172705"
        self.browser.session.headers['Upgrade-Insecure-Requests'] = "1"
        self.browser.session.headers['User-Agent'] = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36"
        #print(self.browser.url)
        self.open_url("https://www.britishairways.com/travel/viewtransaction/execclub/_gf/en_gb?eId=172705b")
        self.view()


        html = self.browser.response.text
        table = self.browser.find("table", {"id": "recentTransTbl"})
        rows = self.browser.select("#recentTransTbl")#[1:-1]
        print(rows)
        return [self.hashed_transaction(row) for row in rows]

    @staticmethod
    def parse_transaction(row):
        pass
