import logging

import typer
from redis import Redis
from retry_tasks_lib.utils.error_handler import job_meta_handler
from rq import Worker

import settings

cli = typer.Typer()
logger = logging.getLogger(__name__)

redis_raw = Redis.from_url(
    settings.REDIS_URL,
    socket_connect_timeout=3,
    socket_keepalive=True,
    retry_on_timeout=False,
)


@cli.command()
def task_worker(burst: bool = False) -> None:  # pragma: no cover
    worker = Worker(
        queues=["midas-retry"],
        connection=redis_raw,
        log_job_description=True,
        exception_handlers=[job_meta_handler],
    )
    logger.info("Starting task worker...")
    worker.work(burst=burst, with_scheduler=True)


if __name__ == "__main__":
    cli()
