FROM python:3.10.8

WORKDIR /app
RUN python3 -m pip install poetry
COPY ./destructivefarm/src/server /app/server
COPY ./poetry.lock ./pyproject.toml /app/
RUN poetry install --only main
RUN poetry run python3 -m pip install -r server/requirements.txt
COPY ./worker /app/worker

EXPOSE 5000
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry","run","python3","-m","worker","server","destructivefarm_check" ]
CMD [ "poetry", "run", "python3", "-m", "worker","server", "destructivefarm" ]