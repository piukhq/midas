FROM ubuntu:xenial
MAINTAINER Chris Pressland <cp@bink.com>

ADD . /usr/local/src/midas

RUN addgroup --gid 1550 apps && \
 adduser --system --no-create-home --uid 1550 --gid 1550 apps && \
 echo "deb http://ppa.launchpad.net/nginx/stable/ubuntu xenial main" >> /etc/apt/sources.list && \
 echo "deb-src http://ppa.launchpad.net/nginx/stable/ubuntu xenial main" >> /etc/apt/sources.list && \
 apt-key adv --keyserver keyserver.ubuntu.com --recv-keys C300EE8C && \
 apt-get update && \
 apt-get -y install rsync git git-core python3 python3-pip libpq-dev libxml2-dev libxslt1-dev python3-dev nodejs nginx curl xvfb wget && \
 curl -L 'https://github.com/just-containers/s6-overlay/releases/download/v1.18.1.5/s6-overlay-amd64.tar.gz' -o /tmp/s6-overlay-amd64.tar.gz && \
 tar xzf /tmp/s6-overlay-amd64.tar.gz -C / && \
 sed -i -e 's/user www-data;/user apps;/g' /etc/nginx/nginx.conf && \
 rm -rf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default && \
 rsync -a --remove-source-files /usr/local/src/midas/docker_root/ / && \
 pip3 install --upgrade pip && \
 pip3 install uwsgi && \
 pip3 install pytest && \
 pip3 install pytest-xdist && \
 pip3 install -r /usr/local/src/midas/requirements.txt && \
 chown apps:apps /usr/local/src -R && \
 curl -L 'https://github.com/mozilla/geckodriver/releases/download/v0.18.0/geckodriver-v0.18.0-linux64.tar.gz' -o /tmp/geckodriver.tar.gz && \
 tar xzf /tmp/geckodriver.tar.gz && \
 mv geckodriver /usr/local/bin/  && \
 wget https://ftp.mozilla.org/pub/firefox/releases/55.0/linux-x86_64/en-US/firefox-55.0.tar.bz2 && \
 tar -xjf firefox-55.0.tar.bz2 && \
 mv firefox /usr/local/firefox
 ln -s /usr/local/firefox/firefox /usr/bin/firefox && \
 rm firefox-55.0.tar.bz2 && \
 mkdir /home/apps && \
 chown -R apps:apps /home/apps && \
 ln -s /usr/local/bin/py.test /usr/bin/py.test && \
 apt-get -y remove rsync git git-core curl && \
 apt-get -y autoremove && \
 apt-get clean && \
 rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

ENTRYPOINT ["/init"]
