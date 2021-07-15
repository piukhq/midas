import os
import typing as t
from contextlib import contextmanager

from blinker import signal
from prometheus_client import Counter, Histogram, push_to_gateway
from prometheus_client.registry import REGISTRY

import settings
from app.reporting import get_logger


log = get_logger("prometheus-manager")


class PrometheusManager:
    def __init__(self) -> None:
        self.metric_types = self._get_metric_types()
        signal("log-in-success").connect(self.log_in_success)
        signal("log-in-fail").connect(self.log_in_fail)
        signal("register-success").connect(self.register_success)
        signal("register-fail").connect(self.register_fail)
        signal("record-http-request").connect(self.record_http_request)
        signal("callback-success").connect(self.callback_success)
        signal("callback-fail").connect(self.callback_fail)
        signal("request-fail").connect(self.request_fail)
        signal("request-success").connect(self.request_success)

    def log_in_success(self, sender: t.Union[object, str], slug: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        """
        counter = self.metric_types["counters"]["log_in_success"]
        labels = {"slug": slug}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def log_in_fail(self, sender: t.Union[object, str], slug: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        """
        counter = self.metric_types["counters"]["log_in_fail"]
        labels = {"slug": slug}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def register_success(self, sender: t.Union[object, str], slug: str, channel: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        :param channel: The origin of this request e.g. 'com.bink.wallet'
        """
        counter = self.metric_types["counters"]["register_success"]
        labels = {"slug": slug, "channel": channel}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def register_fail(self, sender: t.Union[object, str], slug: str, channel: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        :param channel: The origin of this request e.g. 'com.bink.wallet'
        """
        counter = self.metric_types["counters"]["register_fail"]
        labels = {"slug": slug, "channel": channel}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def callback_success(self, sender: t.Union[object, str], slug: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        """
        counter = self.metric_types["counters"]["callback_success"]
        labels = {"slug": slug}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def callback_fail(self, sender: t.Union[object, str], slug: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        """
        counter = self.metric_types["counters"]["callback_fail"]
        labels = {"slug": slug}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def request_fail(self, sender: t.Union[object, str], slug: str, channel: str, error: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        :param channel: The origin of this request e.g. 'com.bink.wallet'
        :param error: The connection error encountered
        """
        counter = self.metric_types["counters"]["request_fail"]
        labels = {"slug": slug, "channel": channel, "error": error}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def request_success(self, sender: t.Union[object, str], slug: str, channel: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        :param channel: The origin of this request e.g. 'com.bink.wallet'
        """
        counter = self.metric_types["counters"]["request_success"]
        labels = {"slug": slug, "channel": channel}
        self._increment_counter(counter=counter, increment_by=1, labels=labels)

    def record_http_request(
        self,
        sender: t.Union[object, str],
        slug: str,
        endpoint: str,
        latency: t.Union[int, float],
        response_code: int,
    ) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        :param endpoint: The API endpoint path
        :param latency: HTTP request time in seconds
        :param response_code: HTTP response code e.g 200, 500
        """

        histogram = self.metric_types["histograms"]["request_latency"]
        with self._prometheus_push_manager(
            prometheus_push_gateway=settings.PROMETHEUS_PUSH_GATEWAY,
            prometheus_job=settings.PROMETHEUS_JOB,
        ):
            histogram.labels(slug=slug, endpoint=endpoint, response_code=response_code).observe(latency)

    def _increment_counter(self, counter: Counter, increment_by: t.Union[int, float], labels: t.Dict):
        with self._prometheus_push_manager(
            prometheus_push_gateway=settings.PROMETHEUS_PUSH_GATEWAY,
            prometheus_job=settings.PROMETHEUS_JOB,
        ):
            counter.labels(**labels).inc(increment_by)

    @staticmethod
    def _get_metric_types() -> t.Dict:
        """
        Define metric types here (see https://prometheus.io/docs/concepts/metric_types/),
        with the name, description and a list of the labels they expect.
        """
        metric_types = {
            "counters": {
                "log_in_success": Counter(
                    name="log_in_success",
                    documentation="Incremental count of successful logins",
                    labelnames=("slug",),
                ),
                "log_in_fail": Counter(
                    name="log_in_fail",
                    documentation="Incremental count of failed logins",
                    labelnames=("slug",),
                ),
                "register_success": Counter(
                    name="register_success",
                    documentation="Incremental count of successful registrations",
                    labelnames=("slug", "channel"),
                ),
                "register_fail": Counter(
                    name="register_fail",
                    documentation="Incremental count of failed registrations",
                    labelnames=("slug", "channel"),
                ),
                "callback_success": Counter(
                    name="callback_success",
                    documentation="Incremental count of successful callbacks to our system",
                    labelnames=("slug",),
                ),
                "callback_fail": Counter(
                    name="callback_fail",
                    documentation="Incremental count of failed callbacks to our system",
                    labelnames=("slug",),
                ),
                "request_fail": Counter(
                    name="request_fail",
                    documentation="Incremental count of failed HTTP requests from our system",
                    labelnames=("slug", "channel", "error"),
                ),
                "request_success": Counter(
                    name="request_success",
                    documentation="Incremental count of successful (not failed) HTTP requests from our system",
                    labelnames=("slug", "channel"),
                ),
            },
            "histograms": {
                "request_latency": Histogram(
                    name="request_latency_seconds",
                    documentation="Request latency seconds",
                    labelnames=("slug", "endpoint", "response_code"),
                )
            },
        }

        return metric_types

    @staticmethod
    @contextmanager
    def _prometheus_push_manager(prometheus_push_gateway: str, prometheus_job: str):
        push_timeout = 3  # PushGateway should be running in the same pod
        grouping_key = {"pid": str(os.getpid())}

        try:
            yield
        finally:
            if settings.PUSH_PROMETHEUS_METRICS:
                log.debug("Prometheus push manager started.")
                try:
                    push_to_gateway(
                        gateway=prometheus_push_gateway,
                        job=prometheus_job,
                        registry=REGISTRY,
                        grouping_key=grouping_key,
                        timeout=push_timeout,
                    )
                except Exception as e:
                    log.exception(str(e))
