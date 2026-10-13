"""Step 1: a bare-bones OpAMP server that prints whatever agents send it.

OpAMP over plain HTTP: agents POST a protobuf-encoded AgentToServer message to
/v1/opamp. We don't decode it yet - we just dump the raw bytes.

Note: Coded by Claude
"""
import uvicorn
from fastapi import FastAPI, Request, Response

app = FastAPI(title="Bare-bones OpAMP server")


@app.post("/v1/opamp")
async def opamp(request: Request) -> Response:
    body = await request.body()

    print(f"--- {request.method} {request.url.path} from {request.client.host} ---")
    for name, value in request.headers.items():
        print(f"{name}: {value}")
    print(f"body ({len(body)} bytes):")
    print(body)
    print(body.hex(" "))
    print(flush=True)

    # An empty body is a valid (all defaults) ServerToAgent protobuf message.
    return Response(media_type="application/x-protobuf")


if __name__ == "__main__":
    print("Starting server on http://localhost:4320")
    uvicorn.run(app, host="0.0.0.0", port=4320, log_level="warning")
