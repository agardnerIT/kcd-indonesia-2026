#!/bin/sh
# Stop this step: the server and the collector containers.
#
# Coded by Claude
cd "$(dirname "$0")" || exit 1

[ -f .server.pid ] && kill "$(cat .server.pid)" 2> /dev/null
rm -f .server.pid

ids=$(docker ps -aq --filter name=kcd-agent-)
[ -n "$ids" ] && docker rm -f $ids > /dev/null
echo "stopped"
exit 0
