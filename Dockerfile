FROM python:3.6-alpine

WORKDIR /app
ADD . .

RUN apk add --no-cache --virtual build \
      build-base \
      libxslt-dev \
      libc-dev \
      openssh \
      git && \
    apk add --no-cache \
      ca-certificates \
      libxslt \
      postgresql-dev && \
    mkdir -p /root/.ssh && mv /app/deploy_key /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    ssh-keyscan git.bink.com > /root/.ssh/known_hosts && \
    pip install pipenv gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip install pytest pytest-xdist && \
    apk del --no-cache build && \
    rm -rf /tmp/* /root/.ssh
