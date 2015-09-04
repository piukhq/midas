from app.agents.base import Miner


class Avios(Miner):
    def login(self, credentials):
        self.open_url("https://www.avios.com/gb/en_gb/my-account/log-into-avios")
        login_form = self.browser.get_form(action='/my-account/login-process')
        login_form['j_username'].value = credentials['username']
        login_form['j_password'].value = credentials['password']
        y=login_form
        self.browser.session.headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        self.browser.session.headers['Accept-Encoding'] = 'gzip, deflate'
        self.browser.session.headers['Referer'] = 'https://www.avios.com/gb/en_gb/my-account/log-into-avios?cmsref=%2Flogout.do'
        self.browser.session.headers['Origin'] = 'https://www.avios.com'
        self.browser.session.headers['Host'] = 'www.avios.com'
        self.browser.session.headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self.browser.session.headers['Content-Length'] = 35
        self.browser.session.headers['Cache-Control'] = 'max-age=0'
        self.browser.session.headers['Accept-Language'] = 'en-US,en;q=0.8'
        self.browser.session.headers['Upgrade-Insecure-Requests'] = 1
        self.browser.session.headers['Cookie'] = '''AVLTM=!0EXQYiviSr2y2vVh7X6ibDC882QboVT37jvOYlganyZl6XQbioUovu/aL9vdWGnG2qQfPP/gSRty+w==; Apache=!FgDAtKZiUwWyO6Bh7X6ibDC882QboStSOmfqD/ZUXyteHfph3EAclwC71KN+zIaJylWUuHJ+qVrBvdB8K/gPH8/7Bw==; LocaleCookie=market%3DGB%26locale%3Den_GB%26language%3Den%26country%3DGB; fsr.r=%7B%22d%22%3A90%2C%22i%22%3A%22dc139d7-81694873-3236-7ea2-bba4f%22%2C%22e%22%3A1441887941513%7D; resolution=1920; JSESSIONID=HZ9QVyjGf7yJ1Y221ycQcj0Thv2F02kTjThKHF285nq5QjTb5H1S!1882810163!vangogh!4601!-1; __utmt=1; CICookie=!+rs6cbLJQadlEnFh7X6ibDC882QboS9dvQ30ksFCvAIfVu1vM+uBWTVtLIb1kHypzom4I8KsefUIMCJz7v0jOCEJh7gPJGeU3FHhhAbdh/aAfHGUNoIeiMM8NDU3SIj5Oy50Z+zjs5XP/bgxiFMHstB9EeVHhzmUPjAIIBshjxIIMd5jQALI8v9NabzLo9UDrFS5ENM=; CPCookie=lm%3DN%26locale%3Den_GB%26ec%3DY%26bt%3D0%26tc%3DN%26dm%3DN%26dotw%3DN%26ss%3DNJ%26sd%3D17%26sc%3DY%26sms%3DN%26ct%3D0%26country%3DGB%26cs%3DESTORE%2C%26pd%3DN%26ef%3DN%26market%3DGB%26pa%3DBO4%263p%3DN%26language%3Den%26ph%3DNONE%26gr%3DCAN%27T+CONNECT+TO+DB.%26cc%3D0; asessionid=hSzRVyycfMlDM4vX8NlyvDlTp51YmJN1cL35s6X8k74QLwJwGpTK!-1725469223!vangogh!4402!-1; mmcore.tst=0.132; mmid=-1139529503%7CRwAAAAp3/zMlXwwAAA%3D%3D; mmcore.pd=1930243416%7CRwAAAAoBQnf/MyVfDG2XGtcFAAbVORF1tNJIDwAAAK65BOg4tNJIAAAAAP//////////AA13d3cuYXZpb3MuY29tAl8MBQAAAAAAAAAAAAAiZwAAImcAACJnAAACANJHAAAAG8al418MAP////8BXwxfDP//BAAAAQAAAAABad0AAA8zAQAA/zQAAABCGd62XwwA/////wFfDF8M//8BAAABAAAAAAHGrwAAq+IAAAFttwAAAQAAAAAAAAFF; mmcore.srv=ldnvwcgeu13; mm_pc=Booking%3DNo%26Balance%3DLogged_Out%26Return_Visit%3DNew; mm_vis_session=1; __utma=70402496.1264370353.1441207459.1441290240.1441293269.6; __utmb=70402496.33.10.1441293269; __utmc=70402496; __utmz=70402496.1441268695.2.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); ki_t=1441268695554%3B1441268695554%3B1441294533435%3B1%3B51; ki_r=; fsr.s=%7B%22cp%22%3A%7B%22SuperSegment%22%3A%22None%22%7D%2C%22v2%22%3A1%2C%22v1%22%3A1%2C%22rid%22%3A%22dc139d7-81694873-3236-7ea2-bba4f%22%2C%22ru%22%3A%22https%3A%2F%2Fwww.google.co.uk%2F%22%2C%22r%22%3A%22www.google.co.uk%22%2C%22st%22%3A%22%22%2C%22to%22%3A2.9%2C%22mid%22%3A%22dc139d7-81695201-dd2a-e7fc-b60c7%22%2C%22rt%22%3Afalse%2C%22rc%22%3Atrue%2C%22c%22%3A%22https%3A%2F%2Fwww.avios.com%2Fgb%2Fen_gb%2Fmy-account%2Flogin-error%22%2C%22pv%22%3A51%2C%22lc%22%3A%7B%22d1%22%3A%7B%22v%22%3A51%2C%22s%22%3Atrue%7D%7D%2C%22cd%22%3A1%2C%22f%22%3A1441294533087%2C%22sd%22%3A1%2C%22l%22%3A%22en%22%2C%22i%22%3A-1%7D; deviceType=desktop; TS013f6525=01af671662e6fd8329d452a2dedf6a0c8951ea1724787086802ef7a284804bb20b0fa011fda40f95f1b002c5b429f2eae6c5838937e640c0596f2ea7c718df72ac0f9cff3d529a5fc67cca98ffeaf7ca0824922408edf6fe3994bc44f2d9865b55f3879ffc2a5bce8510c6fa685a0ab3599778987babba848ee8105f5f6f0ee3196b10a85b516c4bf766fae4c787eeeff29b2075c5c99be3d5f3eba836ce1b46febbfcf2759436c31aaf8170324c0b0ccf7b73ba65'''
        headers = self.browser.session.headers
        self.browser.submit_form(login_form)


    def balance(self):
        pass

    @staticmethod
    def parse_transaction(row):
        pass

    def transactions(self):
        pass