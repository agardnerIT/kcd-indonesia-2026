"""Step 3: keep track of the agents that connect.

Builds on step 2: same decode-and-reply endpoint, plus an in-memory registry of
agents keyed by instance_uid, and a GET /agents endpoint to list them.
"""
import time
from dataclasses import dataclass, field

import uvicorn
from fastapi import FastAPI, Request, Response

from opamp.v1 import opamp_pb2

app = FastAPI(title="Bare-bones OpAMP server")


@dataclass
class Agent:
    uid: str
    description: dict = field(default_factory=dict)
    capabilities: list = field(default_factory=list)
    healthy: bool | None = None
    last_sequence_num: int = 0
    last_seen: float = 0.0
    connected: bool = True


# The "database": instance_uid (hex) -> Agent. Lost on restart, which is fine for a demo.
agents: dict[str, Agent] = {}


def attributes(kvs) -> dict:
    """Flatten a list of OpAMP KeyValue messages into a plain dict of strings."""
    return {kv.key: kv.value.string_value for kv in kvs}


def capability_names(bitmask: int) -> list[str]:
    """Turn the capabilities bitmask into names, e.g. ['ReportsStatus', 'AcceptsRemoteConfig']."""
    return [
        name.removeprefix("AgentCapabilities_")
        for name, bit in opamp_pb2.AgentCapabilities.items()
        if bit and bitmask & bit
    ]


def update_registry(msg: opamp_pb2.AgentToServer) -> bool:
    """Record what the agent told us. Returns True if we need the agent's full state."""
    uid = msg.instance_uid.hex()
    agent = agents.get(uid)
    is_new = agent is None
    if is_new:
        agent = agents[uid] = Agent(uid)
        print(f"+ agent {uid} connected", flush=True)

    # Agents may omit unchanged fields to save bandwidth, so only update what is present.
    if msg.HasField("agent_description"):
        agent.description = {
            **attributes(msg.agent_description.identifying_attributes),
            **attributes(msg.agent_description.non_identifying_attributes),
        }
    if msg.capabilities:
        agent.capabilities = capability_names(msg.capabilities)
    if msg.HasField("health"):
        agent.healthy = msg.health.healthy

    # sequence_num goes up by 1 per message. A gap means we missed something
    # (or we restarted and lost state), so ask the agent to resend everything.
    gap = not is_new and msg.sequence_num != agent.last_sequence_num + 1
    if gap:
        print(f"! agent {uid}: expected seq {agent.last_sequence_num + 1}, got {msg.sequence_num}", flush=True)

    agent.last_sequence_num = msg.sequence_num
    agent.last_seen = time.time()
    agent.connected = not msg.HasField("agent_disconnect")
    if not agent.connected:
        print(f"- agent {uid} disconnected", flush=True)

    # A brand new agent that opens with sequence_num > 1 also skipped ahead (we lost state).
    return gap or (is_new and msg.sequence_num != 1)


@app.post("/v1/opamp")
async def opamp(request: Request) -> Response:
    msg = opamp_pb2.AgentToServer()
    msg.ParseFromString(await request.body())

    needs_full_state = update_registry(msg)

    response = opamp_pb2.ServerToAgent(
        instance_uid=msg.instance_uid,  # required in every response
        capabilities=opamp_pb2.ServerCapabilities_AcceptsStatus,
    )
    if needs_full_state:
        response.flags = opamp_pb2.ServerToAgentFlags_ReportFullState
    return Response(response.SerializeToString(), media_type="application/x-protobuf")


@app.get("/agents")
async def list_agents() -> list[dict]:
    now = time.time()
    return [
        {
            "instance_uid": a.uid,
            "connected": a.connected,
            "healthy": a.healthy,
            "seconds_since_seen": round(now - a.last_seen, 1),
            "description": a.description,
            "capabilities": a.capabilities,
        }
        for a in agents.values()
    ]


if __name__ == "__main__":
    print("Starting server on http://localhost:4320")
    uvicorn.run(app, host="0.0.0.0", port=4320, log_level="warning")
