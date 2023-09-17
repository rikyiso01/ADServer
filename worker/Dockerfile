FROM docker.io/python:3.11.4-alpine3.18

WORKDIR /app
RUN pip install --no-cache-dir poetry
COPY ./pyproject.toml ./poetry.lock /app/
RUN poetry install --only main
COPY worker /app/worker
ENTRYPOINT [ "sh", "-c" ]
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry run python3 -m worker $DEBUG server worker_check" ]
CMD [ "poetry run python3 -m worker $DEBUG server worker" ]
