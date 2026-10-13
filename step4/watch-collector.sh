#!/bin/sh
# Show just "LEVEL message" for each log record the collector prints, instead of the
# supervisor's JSON-wrapped, multi-line debug exporter output.
cd "$(dirname "$0")"
docker compose logs -f --no-log-prefix agent \
  | jq --unbuffered -r 'select(.logger=="supervisor.collector") | .msg | fromjson? | .msg' \
  | awk '
      /^SeverityText:/ { sev = $2 }
      /^Body:/ { sub(/^Body: Str\(/, ""); sub(/\)$/, ""); printf "%-6s %s\n", sev, $0; fflush() }'
