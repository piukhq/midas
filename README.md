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

<!-- END doctoc generated TOC please keep comment here to allow auto update -->

## Prerequisites

- [pipenv](https://docs.pipenv.org)

## Dependencies

The following is a list of the important dependencies used in the project. You do not need to install these manually. See [project setup](#project-setup) for installation instructions.

- [Flask](http://flask.pocoo.org) - API framework.
- [Redis](https://redis-py.readthedocs.io/en/latest) - Key-value store used for storing system configuration and task queues.
- [Celery](https://docs.celeryproject.org/en/stable/index.html) - Celery is distributed task queue.


## Project Setup

Pipenv is used for managing project dependencies and execution.

### Virtual Environment

To create a virtualenv and install required software packages:

```bash
pipenv install --dev
```

Project configuration is done through environment variables. A convenient way to set these is in a `.env` file in the project root. This file will be sourced by Pipenv when `pipenv run` and `pipenv shell` are used. See `settings.py` for configuration options that can be set in this file.

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

## (WIP) Setting up retry tasks
0. Midas needs to be updated to Python 3.10
1. Create database "midas"
2. To create the db schema use the new migration (alembic) included as part of this branch - it'll pre-populate the db 
   with all the data necessary to get the retry mechanism running.
3. Start Redis in a docker container and make sure the port number matches what's in the settings

## (WIP) To-do for retry tasks
The main bulk of the work now is error handling (error_handler.py).
We need to decide which exceptions will be retried on and see what format they reach
the error handler in, once Carla's work around error handling is merged.
At the time of writing this, error handling is where the mechanism fails due to certain exceptions (most notably MaxRetryError) 
bubbling up as completely different exceptions that should not be retried on. 