"""Expose OpenAI-compatible models to Claude Code via Anthropic Messages."""
import contextlib
import os
import secrets
import socket
import subprocess
import threading
import time

from core import credential


@contextlib.contextmanager
def claude_endpoint(spec, runtime):
    if spec.get("api_format", "openai") == "anthropic":
        base = spec.get("base_url", "https://api.anthropic.com").rstrip("/")
        yield base.removesuffix("/v1"), credential(spec), spec["model"]
        return
    os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
    import litellm
    import uvicorn
    from fastapi import FastAPI, Request
    from fastapi.responses import JSONResponse, StreamingResponse

    # Many compatible providers implement Chat Completions but not Responses.
    previous_route = litellm.use_chat_completions_url_for_anthropic_messages
    litellm.use_chat_completions_url_for_anthropic_messages = True
    app = FastAPI()
    token = secrets.token_urlsafe(32)
    key = credential(spec)

    @app.post("/v1/messages")
    async def messages(request: Request):
        if request.headers.get("x-api-key") != token and request.headers.get("authorization") != f"Bearer {token}":
            return JSONResponse({"error": {"type": "authentication_error", "message": "Invalid bridge token"}}, 401)
        body = await request.json()
        allowed = {k: v for k, v in body.items() if k in (
            "messages", "max_tokens", "system", "tools", "tool_choice", "stream", "temperature", "top_p", "stop_sequences")}
        allowed.update(spec.get("parameters", {}))
        try:
            response = await litellm.anthropic_messages(
                model="openai/" + spec["model"], api_key=key,
                api_base=spec.get("base_url", "https://api.openai.com/v1"),
                num_retries=0, timeout=spec.get("timeout", 600), **allowed)
            if body.get("stream"):
                return StreamingResponse(response, media_type="text/event-stream")
            return JSONResponse(response.model_dump() if hasattr(response, "model_dump") else response)
        except Exception:
            return JSONResponse({"error": {"type": "api_error", "message": "Upstream model request failed"}}, 502)

    sock = socket.socket()
    sock.bind((runtime.get("bridge_bind", "0.0.0.0"), 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="critical", access_log=False))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [sock]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started:
            if not thread.is_alive() or time.monotonic() > deadline:
                raise RuntimeError("API bridge did not start")
            time.sleep(0.02)
        host = runtime.get("bridge_host")
        if not host:
            probe = subprocess.run(["docker", "network", "inspect", "bridge", "--format",
                                    "{{(index .IPAM.Config 0).Gateway}}"], capture_output=True, text=True, check=True)
            host = probe.stdout.strip()
        if not host:
            raise ValueError("Set runtime.bridge_host to a host address reachable from Docker")
        yield f"http://{host}:{port}", token, spec["model"]
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        sock.close()
        litellm.use_chat_completions_url_for_anthropic_messages = previous_route
