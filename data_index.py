"""Resolve existing benchmark tasks; never generate or redistribute task data."""
import hashlib
import shutil
import subprocess
import tempfile
import tomllib
import urllib.request
import zipfile
from pathlib import Path

from core import ROOT, contained, read_json, tree_hash, write_json


def source_root(config, benchmark):
    if benchmark in config.get("benchmark_roots", {}):
        return Path(config["benchmark_roots"][benchmark]).resolve()
    return Path(config.get("data_root", "data/upstream")).resolve() / benchmark


def fetch(config, benchmark):
    spec = read_json(ROOT / "data/sources.json")["sources"][benchmark]
    dest = source_root(config, benchmark)
    if dest.exists():
        raise ValueError(f"Destination already exists: {dest}; use data-check to validate it")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        temp = Path(tmp)
        checkout = temp / "checkout"
        if spec["kind"] == "git":
            subprocess.run(["git", "init", "-q", str(checkout)], check=True)
            subprocess.run(["git", "-C", str(checkout), "fetch", "--depth", "1",
                            spec["url"], spec["revision"]], check=True)
            subprocess.run(["git", "-C", str(checkout), "checkout", "--detach", "FETCH_HEAD"], check=True)
        else:
            archive = temp / "tasks.zip"
            url = f"{spec['url']}/resolve/{spec['revision']}/{spec['filename']}"
            h = hashlib.sha256()
            with urllib.request.urlopen(url, timeout=120) as response, archive.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    h.update(chunk)
                    out.write(chunk)
            if h.hexdigest() != spec["sha256"]:
                raise ValueError("Upstream archive checksum mismatch")
            checkout.mkdir()
            with zipfile.ZipFile(archive) as z:
                for member in z.infolist():
                    target = contained(checkout, member.filename)
                    if (member.external_attr >> 16) & 0o170000 == 0o120000:
                        raise ValueError("Archive contains a symlink")
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with z.open(member) as src, target.open("wb") as out:
                            shutil.copyfileobj(src, out)
        if benchmark == "docops":
            materialize_docops_skills(checkout)
        write_json(checkout / ".source.json", spec)
        shutil.move(str(checkout), dest)
    return dest


def materialize_docops_skills(root):
    """Resolve shared skill references in the upstream release without inventing content."""
    selected = {p["task"]: p["skills"] for name in ("screening", "selected")
                for p in read_json(ROOT / f"data/{name}.json")["pairs"] if p["benchmark"] == "docops"}
    for task in (root / "tasks").iterdir():
        dest = task / "environment/skills"
        if not task.is_dir() or list(dest.glob("*/SKILL.md")):
            continue
        metadata = tomllib.loads((task / "task.toml").read_text()).get("metadata", {})
        kind = str(metadata.get("doc_type", "")).lower()
        names = selected.get(task.name) or [{"docx": "doc", "word": "doc", "excel": "xlsx", "powerpoint": "pptx"}.get(kind, kind)]
        for name in names:
            source = contained(root, f"skills/{name}")
            if not (source / "SKILL.md").is_file():
                raise ValueError(f"Missing upstream shared skill for {task.name}: {name}")
            shutil.copytree(source, dest / name, dirs_exist_ok=True)


def resolve(config, pair):
    benchmark, name = pair["benchmark"], pair["task"]
    spec = read_json(ROOT / "data/sources.json")["sources"][benchmark]
    root = source_root(config, benchmark)
    for folder in spec["task_roots"]:
        path = contained(root, f"{folder}/{name}")
        if path.is_dir():
            return path
    raise ValueError(f"Missing upstream task {benchmark}/{name}; run fetch first")


def instruction(task, benchmark):
    names = ["scenario/task.md", "task.md"] if benchmark == "tessl" else ["instruction.md"]
    for name in names:
        p = task / name
        if p.is_file():
            return p.read_text()
    raise ValueError("Upstream task instruction is missing")


def skills(task, benchmark):
    path = task / ("skills" if benchmark == "tessl" else "environment/skills")
    if not list(path.glob("*/SKILL.md")):
        raise ValueError(f"No skill bundle at {path}")
    return path


def inputs(task):
    return task / "scenario/inputs" if (task / "scenario").is_dir() else task / "inputs"


def pairs(config, suite="selected", benchmark=None, task=None):
    if suite in ("selected", "screening"):
        found = read_json(ROOT / f"data/{suite}.json")["pairs"]
    elif suite == "upstream":
        found = []
        for ds, spec in read_json(ROOT / "data/sources.json")["sources"].items():
            if benchmark and benchmark != ds:
                continue
            for directory in spec["task_roots"]:
                for p in sorted((source_root(config, ds) / directory).glob("*")):
                    if not p.is_dir():
                        continue
                    try:
                        skills(p, ds)
                        instruction(p, ds)
                    except ValueError:
                        continue
                    found.append({"benchmark": ds, "task": p.name})
    else:
        found = read_json(suite)["pairs"]
    out = [p for p in found if (not benchmark or p["benchmark"] == benchmark)
           and (not task or p["task"] == task)]
    identities = [(p["benchmark"], p["task"]) for p in out]
    if not out or len(identities) != len(set(identities)):
        raise ValueError("Task selection is empty or contains duplicate identities")
    return out


def check(config, selected):
    result = []
    for pair in selected:
        task = resolve(config, pair)
        skill = skills(task, pair["benchmark"])
        actual = sorted(p.parent.name for p in skill.glob("*/SKILL.md"))
        if pair.get("skills") and pair["skills"] != actual:
            raise ValueError(f"Skill bundle differs from the index: {pair['task']}")
        instruction(task, pair["benchmark"])
        if pair["benchmark"] == "tessl":
            if not (task / "rubrics/task-completion.json").is_file():
                raise ValueError("Task-completion rubric missing")
        elif not all((task / p).exists() for p in ("task.toml", "environment/Dockerfile", "tests")):
            raise ValueError("Harbor task is incomplete")
        result.append({"benchmark": pair["benchmark"], "task": pair["task"], "sha256": tree_hash(task)})
    return result
