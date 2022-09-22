FROM ghcr.io/binkhq/python:3.10-pipenv

WORKDIR /app
ADD . .

RUN pipenv install --system --deploy --ignore-pipfile

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", "--logger-class=gunicorn_log_filter.Logger", \
    "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
