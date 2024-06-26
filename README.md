# Midas


[![pipeline status](https://git.bink.com/Olympus/midas/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/midas/commits/develop) [![coverage report](https://git.bink.com/Olympus/midas/badges/develop/coverage.svg)](https://git.bink.com/Olympus/midas/commits/develop)


<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Midas](#midas)
  - [Prerequisites](#prerequisites)
  - [Dependencies](#dependencies)
  - [Project Setup](#project-setup)
    - [Virtual Environment](#virtual-environment)
    - [Unit Tests](#unit-tests)
  - [Deployment](#deployment)
  - [Implementation/Design notes](#implementationdesign-notes)


<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- [poetry](https://python-poetry.org)

## Dependencies

The following is a list of the important dependencies used in the project. You do not need to install these manually. See [project setup](#project-setup) for installation instructions.

- [Flask](http://flask.pocoo.org) - API framework.
- [Redis](https://redis-py.readthedocs.io/en/latest) - Key-value store used for storing system configuration and task queues.
- [Celery](https://docs.celeryproject.org/en/stable/index.html) - Celery is distributed task queue.


## Project Setup

Poetry is used for managing project dependencies and execution.

### Virtual Environment

Allow Poetry to authenticate with Azure Artifacts, if you haven't already. Username and password can be obtained from the ['Azure DevOps - Feed - Read PAT' item in the Engineering 1Password vault](https://start.1password.com/open/i?a=24Z7AXLXINAQJK5EO2PN4BI7WA&v=sulgy6aoc2tk4jwje655zg44by&i=ryyryvavl2zkeetvfgx5iizqda&h=bink.1password.com).

```bash
poetry config http-basic.azure <username> <password>
```

Create a virtualenv and install required software packages:

```bash
poetry install
```

Project configuration is done through environment variables. A convenient way to set these is in a `.env` file in the project root. See `settings.py` for configuration options that can be set in this file.

For terminal usage this file can be automatically sourced with [direnv]() or [poetry-dotenv-plugin](https://pypi.org/project/poetry-dotenv-plugin). Most editors and IDEs have built-in or plugin support for dotenv files.

To make a `.env` file from the provided example:

```bash
cp .env.example .env
```

The provided example is sufficient as a basic configuration, but modification may be required for specific use-cases.

### Unit Tests

Testing is done with `pytest`.

To execute a full test run:

pytest --verbose --cov app --cov-report term-missing app/tests/unit

## Deployment

There is a Dockerfile provided in the project root. Build an image from this to get a deployment-ready version of the project.

## [Implementation/Design Notes]()

### New journey and handler type added for removed - 05/07/2023

Originally intended for Costa who require a report of when the last card is removed
from a wallet. Details need to be worked out; it is believed this is for marketing purposes
not to inform the retailer to remove/delete the card.  We intend to report the card if Hermes
sends the loyalty_card_removed message

In the agent class override the base method:

  ```loyalty_card_removed(self) -> None:```

This method will only be called if:
1. Europa must be configured for the REMOVED_HANDLER
2. The agent __init__ must implement journey types by sending the handler to super().__init__:
```python

       def __init__(self, retry_count, user_info, scheme_slug=None, config=None):
           super().__init__(
               retry_count,
               user_info,
               config_handler_type=JOURNEY_TYPE_TO_HANDLER_TYPE_MAPPING[user_info["journey_type"]],
               scheme_slug=scheme_slug,
               config=config,
           )
```
