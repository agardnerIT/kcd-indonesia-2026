#!/bin/sh
# Start step 4: the agent (OpAMP Supervisor + collector) in Docker, plus the server in this terminal.
# Resets logs/file.log (three seeded DEBUG lines) and remote-config.yaml (baseline: DEBUG dropped). Ctrl-C stops everything.
# Watch the collector from another terminal with ./watch-collector.sh
cd "$(dirname "$0")" || exit 1
ROOT=$(cd .. && pwd)

# One venv for all steps: the active one, else one at the project root, else create ROOT/.venv
if [ -n "$VIRTUAL_ENV" ]; then VENV=$VIRTUAL_ENV
elif [ -x "$ROOT/bin/python" ]; then VENV=$ROOT
else VENV=$ROOT/.venv; [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"; fi
"$VENV/bin/pip" install -q -r "$ROOT/requirements.txt"

./stop.sh > /dev/null 2>&1   # clean slate: removes the old container (and its saved file offsets)

docker compose up -d --build
echo "agent started; watch it with ./watch-collector.sh"

"$VENV/bin/python" server.py &
echo $! > .server.pid
trap 'echo; ./stop.sh; exit 0' INT TERM
wait
./stop.sh
