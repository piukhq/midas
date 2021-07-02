FROM binkhq/python:3.9

WORKDIR /app
ADD . .

RUN apt-get update && apt-get install -y gcc && \
    pip install --no-cache-dir pipenv gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    apt-get autoremove -y gcc && rm -rf /var/lib/apt/lists

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
