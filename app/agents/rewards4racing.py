from app.agents.base import RoboBrowserMiner
from app.agents.exceptions import STATUS_LOGIN_FAILED, LoginError
from app.utils import extract_decimal
import arrow
import re


class Rewards4Racing(RoboBrowserMiner):
    point_balance_pattern = r'Totalpointspending\:(\d+)'
    point_value_pattern = r'\,worth(£\d+\.\d+)Missing'

    def set_headers(self):
        self.headers['Host'] = 'www.rewards4racing.com'
        self.headers['Origin'] = 'https://www.rewards4racing.com'
        self.headers['Referer'] = 'https://www.rewards4racing.com/'
        self.headers['X-MicrosoftAjax'] = 'Delta=true'
        self.headers['X-Requested-With'] = 'XMLHttpRequest'

    def get_data(self, credentials):
        self.open_url('https://www.rewards4racing.com/Home/')
        login_form = self.browser.get_form('form1')
        data = {}
        for field in list(login_form.keys()):
            data[field] = str(login_form[field].value)

        data['__EVENTTARGET'] = 'ctl00$signin$lnkSignIn'
        data['ctl00$activate$txtConfirmPass'] = ''
        data['ctl00$activate$txtEmailAddress'] = ''
        data['ctl00$activate$txtPassword'] = ''

        data['ctl00$ContentPlaceHolder1$modulecontainer$default.'
             'aspx_0_636071242123030000_default.aspx_0$txtSearch'] = ''
        data['ctl00$ContentPlaceHolder1$modulecontainer$default.'
             'aspx_10_636058356321030000_default.aspx_10$hidKey'] = 'CompEmailCapture'
        data['ctl00$ContentPlaceHolder1$modulecontainer$default.'
             'aspx_10_636058356321030000_default.aspx_10$txtEmailAddress'] = ''
        data['ctl00$modulecontainer$default.aspx_0_636046966323400000_default.aspx_0$hidKey'] = 'newsletter_homepage'
        data['ctl00$modulecontainer$default.aspx_0_636046966323400000_default.aspx_0$txtEmailAddress'] = ''
        data['ctl00$scriptmanager'] = 'ctl00$signin$udp|ctl00$signin$lnkSignIn'

        data['ctl00$signin$txtEmailAddress'] = credentials['email']
        data['ctl00$signin$txtPassword'] = credentials['password']
        data['__ASYNCPOST'] = 'true'

        data.pop('ctl00$clubSelectPopup$ctl00$btnSubmitClub', None)
        data.pop('ctl00$clubSelectPopup$ctl00$ddlClubSelector', None)
        data.pop('ctl00$signin$chkKeepMeLoggedIn', None)

        return data

    def login(self, credentials):
        url = 'https://www.rewards4racing.com/'
        data = self.get_data(credentials)
        self.set_headers()
        self.open_url(url, method='post', data=data)

        generic_error = str(self.browser.select('#signin_pnlGenericError'))

        if 'There was a problem signing you into your account' in generic_error:
            raise LoginError(STATUS_LOGIN_FAILED)

    def balance(self):
        # Despite the fact that this site is a copy-paste job identical to two others, they somehow managed to end up
        # with malformed HTML in this one's point balance, so we have to regex it.
        self.open_url('https://www.rewards4racing.com/my-account')
        pretty_html = self.browser.select('.home-stats')[0].text.strip()\
            .replace('\n', '').replace('\r', '').replace(' ', '')

        value = extract_decimal(re.findall(self.point_value_pattern, pretty_html)[0])

        return {
            'points': extract_decimal(re.findall(self.point_balance_pattern, pretty_html)[0]),
            'value': value,
            'value_label': '£{}'.format(value),
        }

    @staticmethod
    def parse_transaction(row):
        def get_pending_description(transaction):
            pending_message = data[3].contents[1].text
            activate_date = data[2].text.replace(' ', '')
            if pending_message == 'PENDING':
                description = data[1].text + ' (Points Activate on: ' + activate_date + ')'
                return description
            else:
                raise ValueError('No pending message, assuming points are active')

        data = row.select('p')
        try:
            description = get_pending_description(row)

        except Exception:
            description = data[1].text

        t = {
            'date': arrow.get(data[0].text.replace(' ', ''), 'DD/MM/YYYY'),
            'description': description,
            'points': extract_decimal(data[3].contents[0].text)
        }

        return t

    def scrape_transactions(self):
        self.open_url('https://www.rewards4racing.com/my-account/points-statement')
        return self.browser.select('div.stmt-repeaterShort div.statement-details')
