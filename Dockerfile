FROM binkhq/python:3.7

WORKDIR /app
ADD . .

RUN pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
