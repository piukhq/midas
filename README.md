# Midas


[![pipeline status](https://git.bink.com/Olympus/midas/badges/develop/pipeline.svg)](https://git.bink.com/Olympus/midas/commits/develop) [![coverage report](https://git.bink.com/Olympus/midas/badges/develop/coverage.svg)](https://git.bink.com/Olympus/midas/commits/develop)


<!-- START doctoc generated TOC please keep comment here to allow auto update -->
<!-- DON'T EDIT THIS SECTION, INSTEAD RE-RUN doctoc TO UPDATE -->
**Table of Contents**  *generated with [DocToc](https://github.com/thlorenz/doctoc)*

- [Midas](#midas)
  - [Prerequisites](#prerequisites)
  - [Dependencies](#dependencies)
  - [Project Setup](#project-setup)
    - [MacOS Dependencies](#macos-dependencies)
    - [Virtual Environment](#virtual-environment)
    - [Database Schema Migration](#database-schema-migration)
    - [Development API Server](#development-api-server)
    - [Unit Tests](#unit-tests)
    - [End-to-End Matching Test](#end-to-end-matching-test)
      - [Testing with Flexible Transactions](#testing-with-flexible-transactions)
      - [Inspecting PostgreSQL](#inspecting-postgresql)
      - [Inspecting Redis](#inspecting-redis)
  - [Migrations](#migrations)
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

### MacOS Dependencies

Before installing the project dependencies on MacOS, you will need to install a few homebrew dependencies, and let the system know where to find the OpenSSL libraries.

```bash
brew install postgres openssl
export LDFLAGS="-L/usr/local/opt/openssl/lib"
```

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

The `.env` file contains connection parameters for the two major services used in the project; PostgreSQL and Redis. The default connection parameters assume a local instance of these services listening on ports 51234 (PostgreSQL) and 61234 (Redis.)

To quickly create docker containers for the required services:

```bash
s/services
```

### Database Schema Migration


### Development API Server



### Unit Tests



### End-to-End Matching Test
`


The `txmatch:status:checkins:*` keys contain timestamps from when various parts of the system were operating.

## Migrations

Migrations should be manually squashed before each deployment for efficiency's sake. As a rule of thumb, each merge request should only include a single migration containing all the required changes for that feature. In some cases this will not be possible.

## Deployment

There is a Dockerfile provided in the project root. Build an image from this to get a deployment-ready version of the project.
