FROM docker.io/alpine:3.18 as builder

WORKDIR /build
RUN apk --no-cache add go yarn git pkgconf libpcap-dev vectorscan-dev libstdc++-dev
COPY ./caronte/src /build
RUN go mod download && go build
RUN export NODE_OPTIONS=--openssl-legacy-provider && cd frontend && yarn install && yarn build

FROM docker.io/alpine:3.18 as caronte

WORKDIR /app
RUN apk --no-cache add libpcap vectorscan
RUN mkdir -p /app/pcaps/processing
COPY --from=builder /build/caronte /app/caronte
COPY --from=builder /build/frontend/build /app/frontend/build

CMD [ "sh","-c","/app/caronte -mongo-host $MONGO_HOST"]
EXPOSE 3333

FROM caronte

RUN apk --no-cache add poetry
COPY ./pyproject.toml ./poetry.lock /app/
RUN poetry install --only main
COPY worker /app/worker
ENTRYPOINT ["sh", "-c"]
HEALTHCHECK --interval=5s --retries=1 CMD [ "poetry run python3 -m worker $DEBUG server caronte_check" ]
CMD [ "poetry run python3 -m worker $DEBUG server caronte" ]