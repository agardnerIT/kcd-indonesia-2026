# Step 3: keep track of the agents

[Step 2](../step2/README.md) decoded each message and then forgot it. Step 3 remembers who is connected, which is what makes a demo with 2 or 3 collectors possible.

## What changed

- **A registry.** `agents` is a dict keyed by `instance_uid`. Each entry records the agent's description (service name, version, host...), its capabilities, whether it's healthy, its last sequence number and when it was last seen. It lives in memory and is lost on restart, which is fine for a demo.
- **`GET /agents`.** Lists everything the server knows, as JSON.
- **Partial updates.** An agent may leave out fields that haven't changed since its last message. So we only update the fields that are present in each message (`HasField`), and never wipe what we already know.
- **Capabilities as names.** The `capabilities` field is a bitmask. We turn it into readable names such as `ReportsStatus`.
- **`ReportFullState`.** Each agent numbers its messages with `sequence_num`, going up by 1. If we see a gap, or an agent we've never met starts mid-sequence (for example because *we* restarted and lost our state), we set the `ReportFullState` flag in the reply. That asks the agent to resend everything about itself.
- **Disconnects.** If an agent sends `agent_disconnect`, we mark it as disconnected.
- **Server capabilities.** The reply now declares `AcceptsStatus`, telling agents that we take their status reports.
- **Short logs.** One line per event (`+ connected`, `- disconnected`, `! gap`), instead of dumping every message.

## Quick start

```sh
./start.sh [n]   # n plain collectors (default 1) in Docker + the server here; Ctrl-C stops all
./stop.sh        # stop anything left running
```

## Run (by hand)

```sh
python server.py   # with the shared venv active, see the root README
```

Start 2 or 3 collectors from this folder, in separate terminals (or use `./start.sh 3`):

```sh
docker run --rm -v "$PWD/collector-config.yaml:/etc/otelcol-contrib/config.yaml" \
  otel/opentelemetry-collector-contrib:0.162.0
```

Each one generates its own random instance UID, so just start the container several times. Then look at the result:

```sh
curl -s localhost:4320/agents | python3 -m json.tool
```

## Limitations

- Over plain HTTP there's no persistent connection, so "connected" only means "has not said goodbye". Use `seconds_since_seen` to spot agents that have gone quiet.
- We receive agent status but still send nothing but the UID, flags and capabilities. Remote config is the next step.
