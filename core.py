"""Small, dependency-free utilities shared by the public entry points."""
import hashlib
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def contained(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or "\\" in str(relative):
        raise ValueError("Expected a relative path inside the declared root")
    target = root / rel
    if not target.resolve().is_relative_to(root):
        raise ValueError("Path escapes the declared root")
    for p in (target, *target.parents):
        if p == root:
            break
        if p.is_symlink():
            raise ValueError("Symlink paths are not accepted")
    return target


def files(root):
    root = Path(root)
    return sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()
                  and not any(x in p.relative_to(root).parts for x in
                              (".git", "__pycache__", ".pytest_cache", "node_modules", ".venv")))


def tree_hash(root):
    h = hashlib.sha256()
    for p in files(root):
        h.update(p.relative_to(root).as_posix().encode() + b"\0")
        h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()


def reward(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("Reward must be a numeric score")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("Reward must be finite and in [0, 1]")
    return float(value)


def load_config(path):
    config = read_json(path)
    for name, model in config.get("models", {}).items():
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", name):
            raise ValueError("Model profile names must be simple directory-safe identifiers")
        if not model.get("model") or not model.get("api_key_env"):
            raise ValueError(f"Model {name} needs model and api_key_env")
        if "api_key" in model:
            raise ValueError("Store credentials in environment variables, not config files")
        if model.get("api_format", "openai") not in ("openai", "anthropic"):
            raise ValueError(f"Unsupported API format for {name}")
    return config


def model_spec(config, name):
    if name not in config.get("models", {}):
        raise ValueError(f"Unknown model profile: {name}")
    return config["models"][name]


def credential(spec):
    key = os.environ.get(spec["api_key_env"])
    if not key:
        raise ValueError(f"Set {spec['api_key_env']} in your environment")
    return key


def redact(text, config):
    for spec in config.get("models", {}).values():
        value = os.environ.get(spec.get("api_key_env", ""), "")
        if value:
            text = text.replace(value, "[REDACTED]")
    return text
