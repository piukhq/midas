from redis import StrictRedis
from settings import SELENIUM_PID_STORE
from datetime import datetime
import os
import signal


class SeleniumPIDStore:
    max_selenium_browsers = 5
    selenium_time_limit = 300

    def __init__(self):
        """
        Connect to Redis database containing Selenium process IDs
        """
        self.storage = StrictRedis.from_url(SELENIUM_PID_STORE)

    @staticmethod
    def _key(pid):
        """
        Creates a key for the given scheme account.
        :param scheme_account_id: The scheme account ID to create the key for.
        :return: A string key to use as the key for the given scheme account ID.
        """
        return 'selenium-pid-{}'.format(pid)

    def get(self, pid):
        """
        Gets created timestamp for a selenium process ID.
        :param pid: Process ID for the selenium browser process.
        :return: Timestamp of when the process was created.
        """
        time = self.storage.get(self._key(pid))
        if not time:
            raise NoSuchProcess({'error': 'No process found for this PID: {}'.format(pid)})
        return time

    def set(self, pid):
        """
        Set a process ID and a created time for a Selenium process.
        :param pid: Process ID for the selenium process.
        :return: None
        """
        created_time = datetime.timestamp(datetime.now())
        self.storage.set(self._key(pid), created_time)

    def terminate_old_browsers(self):
        """
        Set a process ID and a created time for a Selenium process.
        :param pid: Process ID for the selenium process.
        :return: None
        """
        redis_keys = [x.decode("utf-8") for x in self.storage.scan_iter(match='selenium-pid-*')]
        start_time = datetime.timestamp(datetime.now())
        for key in redis_keys:
            key_created_timestamp = self.get(get_pid_from_key(key))
            total_time = start_time - float(key_created_timestamp)
            if total_time > self.selenium_time_limit:
                self.close_process_and_delete(get_pid_from_key(key))

    def close_process_and_delete(self, pid):
        """
        Delete an auth token for the given scheme account.
        :param pid: Process ID for the selenium process.
        :return: None
        """
        try:
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.storage.delete(self._key(pid))

    def check_max_current_browsers(self):
        all_browsers = [x for x in self.storage.scan_iter(match='selenium-pid-*')]
        if len(all_browsers) > self.max_selenium_browsers:
            raise MaxSeleniumBrowsersReached({'error': 'Max Selenium browsers reached'})


def get_pid_from_key(key):
    return key.replace('selenium-pid-', '')


class MaxSeleniumBrowsersReached(Exception):
    pass


class NoSuchProcess(Exception):
    pass
