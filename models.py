"""OpenAI Chat Completions and Anthropic Messages clients; no model allowlist."""
import json
import urllib.error
import urllib.request

from core import credential


def chat(spec, system, user):
    fmt = spec.get("api_format", "openai")
    default = "https://api.anthropic.com" if fmt == "anthropic" else "https://api.openai.com/v1"
    base = spec.get("base_url", default).rstrip("/")
    headers = {"Content-Type": "application/json"}
    params = dict(spec.get("parameters", {}))
    if any(k in params for k in ("messages", "model", "system", "stream", "tools")):
        raise ValueError("Model parameters must not override the request protocol")
    if fmt == "anthropic":
        url = base + ("/messages" if base.endswith("/v1") else "/v1/messages")
        headers.update({"x-api-key": credential(spec), "anthropic-version": "2023-06-01"})
        body = {"max_tokens": 16000, **params, "model": spec["model"],
                "system": system, "messages": [{"role": "user", "content": user}]}
    else:
        url = base + "/chat/completions"
        headers["Authorization"] = "Bearer " + credential(spec)
        body = {**params, "model": spec["model"], "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": user}]}
    request = urllib.request.Request(url, json.dumps(body).encode(), headers)
    try:
        with urllib.request.urlopen(request, timeout=spec.get("timeout", 600)) as response:
            result = json.load(response)
    except urllib.error.HTTPError as exc:
        # Provider error bodies can echo Authorization or user prompts.
        raise RuntimeError(f"Model API returned HTTP {exc.code}; check the endpoint and model") from None
    except (urllib.error.URLError, TimeoutError):
        raise RuntimeError("Model API connection failed or timed out") from None
    if fmt == "anthropic":
        text = "\n".join(b["text"] for b in result.get("content", []) if b.get("type") == "text")
    else:
        text = result["choices"][0]["message"].get("content")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Model returned no text; check output/reasoning token settings")
    return text
