FROM binkhq/python:3.7

WORKDIR /app
ADD . .

RUN pip install --no-cache-dir pipenv==2018.11.26 gunicorn && \
    pipenv install --system --deploy --ignore-pipfile && \
    pip uninstall -y pipenv && \
    echo '[ default_conf ]\nssl_conf = ssl_sect\n[ssl_sect]\nsystem_default = ssl_default_sect\n[ssl_default_sect]\nMinProtocol = TLSv1.2\nCipherString = DEFAULT:@SECLEVEL=1' >> /etc/ssl/openssl.cnf

CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", \
                  "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
