from unittest import TestCase, mock

import settings
from app.prometheus import PrometheusManager
from blinker import signal


class TestPrometheus(TestCase):
    # initialise the prometheus manager, but only once or you will get name
    # conflicts in the registry
    prometheus = PrometheusManager()

    @mock.patch('app.prometheus.Counter.inc', autospec=True)
    def test_log_in_success(self, mock_prometheus_counter_inc):
        """
        Test the login success counter increment
        """
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        signal("log-in-success").send(self, slug="test-prometheus")

        self.assertTrue(mock_prometheus_counter_inc.called)

    @mock.patch('app.prometheus.Counter.inc', autospec=True)
    def test_log_in_fail(self, mock_prometheus_counter_inc):
        """
        Test the login fail counter increment
        """
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        signal("log-in-fail").send(self, slug="test-prometheus")

        self.assertTrue(mock_prometheus_counter_inc.called)
