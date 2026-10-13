# Step 1: print raw OpAMP messages

The smallest possible OpAMP server, built with FastAPI. It accepts what agents send and prints it, byte for byte.

## How it works

- OpAMP has two transports: WebSocket and plain HTTP. We use **HTTP**: the agent polls by sending `POST /v1/opamp` with a protobuf-encoded `AgentToServer` message as the body.
- One FastAPI handler, `@app.post("/v1/opamp")`, reads `await request.body()`. Uvicorn takes care of chunked bodies, which the collector's Go HTTP client uses.
- The headers are printed, then the body as a Python bytes literal and as hex. It is protobuf, so it isn't human-readable yet.
- The server replies `200` with an empty body, which is a valid all-defaults `ServerToAgent`.
- The `Opamp-Instance-Uid` header identifies each agent, so you can tell collectors apart already.

## Quick start

```sh
./start.sh [n]   # n plain collectors (default 1) in Docker + the server here; Ctrl-C stops all
./stop.sh        # stop anything left running
```

## Run (by hand)

```sh
python server.py   # with the shared venv active, see the root README
```

Then start a collector from this folder (`./collector-config.yaml` is its config):

```sh
docker run --rm -v "$PWD/collector-config.yaml:/etc/otelcol-contrib/config.yaml" \
  otel/opentelemetry-collector-contrib:0.162.0
```

Expect a message every 30s or so.


## Limitations

Nothing is decoded and the reply doesn't carry the agent's `instance_uid`. Step 2 fixes both.
