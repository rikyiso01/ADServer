FROM ghcr.io/eciavatta/caronte:1.21.1

RUN apt-get update && apt-get install -y --no-install-recommends python3 python3-pip && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install poetry
COPY ./pyproject.toml ./poetry.lock /opt/caronte/
RUN poetry install --only main
COPY worker /opt/caronte/worker
ENTRYPOINT []
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry","run","python3","-m","worker","server","caronte_check" ]
CMD [ "poetry","run","python3","-m","worker","server","caronte" ]