"""Deterministic evidence from the last rollout, never from hidden test sources."""
import json
from pathlib import Path

from core import read_json


def clip(text, limit):
    return text if len(text) <= limit else text[:limit // 2] + '\n[...middle omitted...]\n' + text[-limit // 2:]


def trajectory(trial, cap=9000):
    trial = Path(trial)
    out, calls, failures = [], [], []
    if (trial / 'trajectory.json').exists():
        data = read_json(trial / 'trajectory.json')
        for step in data.get('steps', []):
            if step.get('source') in ('user', 'system'):
                continue
            for call in step.get('tool_calls', []):
                label = f"{call.get('function_name')} {json.dumps(call.get('arguments', {}))[:220]}"
                calls.append(label)
                out.append(f'[{len(calls)}] {label}')
            for obs in (step.get('observation') or {}).get('results', []):
                text = str(obs.get('content', ''))[:300]
                out.append('  -> ' + text)
                if obs.get('is_error'):
                    failures.append(calls[-1] if calls else text)
            if step.get('message'):
                out.append(str(step['message'])[:1200])
    elif (trial / 'transcript.jsonl').exists():
        for line in (trial / 'transcript.jsonl').read_text(errors='replace').splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            content = (event.get('message') or {}).get('content', [])
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get('type') == 'tool_use':
                    label = f"{block.get('name')} {json.dumps(block.get('input', {}))[:220]}"
                    calls.append(label)
                    out.append(f'[{len(calls)}] {label}')
                elif block.get('type') == 'tool_result':
                    out.append('  -> ' + str(block.get('content', ''))[:300])
                    if block.get('is_error'):
                        failures.append(calls[-1] if calls else '(unmatched tool result)')
            if event.get('type') == 'result':
                out.append('[final] ' + str(event.get('result', ''))[:1200])
    return clip('\n'.join(out) or '(no tool trajectory recorded)', cap), {
        'calls': len(calls), 'failed': len(failures), 'first_failed': next(iter(failures), '(none)'),
        'last_write': next((c for c in reversed(calls) if any(w in c.lower() for w in ('write', 'edit', 'create'))), '(none)')}


def evidence(trial, value):
    trial = Path(trial)
    digest, stats = trajectory(trial)
    checks_path = trial / 'verifier/ctrf.json'
    checks = read_json(checks_path).get('results', {}).get('tests', []) if checks_path.exists() else []
    groups = {'failed': [], 'passed': [], 'other': []}
    for check in checks:
        status = check.get('status', 'unknown')
        bucket = status if status in ('failed', 'passed') else 'other'
        groups[bucket].append(str(check.get('name', '')) + ': ' + str(check.get('message', ''))[:350])
    state = 'unknown' if value is None else ('passed' if value == 1 else 'failed' if value == 0 else 'partial')
    parts = ['## Failure capsule (deterministically extracted)', f'OUTCOME: {state}', f'REWARD: {value}']
    for key, label in [('failed', 'FAILED CHECKS TO REPAIR'), ('passed', 'PASSED CHECKS TO PRESERVE'), ('other', 'NON-FAILURE CHECK STATUSES')]:
        parts += [label + ':', '\n'.join('- ' + s for s in groups[key]) or '- (none)']
    parts += [f"TOOL CALLS: {stats['calls']} total; {stats['failed']} failed",
              f"FIRST FAILED TOOL CALL: {stats['first_failed']}", f"LAST RECORDED WRITE-LIKE ACTION: {stats['last_write']}",
              '## Trajectory digest', digest, '## Verifier output']
    for name in ('test-stdout.txt', 'test-stderr.txt'):
        p = trial / 'verifier' / name
        if p.exists():
            parts.append(clip(p.read_text(errors='replace'), 9000))
    return '\n\n'.join(parts)
