from datetime import datetime, timedelta
import unittest
from unittest import mock

from app.selenium_pid_store import SeleniumPIDStore, NoSuchProcess, MaxSeleniumBrowsersReached


@mock.patch('redis.StrictRedis.get')
@mock.patch('redis.StrictRedis.set')
@mock.patch('redis.StrictRedis.delete')
@mock.patch('redis.StrictRedis.scan_iter')
class TestEncryption(unittest.TestCase):
    data = {}
    storage = SeleniumPIDStore()

    def redis_set(self, key, val):
        self.data[key] = val

    def redis_get(self, key):
        return self.data.get(key)

    def redis_delete(self, key):
        self.data.pop(key)

    def setUp(self):
        self.data = {}

    def test_set_and_get(self, mock_scan, mock_delete, mock_set, mock_get):
        mock_set.side_effect = self.redis_set
        mock_get.side_effect = self.redis_get
        pid = '12345'

        self.storage.set(pid)
        self.assertTrue('selenium-pid-{}'.format(pid) in self.data.keys())

        get_timestamp = self.storage.get('12345')
        self.assertEqual(type(get_timestamp), float)

    def test_get_not_found(self, mock_scan, mock_delete, mock_set, mock_get):
        mock_get.side_effect = self.redis_get

        with self.assertRaises(NoSuchProcess):
            self.storage.get('12345')

    @mock.patch('os.kill')
    def test_terminate_old_browsers(self, mock_os_kill, mock_scan, mock_delete, mock_set, mock_get):
        mock_get.side_effect = self.redis_get
        mock_os_kill.side_effect = ProcessLookupError
        mock_delete.side_effect = self.redis_delete
        self.data = {
            'selenium-pid-11111': datetime.timestamp(datetime.now()),
            'selenium-pid-22222': datetime.timestamp(datetime.now() - timedelta(minutes=15)),
        }
        mock_scan.return_value = [x.encode('utf-8') for x in self.data.keys()]
        self.assertTrue(self.storage.get('11111'))
        self.assertTrue(self.storage.get('22222'))

        self.storage.terminate_old_browsers()
        self.assertTrue(self.storage.get('11111'))
        with self.assertRaises(NoSuchProcess):
            self.storage.get('22222')

    @mock.patch('os.kill')
    def test_close_process_and_delete(self, mock_os_kill, mock_scan, mock_delete, mock_set, mock_get):
        mock_os_kill.side_effect = ProcessLookupError
        mock_set.side_effect = self.redis_set
        mock_get.side_effect = self.redis_get
        mock_delete.side_effect = self.redis_delete
        pid = '11111'
        self.storage.set(pid)

        self.assertTrue(self.storage.get(pid))
        self.storage.close_process_and_delete(pid)
        with self.assertRaises(NoSuchProcess):
            self.storage.get(pid)

    def test_check_max_current_browsers(self, mock_scan, mock_delete, mock_set, mock_get):
        mock_set.side_effect = self.redis_set
        for x in ['11111', '22222', '33333']:
            self.storage.set(x)
        mock_scan.return_value = [x for x in self.data.keys()]

        self.storage.check_max_current_browsers()
        self.assertTrue(mock_scan.called)

    def test_check_max_current_browsers_max_reached(self, mock_scan, mock_delete, mock_set, mock_get):
        mock_set.side_effect = self.redis_set
        for x in ['11111', '22222', '33333', '44444', '55555', '66666']:
            self.storage.set(x)
        mock_scan.return_value = [x for x in self.data.keys()]

        with self.assertRaises(MaxSeleniumBrowsersReached):
            self.storage.check_max_current_browsers()
        self.assertTrue(mock_scan.called)


if __name__ == '__main__':
    unittest.main()
