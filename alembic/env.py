"""
Contains functions for setting up an alembic context and running migrations.
"""

import logging

# pylint: disable=no-member
from alembic import context
import sys
import os

sys.path.append(os.getcwd())

from app import db
from sqlalchemy import engine_from_config, pool

from app.reporting import LOG_FORMAT
import settings
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

config = context.config
config.set_main_option("sqlalchemy.url", settings.POSTGRES_DSN)

target_metadata = db.Model.metadata


def run_migrations_offline():
    """
    Runs migrations without an active database connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Runs migrations with an active database connection.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
