import logging

import typer
from rq import Worker

from app.db import redis_raw
from app.error_handler import handle_retry_task_request_error

cli = typer.Typer()
logger = logging.getLogger(__name__)


# this one
@cli.command()
def task_worker(burst: bool = False) -> None:  # pragma: no cover
    worker = Worker(
        queues=["midas-retry"],
        connection=redis_raw,
        log_job_description=True,
        exception_handlers=[handle_retry_task_request_error],
    )
    logger.info("Starting task worker...")
    worker.work(burst=burst, with_scheduler=True)


if __name__ == "__main__":
    cli()
