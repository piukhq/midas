import os
import typing as t
from contextlib import contextmanager

import settings
from blinker import signal
from prometheus_client import Counter, push_to_gateway
from prometheus_client.registry import REGISTRY
from settings import logger


class PrometheusManager:
    def __init__(self) -> None:
        self.metric_types = self._get_metric_types()
        signal("log-in-success").connect(self.log_in_success)
        signal("log-in-fail").connect(self.log_in_fail)

    def log_in_success(self, sender: t.Union[object, str], slug: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        """
        increment_by = 1
        with self.prometheus_push_manager(
            prometheus_push_gateway=settings.PROMETHEUS_PUSH_GATEWAY,
            prometheus_job=settings.PROMETHEUS_JOB,
        ):
            counter = self.metric_types["counters"]["log_in_success"]
            counter.labels(slug=slug).inc(increment_by)

    def log_in_fail(self, sender: t.Union[object, str], slug: str) -> None:
        """
        :param sender: Could be an agent, or a string description of who the sender is
        :param slug: A slug, e.g. 'harvey-nichols'
        """
        increment_by = 1
        with self.prometheus_push_manager(
            prometheus_push_gateway=settings.PROMETHEUS_PUSH_GATEWAY,
            prometheus_job=settings.PROMETHEUS_JOB,
        ):
            counter = self.metric_types["counters"]["log_in_fail"]
            counter.labels(slug=slug).inc(increment_by)

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
            },
        }

        return metric_types

    @staticmethod
    @contextmanager
    def prometheus_push_manager(prometheus_push_gateway: str, prometheus_job: str):
        push_timeout = 3  # PushGateway should be running in the same pod
        grouping_key = {"pid": str(os.getpid())}

        try:
            yield
        finally:
            if settings.PUSH_PROMETHEUS_METRICS:
                logger.debug("Prometheus push manager started")
                try:
                    push_to_gateway(
                        gateway=prometheus_push_gateway,
                        job=prometheus_job,
                        registry=REGISTRY,
                        grouping_key=grouping_key,
                        timeout=push_timeout,
                    )
                except Exception as e:
                    logger.exception(str(e))
