FROM binkhq/python:3.7

WORKDIR /app
ADD . .

# prevents tzdata from asking where you live
ARG DEBIAN_FRONTEND=noninteractive

# libgi* and libcairo* are installed for pygobject.
# https://github.com/AzureAD/microsoft-authentication-extensions-for-python/wiki/Encryption-on-Linux
RUN apt-get update && apt-get install -y gcc libgirepository1.0-dev libcairo2-dev python3-dev gir1.2-secret-1 && \
    pip install --no-cache-dir pipenv gunicorn pygobject && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    apt-get autoremove -y gcc libgirepository1.0-dev libcairo2-dev python3-dev && rm -rf /var/lib/apt/lists

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
