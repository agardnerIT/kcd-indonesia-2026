# Step 4: push config to a running collector

The demo: a collector tails a log file and, as is normal in production, drops DEBUG logs to save cost and noise. Then **there's an incident**. We need more detail, right now. We **change a file on the server** (`remote-config.yaml`) to temporarily *enable* DEBUG log capture, and watch the DEBUG lines start flowing, without touching the collector ourselves. When the incident is over, we revert it.

## Why a Supervisor?

You might expect the collector's own `opamp` extension to accept a config from the server and apply it. It doesn't: it reports status, health and its effective config, but can't change the collector it lives in. (A collector can't easily rewrite and restart itself.)

The job belongs to the **OpAMP Supervisor**, a small program that:

1. keeps the OpAMP connection to the server,
2. starts the collector as a **child process**,
3. when a remote config arrives, **merges it** with the collector's local config, writes the result to disk and **restarts the collector** with it,
4. reports back `APPLYING`, then `APPLIED` (or `FAILED`).

So in this step the "agent" is a Supervisor plus a collector, in one container ([agent/Dockerfile](agent/Dockerfile)).

## What's in the folder

| Path | What it is |
|------|-----------|
| [server.py](server.py) | The server: step 3 plus WebSocket, a watched config file and status tracking |
| [remote-config.yaml](remote-config.yaml) | **The file the server watches.** Whatever is in it is what every agent is told to run |
| [examples/baseline.yaml](examples/baseline.yaml) | Ready-made content for it: keep the local filter, so DEBUG stays dropped. This is the starting state |
| [examples/capture-debug.yaml](examples/capture-debug.yaml) | Ready-made content for it: remove the filter from the pipeline. This is incident mode |
| [agent/collector.yaml](agent/collector.yaml) | The collector's **local** config: tail the file, parse the level, drop DEBUG, print the rest |
| [agent/supervisor.yaml](agent/supervisor.yaml) | Supervisor settings: where the server is, `accepts_remote_config: true` |
| [logs/file.log](logs/file.log) | The log file, bind-mounted into the container, seeded with a few DEBUG lines (dropped at first) |
| [watch-collector.sh](watch-collector.sh) | Shows the collector's output as just `LEVEL message` |

## What changed in the server

- **WebSocket endpoint.** `/v1/opamp` now also speaks WebSocket (the HTTP endpoint is unchanged). Over HTTP, the server can only answer when the agent asks, and the Supervisor only asks every ~30 seconds. Over a WebSocket, either side can send at any time, so a push lands immediately. Both transports share one `handle_message()` function.
- **A watched file, not an endpoint.** A background task in the server checks `remote-config.yaml` once a second. When its contents change, the server wraps it in an `AgentRemoteConfig` message and sends it to every connected agent that accepts remote config. Agents that connect later get the current file straight away. Each config carries a **hash** (SHA-256 of its contents). The agent echoes the hash back when it has applied it, so the server knows it's done.
- **Only capable agents.** It targets agents that said they `AcceptsRemoteConfig`. Plain collectors from the earlier steps are skipped. Add `?agent=<instance_uid>` to target just one.
- **Status tracking.** The server records each agent's `RemoteConfigStatus` (and logs `APPLYING` / `APPLIED` / `FAILED`) and its **effective config**, which you can read at `GET /agents/{uid}/effective-config`.
- **Server capabilities.** The server now says it `OffersRemoteConfig` and `AcceptsEffectiveConfig`.

### How the merge works

The collector runs `local config` + `remote config`, merged key by key. Our local config sends logs through `file_log` to `debug` via a `filter/drop_debug` processor. The remote config only says "this pipeline now has no processors" (lists are replaced, not appended), so the small diff is all we push. The filter, defined locally, is:

```yaml
- severity_number < SEVERITY_NUMBER_INFO
```

That works because the local config parses the first word of each line (`DEBUG`, `INFO`...) into the log record's severity.

## Quick start

```sh
./start.sh   # resets logs/file.log, starts the agent in Docker and the server here; Ctrl-C stops all
./stop.sh    # stop anything left running (and reset logs/file.log)
```

Then use `./watch-collector.sh` in a second terminal and jump to step 4 below.

## Run the demo (by hand)

You need four terminals.

**1. The server**

```sh
python server.py   # with the shared venv active, see the root README
```

If you see `No supported WebSocket library detected`, your venv is missing `websockets`. Re-run `pip install -r ../requirements.txt`.

**2. The agent** (builds the image the first time)

```sh
docker compose up --build
```

**3. Watch what the collector prints**

```sh
./watch-collector.sh
```

The three seeded DEBUG lines are dropped, so you see nothing yet. That's the production baseline.

**4. Write some logs. Only INFO comes through.**

```sh
echo "INFO user logged in" >> logs/file.log
echo "DEBUG cache miss"    >> logs/file.log
```

**5. Incident! Enable DEBUG capture**

Overwrite `remote-config.yaml` to remove the filter. Copying the example does it (or open the file in your editor and paste the example in, then save):

```sh
cp examples/capture-debug.yaml remote-config.yaml
```

In the server terminal you'll see `remote-config.yaml changed`, `pushed`, then `APPLYING`, then `APPLIED`. The collector restarts, and `curl -s localhost:4320/agents/<uid>/effective-config` now shows the pipeline without the filter. (Get the uid from `curl -s localhost:4320/agents`.)

**6. Write more logs. DEBUG comes through too.**

```sh
echo "INFO payment failed"            >> logs/file.log
echo "DEBUG retrying gateway call"  >> logs/file.log
```

**7. Incident over: revert**

```sh
cp examples/baseline.yaml remote-config.yaml
```

DEBUG lines are dropped again. `./stop.sh` (or the next `./start.sh`) resets `remote-config.yaml` and `logs/file.log`.

## Good to know

- **Why can't the Supervisor just read the file itself?** It runs somewhere else (here, in a container) and OpAMP is its only link to the server. Your file lives on the *server*, so the server has to send it. That is the whole point of OpAMP: change one file centrally and a fleet of collectors follows. The Supervisor also doesn't watch its own local config, so mounting the file into the container wouldn't work either.
- **One restart at startup.** The server sends `remote-config.yaml` as soon as the agent connects, so you'll see one `APPLIED` right at the start, even though the starting config is the same as the local one.

- **The collector remembers how far it has read** (the `file_storage` extension in the local config). Without it, every restart would re-read the whole file and repeat old INFO lines, which would muddy the demo.
- **Supervisor output is noisy.** It wraps the collector's log in JSON, hence `watch-collector.sh`. It needs `jq`.
- **`GET /agents` also lists any plain collectors from the earlier steps** that are still pointed at this server. They show `remote_config_status: UNSET` and are never sent the file.
- **Adding more agents:** each agent needs its own log file. Copy the `agent` service in [docker-compose.yaml](docker-compose.yaml) and give it a different `logs` folder.
- Versions are pinned to **0.162.0** for both the collector and the Supervisor in [agent/Dockerfile](agent/Dockerfile) (and the plain collectors in steps 1-3). Keep the two in step 4 on the same version when you upgrade.
