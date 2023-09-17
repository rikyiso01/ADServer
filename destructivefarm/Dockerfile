FROM docker.io/python:3.11.4-alpine3.18 as destructivefarm

WORKDIR /app
COPY ./destructivefarm/src/server/requirements.txt /app/server/requirements.txt
RUN pip install --no-cache-dir -r /app/server/requirements.txt
COPY ./destructivefarm/src/server /app/server
RUN ln -Tfs /data/flags.sqlite /app/server/flags.sqlite

CMD ["/app/server/start_server.sh"]
EXPOSE 5000
VOLUME [ "/data" ]

FROM destructivefarm

RUN pip install --no-cache-dir poetry
COPY ./poetry.lock ./pyproject.toml /app/
RUN poetry install --only main
RUN poetry run python3 -m pip install -r server/requirements.txt
COPY ./worker /app/worker

ENTRYPOINT [ "sh", "-c" ]
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry run python3 -m worker $DEBUG server destructivefarm_check" ]
CMD [ "poetry run python3 -m worker $DEBUG server destructivefarm" ]