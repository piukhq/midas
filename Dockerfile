FROM python:3.6

WORKDIR /app
ADD . .

ARG FIREFOX_URL=https://ftp.mozilla.org/pub/firefox/releases/55.0/linux-x86_64/en-US/firefox-55.0.tar.bz2
ARG GECKODRIVER_URL=https://github.com/mozilla/geckodriver/releases/download/v0.18.0/geckodriver-v0.18.0-linux64.tar.gz

RUN apt update && apt -y install curl bzip2 ca-certificates xvfb && \
    curl -L "$FIREFOX_URL" -o /tmp/firefox.tar.bz2 && \
    tar xvf /tmp/firefox.tar.bz2 -C /usr/local && \
    ln -s /usr/local/firefox/firefox /usr/bin/firefox && \
    curl -L "$GECKODRIVER_URL" -o /tmp/geckodriver.tar.gz && \
    tar xvf /tmp/geckodriver.tar.gz -C /usr/local/bin && \
    mkdir -p /root/.ssh && mv /app/deploy_key /root/.ssh/id_rsa && \
    chmod 0600 /root/.ssh/id_rsa && \
    ssh-keyscan git.bink.com > /root/.ssh/known_hosts && \
    pip install pipenv uwsgi && pipenv install --system --deploy && \
    pip install pytest pytest-xdist && \
    apt -y remove bzip2 curl && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp* /root/.ssh
