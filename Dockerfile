FROM ghcr.io/binkhq/python:3.12-poetry AS build

WORKDIR /src
COPY . .
RUN poetry build

FROM ghcr.io/binkhq/python:3.12

ARG PIP_INDEX_URL

WORKDIR /app

COPY --from=build /src/dist/*.whl .
RUN pip install *.whl && rm *.whl

COPY --from=build /src/alembic/ ./alembic/
COPY --from=build /src/alembic.ini .

ENTRYPOINT [ "linkerd-await", "--" ]
CMD [ "gunicorn", "--workers=2", "--threads=2", "--error-logfile=-", "--logger-class=gunicorn_log_filter.Logger", \
    "--access-logfile=-", "--bind=0.0.0.0:9000", "wsgi:app" ]
