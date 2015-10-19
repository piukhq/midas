from app.agents.base import Miner
from app.agents.exceptions import LoginError, END_SITE_DOWN, STATUS_LOGIN_FAILED
from app.utils import extract_decimal

class Debenhams(Miner):
    def login(self, credentials):
        url = 'https://portal.prepaytec.com/chopinweb/scareMyLogin.do?customerCode=452519111525&loc=en&brandingCode=myscare_uk'
        self.open_url(url)

        if self.browser.response.status_code != 200:
            raise LoginError(END_SITE_DOWN)

        login_form = self.browser.get_form('login')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']

        self.browser.submit_form(login_form)

        # Obtain the memorable date form.
        date_form = self.browser.get_form('login')

        # The first 12 cells are just for formatting.
        date_table = self.browser.select("table.memorable tr td")[12:]
        correct = credentials['memorable_date']
        index = 0

        for cell in date_table:
            # Cells with an input field contain three elements, others just one.
            if len(cell.contents) == 3:
                input = cell.contents[1]
                date_form[input.attrs['name']] = correct[index]

            index += 1

        self.browser.submit_form(date_form)

        selector = '#login > p.error'
        self.check_error('/chopinweb/scareMyLogin.do', ((selector, STATUS_LOGIN_FAILED, 'Please correct the following errors'),))

    def balance(self):
        self.open_url('https://portal.prepaytec.com/chopinweb/scareMyStatement.do')
        points_span = self.browser.select("td#clearedBalance span.balanceValue")[1]
        return {
            "points": extract_decimal(points_span.text)
        }