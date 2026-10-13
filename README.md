# kcd-indonesia-2026
Slides and Hands on content for my talk at KCD Indonesia 2026

## Slides

Google Slides: https://dt-url.net/kcd-indonesia-2026

## Hands On

### Building an OpAMP server

This repository is a companion code repo to the KCD Indonesia 2026 talk. In it, we will walk through building an OpAMP server.

The server will be implemented in Python and will be as bare-bones as possible - we're illustrating concepts not designing a production ready

We will use the OpenTelemtry contrib collector (running in docker) as a client.

As part of the demo, we should be able to connect 2 or 3 collectors. We call each collector an "agent". We acknowledge that any other software capable of "speaking OpAMP" could be a client, but we're focussed on OTel Collectors.

### Setup

One virtual environment and one `requirements.txt` serve every step:

```sh
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Every step folder has a `start.sh` and `stop.sh`. They use the active venv, or one at the project root, or create `.venv`.

### Steps

Each `stepN/` folder is a self-contained stage: its own server, protobuf code, collector config and start/stop scripts. Every `server.py` builds on the previous one. Only the Python dependencies (`requirements.txt`) and the virtual environment are shared.

| Step | What it adds |
|------|--------------|
| [step1](step1/README.md) | FastAPI endpoint that receives OpAMP messages and prints the raw bytes |
| [step2](step2/README.md) | Decode the protobuf and reply with a valid `ServerToAgent` |
| [step3](step3/README.md) | Track connected agents in a registry and list them at `GET /agents` |
| [step4](step4/README.md) | WebSocket transport and remote config: during a simulated incident, edit a watched file to temporarily enable DEBUG log capture on a collector (via the OpAMP Supervisor) |

