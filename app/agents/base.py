import hashlib
from robobrowser import RoboBrowser
from app.agents.exceptions import MinerError


class Miner(object):
    retry_limit = 2

    def __init__(self, credentials, retry_count):
        self.browser = RoboBrowser(parser="lxml", history=False)

        if retry_count <= self.retry_limit:
            self.login(credentials)
        else:
            raise MinerError("RETRY_LIMIT_REACHED")

    def login(self, credentials):
        raise NotImplementedError()

    def balance(self):
        raise NotImplementedError()

    def transactions(self):
        raise NotImplementedError()

    @staticmethod
    def parse_transaction(row):
        raise NotImplementedError()

    def hashed_transaction(self, transaction):
        transaction = self.parse_transaction(transaction)
        s = "{0}{1}{2}".format(transaction['date'], transaction['title'], transaction['points'])
        transaction["hash"] = hashlib.md5(s.encode("utf-8")).hexdigest()
        return transaction
