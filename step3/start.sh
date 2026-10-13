#!/bin/sh
# Start this step: N plain collectors ("agents") in Docker, plus the server in this terminal.
# Usage: ./start.sh [number-of-collectors]    (default 1)
# Ctrl-C stops everything.
cd "$(dirname "$0")" || exit 1
ROOT=$(cd .. && pwd)

# One venv for all steps: the active one, else one at the project root, else create ROOT/.venv
if [ -n "$VIRTUAL_ENV" ]; then VENV=$VIRTUAL_ENV
elif [ -x "$ROOT/bin/python" ]; then VENV=$ROOT
else VENV=$ROOT/.venv; [ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"; fi
"$VENV/bin/pip" install -q -r "$ROOT/requirements.txt"

./stop.sh > /dev/null 2>&1   # start from a clean slate

for i in $(seq 1 "${1:-1}"); do
  docker run -d --rm --name "kcd-agent-$i" \
    -v "$PWD/collector-config.yaml:/etc/otelcol-contrib/config.yaml" \
    otel/opentelemetry-collector-contrib:0.162.0 > /dev/null
  echo "started collector kcd-agent-$i"
done

"$VENV/bin/python" server.py &
echo $! > .server.pid
trap 'echo; ./stop.sh; exit 0' INT TERM
wait
./stop.sh
