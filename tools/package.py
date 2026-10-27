#!/usr/bin/env python3
"""Build a source-only release from an explicit allowlist; refuse secret-like text."""
import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = '''
.env.example
.gitignore
LICENSE
README.md
analysis.py
core.py
data_index.py
models.py
run.py
requirements.txt
requirements-dev.txt
configs/example.json
configs/screening.example.json
data/sources.json
data/selected.json
data/screening.json
data/README.md
docker/claude.Dockerfile
harnesses/__init__.py
harnesses/agents.py
harnesses/bridge.py
harnesses/harbor.py
harnesses/runner.py
harnesses/tessl.py
evolution/__init__.py
evolution/evidence.py
evolution/gate.py
evolution/pipeline.py
evolution/rewrite.py
screening/select_pairs.py
prompts/README.md
prompts/meta_skill.md
prompts/no_meta_baseline.md
prompts/one_sentence_rewrite.md
prompts/output_contract.md
prompts/failure_capsule.md
interfaces/openhands.json
interfaces/claude_code.json
tests/conftest.py
tests/test_protocol.py
tests/test_clients.py
tests/test_indexes.py
tools/package.py
'''.split()

PATTERNS = {
    'credential': re.compile(r'(?:gh[pousr]_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9_-]{24,}|AKIA[A-Z0-9]{16})'),
    'private-key': re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
    'credential-in-url': re.compile(r'https?://[^\s/]+:[^\s/]+@|https?://(?:gh[pousr]_|sk-)[^\s/]+@'),
    'private-endpoint': re.compile(r'https?://(?:10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+)'),
    'host-workspace-path': re.compile(r'/mnt/[A-Za-z0-9_/-]+|/home/(?!\*|node(?:/|\b))[a-zA-Z][a-zA-Z0-9_.-]*/'),
}


def validate_indexes(payload):
    allowed = {'benchmark', 'task', 'path', 'skills', 'skill_paths'}
    indexes = {}
    for name, count in [('selected', 103), ('screening', 607)]:
        rows = json.loads(payload[f'data/{name}.json'])['pairs']
        if len(rows) != count:
            raise ValueError(f'The {name} index must contain {count} pairs')
        if any(set(row) != allowed for row in rows):
            raise ValueError('Index fields must match the source-identity schema')
        identities = {(row['benchmark'], row['task']): row for row in rows}
        if len(identities) != len(rows):
            raise ValueError(f'The {name} index contains duplicate identities')
        indexes[name] = identities
    selected, screening = indexes['selected'], indexes['screening']
    if not selected.keys() <= screening.keys():
        raise ValueError('The selected index must be a subset of the screening index')
    if any(row != screening[key] for key, row in selected.items()):
        raise ValueError('Task and skill references must match across both indexes')


def collect():
    payload = {}
    for name in FILES:
        path = ROOT / name
        if path.is_symlink() or not path.is_file():
            raise ValueError(f'Missing or symlinked release file: {name}')
        body = path.read_bytes()
        text = body.decode('utf-8')
        for label, pattern in PATTERNS.items():
            if pattern.search(text):
                raise ValueError(f'Release audit failed: {label} in {name}; matched values are not printed')
        payload[name] = body
    validate_indexes(payload)
    return payload


def build(out):
    payload = collect()
    # Stable metadata avoids including machine usernames or local timestamps.
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise ValueError('Output ZIP already exists; choose a new path')
    manifest = {name: hashlib.sha256(body).hexdigest() for name, body in sorted(payload.items())}
    payload['MANIFEST.sha256.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, body in sorted(payload.items()):
            info = zipfile.ZipInfo('skill-adaptation/' + name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, body)
    print(f'{out}: {len(payload)} files, {out.stat().st_size} bytes')
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    build(parser.parse_args().out)
