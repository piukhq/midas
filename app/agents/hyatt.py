from app.agents.base import Miner


class Hyatt(Miner):
    def login(self, credentials):
        self.open_url('https://www.hyatt.com/gp/en/index.jsp')

        login_form = self.browser.get_form('signin')
        login_form['username'].value = credentials['username']
        login_form['password'].value = credentials['password']
        self.browser.submit_form(login_form)
        self.view()
