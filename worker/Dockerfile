FROM docker.io/python:3.8.16-alpine3.18

WORKDIR /app
RUN apk add --no-cache poetry
COPY ./pyproject.toml ./poetry.lock /app/
RUN poetry install --only main
COPY worker /app/worker
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry","run","python3","-m","worker","server","worker_check" ]
CMD [ "poetry","run","python3","-m","worker","server","worker" ]
