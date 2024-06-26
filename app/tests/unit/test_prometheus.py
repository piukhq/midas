from unittest import TestCase, mock

from blinker import signal

import settings


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
        mock_prometheus_counter_inc.assert_called_once()

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
        mock_prometheus_counter_inc.assert_called_once()

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_join_success(self, mock_prometheus_counter_inc):
        """
        Test that the join success counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("join-success").send(self, slug="test-prometheus", channel="com.bink.wallet")
        # THEN
        mock_prometheus_counter_inc.assert_called_once()

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_join_fail(self, mock_prometheus_counter_inc):
        """
        Test that the join fail counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("join-fail").send(self, slug="test-prometheus", channel="com.bink.wallet")
        # THEN
        mock_prometheus_counter_inc.assert_called_once()

    @mock.patch("app.prometheus.Histogram.observe", autospec=True)
    def test_record_http_request(self, mock_prometheus_histogram_observe):
        """
        Test that the join fail counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("record-http-request").send(
            self,
            slug="test-prometheus",
            endpoint="/someplace",
            latency=1.234,
            response_code=500,
        )
        # THEN
        mock_prometheus_histogram_observe.assert_called_once()

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_callback_success(self, mock_prometheus_counter_inc):
        """
        Test that the callback success counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("callback-success").send(self, slug="test-prometheus")
        # THEN
        mock_prometheus_counter_inc.assert_called_once()

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_callback_fail(self, mock_prometheus_counter_inc):
        """
        Test that the callback fail counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("callback-fail").send(self, slug="test-prometheus")
        # THEN
        mock_prometheus_counter_inc.assert_called_once()

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_request_fail(self, mock_prometheus_counter_inc):
        """
        Test that the request fail counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("request-fail").send(self, slug="test-prometheus", channel="com.bink.wallet", error="TIMEOUT")
        # THEN
        mock_prometheus_counter_inc.assert_called_once()

    @mock.patch("app.prometheus.Counter.inc", autospec=True)
    def test_request_success(self, mock_prometheus_counter_inc):
        """
        Test that the request success counter increments
        """
        # GIVEN
        settings.PUSH_PROMETHEUS_METRICS = False  # Disable the attempted push
        # WHEN
        signal("request-success").send(self, slug="test-prometheus", channel="com.bink.wallet")
        # THEN
        mock_prometheus_counter_inc.assert_called_once()
