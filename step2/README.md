# Step 2: decode messages and reply properly

Same FastAPI endpoint as [step 1](../step1/README.md), but the body is now parsed into a real `AgentToServer` message.

## What changed

- `proto/` holds `opamp.proto` and `anyvalue.proto` from [opamp-spec](https://github.com/open-telemetry/opamp-spec/tree/main/proto/opamp/v1).
- `opamp/v1/*_pb2.py` is the generated Python code (committed, so you don't need `protoc` to run the server).
- The handler parses each body and prints it with `text_format`, so you see the agent's description, capabilities, health, effective config and so on.
- The reply is a `ServerToAgent` that **echoes the agent's `instance_uid`**, which the spec requires in every response.

## Protobuf, in plain English

### What is it?

Protocol Buffers ("protobuf") is a way of turning structured data into a small string of bytes so it can be sent over a network, and turning it back again. It's like JSON in purpose, but compact and binary.

OpAMP uses it for every message. When a collector says "hello, here's who I am", it builds an `AgentToServer` message, **serializes** it to bytes and POSTs those bytes. That is the unreadable blob you saw in step 1.

### Why can't we just read the bytes?

Take the start of a real message:

```
0a 10 30 31 32 33 ... 66   10 01   1a 23 ...
```

It can be read like this:

| Bytes | Meaning |
|-------|---------|
| `0a` | "field number 1, a chunk of bytes follows" |
| `10` | "the chunk is 16 bytes long" |
| `30 31 ... 66` | the 16 bytes: the agent's `instance_uid` |
| `10 01` | "field number 2, the number 1": `sequence_num` |
| `1a 23` | "field number 3, a 35-byte chunk follows": `agent_description` |

Notice what's **missing**: the field *names*. The bytes only carry field *numbers*. That's why protobuf is small, but it means the bytes are meaningless unless you know what field 1, 2 and 3 stand for.

### Where do the field numbers come from?

From a **schema**: a `.proto` file. It's the shared dictionary between sender and receiver. The OpAMP spec publishes one, and the two we use are in [proto/opamp/v1/](proto/opamp/v1/). An excerpt, simplified:

```proto
message AgentToServer {
    bytes instance_uid = 1;
    uint64 sequence_num = 2;
    AgentDescription agent_description = 3;
    ...
}
```

This is the other half of the table above: field 1 is `instance_uid`, field 2 is `sequence_num`, and so on. Both sides must use the same file, or they will misread each other.

### How do we decode it, then?

1. Take the `.proto` files from the spec.
2. Run `protoc`, the protobuf compiler (here via `grpc_tools.protoc`, which bundles it as a Python package). It reads the schema and **generates Python code**: [opamp/v1/opamp_pb2.py](opamp/v1/opamp_pb2.py).
3. Import that generated module and use it like any other Python class:

```python
msg = opamp_pb2.AgentToServer()
msg.ParseFromString(body)      # bytes in
print(msg.instance_uid)        # normal Python attributes out
```

### Why generate code? Why not a generic library?

The generic `protobuf` package (in [requirements.txt](../requirements.txt)) knows the *rules* of the wire format: how a number or a chunk of bytes is laid out. It knows nothing about OpAMP. The generated `_pb2.py` file is the OpAMP-specific part: classes such as `AgentToServer` and `ServerToAgent`, with every field name, type and number filled in.

So: **`protobuf` = the engine, the `.proto` file = the OpAMP-specific schema, `_pb2.py` = the engine configured for OpAMP.**

Generating the code rather than hand-writing it means we can't get a field number wrong, and when the spec adds fields we re-run one command. We commit the generated files so you don't need to run `protoc` just to try the demo.

### A number that is really a list: bitmasks

Look at the `capabilities` line in the output, for example `capabilities: 18437  # ReportsStatus | ReportsEffectiveConfig | ReportsHealth | ReportsAvailableComponents`. The agent sends one number, but it is really a set of yes/no answers. Each capability owns one bit (1, 2, 4, 8, ...), and the agent adds up the ones it supports: `1 + 4 + 2048 + 16384 = 18437`. To decode it, check which bits are set (`bitmask & bit`) against the `AgentCapabilities` enum, which is what `capability_names()` in `server.py` does. The part after `#` is added by our server, not by protobuf.

### Why do we need to decode at all?

Because the server needs to **understand** the agent to manage it: who it is (`instance_uid`), what it is (`agent_description`), what it can do (`capabilities`), whether it's healthy (`health`), and which config it's running (`effective_config`). We also need to build a **reply** in the same format. You can't write a `ServerToAgent` message by hand-assembling bytes. Well, you could, but you shouldn't.

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


## Regenerate the protobuf code

The `.proto` files were downloaded from the `main` branch of opamp-spec (commit `61372c6`, October 2026). The generated code needs a `protobuf` runtime at least as new as the version that generated it (7.35.1), which `requirements.txt` guarantees.

```sh
python -m grpc_tools.protoc -Iproto --python_out=. proto/opamp/v1/*.proto
```

## Limitations

The reply contains nothing but the UID. The server doesn't yet remember agents or send them anything such as config. That's the next step.
