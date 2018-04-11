FROM python:3.6

ADD . /app

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
    pip install uwsgi && pip install -r /app/requirements.txt && \
    pip install pytest pytest-xdist && \
    apt -y remove bzip2 curl && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp* /root/.ssh






    

 #rsync -a --remove-source-files /usr/local/src/midas/docker_root/ / && \
 #echo "Host git.bink.com\n\tStrictHostKeyChecking no\n" >> /root/.ssh/config && \
 #chmod -R 600 /root/.ssh && \
 #pip3 install --upgrade pip && \
 #pip3 install uwsgi && \
 #pip3 install -r /usr/local/src/midas/requirements.txt && \
 #pip3 install pytest && \
 #pip3 install pytest-xdist && \
 #chown apps:apps /usr/local/src -R && \
 #rm firefox-55.0.tar.bz2 && \
 #mkdir /home/apps && \
 #chown -R apps:apps /home/apps && \
 #ln -s /usr/local/bin/pytest /usr/bin/pytest && \
 #apt-get -y remove rsync git git-core curl && \
 #apt-get -y autoremove && \
 #apt-get clean && \
 #rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* /root/.ssh /usr/local/src/midas/docker_root

#ENTRYPOINT ["/init"]
