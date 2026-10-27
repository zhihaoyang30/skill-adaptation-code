"""Shared adaptation step: prompt, one format repair, atomic validity gate."""
import re
import shutil

import yaml

from core import ROOT, contained, files, model_spec, tree_hash, write_json
from data_index import instruction
from evolution.evidence import evidence
from evolution.gate import gate, secrets_from_tests
from models import chat

ARMS = {"meta": "meta_skill.md", "no_meta": "no_meta_baseline.md", "one_sentence": "one_sentence_rewrite.md"}
FILE = re.compile(r"<<<FILE path=([^\n>]+)>>>\r?\n(.*?)\r?\n?<<<END>>>", re.S)
NO_CHANGE = re.compile(r"\A\s*<<<NO_CHANGE>>>.*?<<<END_NO_CHANGE>>>\s*\Z", re.S)


def parse(reply):
    if NO_CHANGE.fullmatch(reply):
        return {}
    blocks = list(FILE.finditer(reply))
    if not blocks or FILE.sub("", reply).strip():
        raise ValueError("Return only complete FILE blocks or one NO_CHANGE block")
    out = {}
    for block in blocks:
        name = block[1].strip()
        if name in out:
            raise ValueError("Duplicate FILE path")
        out[name] = block[2] + "\n"
    return out


def secret_tokens(task, benchmark):
    hidden = [task / name for name in ("tests", "solution", "rubrics")]
    private, public = [], []
    for f in files(task):
        if f.stat().st_size > 2_000_000:
            continue
        try:
            text = f.read_text()
        except UnicodeError:
            continue
        is_hidden = any(f.is_relative_to(p) for p in hidden)
        (private if is_hidden else public).append(text)
    return secrets_from_tests("\n".join(private), "\n".join(public))


def user_message(task, benchmark, bundle, last_trial=None):
    interface = ROOT / "interfaces" / ("openhands.json" if benchmark == "skillsbench" else "claude_code.json")
    parts = ["## Authoritative task instruction", instruction(task, benchmark),
             "## Executor tool interface", interface.read_text(), "## Current skill bundle"]
    for f in files(bundle):
        rel = f.relative_to(bundle)
        if f.name == "SKILL.md":
            parts += [f"### {rel}", f.read_text()]
        else:
            parts.append(f"Auxiliary file: {rel}")
    if last_trial:
        trial, value = last_trial
        parts.append(evidence(trial, value))
        parts.append("You know what the weak model did, which checks failed, and what the test output said. "
                     "Rewrite the skill so that the same weak model does better on the next attempt. "
                     "Do not encode expected values or test-specific answers.")
    else:
        parts.append("Your evidence is the task instruction, the skill as it stands, and the executor's tool interface. "
                     "No execution has taken place. Adapt the skill for the executor without assuming a previous failure.")
    parts.append((ROOT / "prompts/output_contract.md").read_text().split("\n---\n", 1)[-1])
    return "\n\n".join(parts)


def apply(reply, source, destination, hidden, shown):
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Skill bundles must contain regular files, not symlinks")
    changes = parse(reply)
    log = []
    accepted = True
    for name, new in changes.items():
        try:
            path = contained(source, name)
            if not path.is_file():
                raise ValueError("Path does not name an existing skill file")
            old = path.read_text()
            if path.name == "SKILL.md":
                for text in (old, new):
                    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
                    header = yaml.safe_load(match[1]) if match else None
                    if not isinstance(header, dict) or not isinstance(header.get("name"), str) or not header.get("description"):
                        raise ValueError("Invalid skill frontmatter")
            ok, reason, seen, _ = gate(old, new, name, hidden, shown)
            log.append({"file": name, "accepted": ok, "reason": reason, "visible_token_count": len(seen)})
            accepted &= ok
        except (ValueError, UnicodeError, yaml.YAMLError) as exc:
            accepted = False
            log.append({"file": name, "accepted": False, "reason": str(exc)})
    if destination.exists():
        raise ValueError("Rewrite destination already exists")
    shutil.copytree(source, destination, symlinks=False)
    if accepted:
        for name, text in changes.items():
            contained(destination, name).write_text(text)
    return {"status": "accepted" if changes and accepted else "rejected" if changes else "no_change",
            "changed": tree_hash(source) != tree_hash(destination), "files": log}


def rewrite(config, task, benchmark, rewriter, arm, source, destination, last_trial=None):
    if arm not in ARMS:
        raise ValueError("Unknown rewrite arm")
    if destination.exists() or any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Use a fresh destination and a skill bundle containing regular files")
    system = (ROOT / "prompts" / ARMS[arm]).read_text()
    user = user_message(task, benchmark, source, last_trial)
    spec = model_spec(config, rewriter)
    reply = chat(spec, system, user)
    repairs = 0
    try:
        parse(reply)
    except ValueError as exc:
        repairs = 1
        reply = chat(spec, system, user + "\n\nYour previous response was not parseable: " + str(exc)
                     + "\nReturn the required blocks only.")
    try:
        parse(reply)
    except ValueError:
        shutil.copytree(source, destination)
        result = {"status": "invalid_format", "changed": False, "files": []}
    else:
        result = apply(reply, source, destination, secret_tokens(task, benchmark), user)
    result.update(arm=arm, rewriter=rewriter, format_repairs=repairs,
                  skill_sha256=tree_hash(destination))
    write_json(destination.parent / "rewrite.json", result)
    return result
