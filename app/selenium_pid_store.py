from redis import StrictRedis
from settings import SELENIUM_PID_STORE, MAX_SELENIUM_BROWSERS, SELENIUM_BROWSER_TIMEOUT
from datetime import datetime
import os
import signal


class SeleniumPIDStore:
    max_selenium_browsers = int(MAX_SELENIUM_BROWSERS)
    selenium_time_limit = int(SELENIUM_BROWSER_TIMEOUT)

    def __init__(self):
        """
        Connect to the Redis database containing Selenium process IDs.
        """
        self.storage = StrictRedis.from_url(SELENIUM_PID_STORE)

    @staticmethod
    def _key(pid):
        """
        Creates a key for the given Selenium process ID.
        :param pid: Process ID of the Selenium process.
        :return: A string key to use as the key for the given Selenium process ID.
        """
        return 'selenium-pid-{}'.format(pid)

    @staticmethod
    def get_pid_from_key(key):
        """
        Returns a Process ID from the redis key of a Selenium process.
        :param key: Redis key for a Selenium process.
        :return: The process ID.
        """
        return key.replace('selenium-pid-', '')

    def get(self, pid):
        """
        Gets the timestamp for when a Selenium process ID was created.
        :param pid: Process ID of the Selenium process.
        :return: Timestamp of when the process was created.
        """
        time = self.storage.get(self._key(pid))
        if not time:
            raise NoSuchProcess({'error': 'No process found for this PID: {}'.format(pid)})
        return time

    def set(self, pid):
        """
        Set the process ID of a Selenium process and a timestamp of when it was created.
        :param pid: Process ID of the Selenium process.
        :return: None.
        """
        created_time = datetime.now().timestamp()
        self.storage.set(self._key(pid), created_time)

    def terminate_old_browsers(self):
        """
        Checks maximum runtime for a Selenium process from settings, then closes any stored Selenium processes which.
        have been running for longer than the maximum runtime.
        :return: None.
        """
        redis_keys = [x.decode("utf-8") for x in self.storage.scan_iter(match='selenium-pid-*')]
        start_time = datetime.now().timestamp()
        for key in redis_keys:
            key_created_timestamp = self.get(self.get_pid_from_key(key))
            total_time = start_time - float(key_created_timestamp)
            if total_time > self.selenium_time_limit:
                self.close_process_and_delete(self.get_pid_from_key(key))

    def close_process_and_delete(self, pid):
        """
        Kills the requested process ID and removes it from redis.
        :param pid: Process ID of the selenium process.
        :return: None.
        """
        try:
            os.kill(int(pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        self.storage.delete(self._key(pid))

    def is_browser_available(self):
        all_browsers = [x for x in self.storage.scan_iter(match='selenium-pid-*')]

        if len(all_browsers) >= self.max_selenium_browsers:
            return False
        return True


class NoSuchProcess(Exception):
    pass
