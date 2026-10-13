#!/bin/sh
# Stop step 4: the server and the agent container, and reset logs/file.log and remote-config.yaml.
cd "$(dirname "$0")" || exit 1

[ -f .server.pid ] && kill "$(cat .server.pid)" 2> /dev/null
rm -f .server.pid

docker compose down > /dev/null 2>&1
cp examples/baseline.yaml remote-config.yaml
printf 'DEBUG starting up\nDEBUG loaded 3 plugins\nDEBUG cache miss key=user:42\n' > logs/file.log
echo "stopped"
exit 0
