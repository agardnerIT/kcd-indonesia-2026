"""Step 2: decode what agents send us and reply with a valid ServerToAgent.

Builds on step 1: same endpoint (POST /v1/opamp, protobuf body), but the body
is now parsed into an AgentToServer message and pretty-printed.

Regenerate the protobuf code (after `pip install protobuf grpcio-tools`) with:
    python -m grpc_tools.protoc -Iproto --python_out=. proto/opamp/v1/*.proto
"""
import re

import uvicorn
from fastapi import FastAPI, Request, Response
from google.protobuf import text_format

from opamp.v1 import opamp_pb2

app = FastAPI(title="Bare-bones OpAMP server")


def capability_names(bitmask: int) -> list[str]:
    """Turn the capabilities bitmask into names, e.g. ['ReportsStatus', 'ReportsHealth']."""
    return [
        name.removeprefix("AgentCapabilities_")
        for name, bit in opamp_pb2.AgentCapabilities.items()
        if bit and bitmask & bit
    ]


def describe(msg: opamp_pb2.AgentToServer) -> str:
    """The message as text, with the capabilities bitmask spelled out next to the number."""
    text = text_format.MessageToString(msg, as_utf8=True)
    names = " | ".join(capability_names(msg.capabilities))
    return re.sub(r"^(capabilities: \d+)$", rf"\1  # {names}", text, flags=re.M)


@app.post("/v1/opamp")
async def opamp(request: Request) -> Response:
    msg = opamp_pb2.AgentToServer()
    msg.ParseFromString(await request.body())

    print(f"--- agent {msg.instance_uid.hex()} (seq {msg.sequence_num}) ---")
    print(describe(msg), flush=True)

    # Every response must carry the agent's instance_uid back to it.
    response = opamp_pb2.ServerToAgent(instance_uid=msg.instance_uid)
    return Response(response.SerializeToString(), media_type="application/x-protobuf")


if __name__ == "__main__":
    print("Starting server on http://localhost:4320")
    uvicorn.run(app, host="0.0.0.0", port=4320, log_level="warning")
