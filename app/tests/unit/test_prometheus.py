from unittest import TestCase, mock

import settings
from blinker import signal


class TestPrometheus(TestCase):
    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_log_in_success(self, mock_prometheus_counter_inc):
        """
        Test that the login success counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("log-in-success").send(self, slug="test-prometheus")
        # THEN
        self.assertTrue(mock_prometheus_counter_inc.called)

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_log_in_fail(self, mock_prometheus_counter_inc):
        """
        Test that the login fail counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("log-in-fail").send(self, slug="test-prometheus")
        # THEN
        self.assertTrue(mock_prometheus_counter_inc.called)

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_register_success(self, mock_prometheus_counter_inc):
        """
        Test that the register success counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("register-success").send(self, slug="test-prometheus", channel="Bink")
        # THEN
        self.assertTrue(mock_prometheus_counter_inc.called)

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_register_fail(self, mock_prometheus_counter_inc):
        """
        Test that the register fail counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("register-fail").send(self, slug="test-prometheus", channel="Bink")
        # THEN
        self.assertTrue(mock_prometheus_counter_inc.called)
