FROM python:3.10.8

WORKDIR /app
RUN python3 -m pip install poetry
COPY ./pyproject.toml ./poetry.lock /app/
RUN poetry install --only main
COPY worker /app/worker
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry","run","python3","-m","worker","server","worker_check" ]
CMD [ "poetry","run","python3","-m","worker","server","worker" ]
