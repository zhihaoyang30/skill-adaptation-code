#!/usr/bin/env python3
"""Public command-line entry point. Run from the release root."""
import argparse
import csv
import json
import os
import subprocess
import sys
from pathlib import Path

from core import credential, load_config, model_spec, redact, write_json
import data_index


def parser():
    ap = argparse.ArgumentParser(description="Skill adaptation and self-evolution")
    ap.add_argument("--config", type=Path, default=Path("configs/local.json"))
    commands = ap.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Check local dependencies and model configuration")
    fetch = commands.add_parser("fetch", help="Download pinned upstream benchmark releases")
    fetch.add_argument("--benchmark", choices=["skillsbench", "docops", "tessl", "all"], default="all")
    for name in ("data-check", "list", "evaluate", "adapt", "evolve", "rewrite"):
        p = commands.add_parser(name)
        p.add_argument("--suite", default="selected", help="selected, screening, upstream, or an index JSON path")
        p.add_argument("--benchmark", choices=["skillsbench", "docops", "tessl"])
        p.add_argument("--task", help="Upstream task ID")
        p.add_argument("--limit", type=int)
        if name in ("evaluate", "adapt", "evolve", "rewrite"):
            p.add_argument("--executor", default="executor", help="Configured model profile")
            p.add_argument("--out", type=Path, required=True)
        if name == "evaluate":
            p.add_argument("--models", nargs="+", help="Run several model profiles")
            p.add_argument("--conditions", nargs="+", choices=["no_skill", "with_skill"], default=["no_skill", "with_skill"])
            p.add_argument("--repeats", type=int, default=1)
        if name in ("adapt", "evolve", "rewrite"):
            p.add_argument("--arms", nargs="+", choices=["meta", "no_meta", "one_sentence"],
                           default=["meta", "no_meta"] if name == "evolve" else ["meta", "one_sentence"])
        if name in ("adapt", "rewrite"):
            p.add_argument("--rewriter", default="rewriter")
        if name == "evolve":
            p.add_argument("--rounds", type=int, default=5)
            p.add_argument("--no-evidence", action="store_true", help="Ablate trajectory and verifier feedback")
    screen = commands.add_parser("screen")
    screen.add_argument("--scores", type=Path, required=True)
    screen.add_argument("--out", type=Path, required=True)
    screen.add_argument("--tau", type=float, default=0.10)
    summary = commands.add_parser("summarize")
    summary.add_argument("--runs", type=Path, required=True)
    summary.add_argument("--out", type=Path, required=True)
    judge = commands.add_parser("judge", help="Rescore a Tessl trial without executing it again")
    judge.add_argument("--task", required=True)
    judge.add_argument("--trial", type=Path, required=True)
    return ap


def doctor(config):
    import importlib.util
    missing = []
    if sys.version_info < (3, 12):
        missing.append("Python >= 3.12")
    for module in ("harbor", "litellm", "yaml", "fastapi", "uvicorn"):
        if not importlib.util.find_spec(module):
            missing.append(module)
    for command in (["docker", "info"], ["docker", "compose", "version"]):
        try:
            if subprocess.run(command, capture_output=True).returncode:
                missing.append(" ".join(command))
        except FileNotFoundError:
            missing.append(command[0])
    for name, spec in config.get("models", {}).items():
        print(f"{name}: {spec['api_format']} / {spec['model']} / credential "
              + ("set" if os.environ.get(spec["api_key_env"]) else f"missing ({spec['api_key_env']})"))
    if missing:
        raise ValueError("Missing runtime requirements: " + ", ".join(missing))
    print("Runtime dependencies available. API reachability is checked when a run starts.")


def main():
    args = parser().parse_args()
    config = load_config(args.config)
    if args.command == "doctor":
        return doctor(config)
    if args.command == "fetch":
        for benchmark in ([args.benchmark] if args.benchmark != "all" else ["skillsbench", "docops", "tessl"]):
            print(data_index.fetch(config, benchmark), flush=True)
        return
    if args.command == "screen":
        from screening.select_pairs import select
        chosen, report = select(args.scores, config["tiers"], args.tau)
        write_json(args.out, chosen)
        write_json(args.out.with_suffix(".report.json"), report)
        print(f"Selected {len(chosen['pairs'])} task-skill pairs")
        return
    if args.command == "summarize":
        from analysis import summarize
        print(json.dumps(summarize(args.runs, args.out), indent=2))
        return
    if args.command == "judge":
        from harnesses.tessl import judge
        task = data_index.resolve(config, {"benchmark": "tessl", "task": args.task})
        print(judge(config, task, args.trial.resolve()))
        return
    if getattr(args, "arms", None) and len(set(args.arms)) != len(args.arms):
        raise ValueError("Each rewrite arm may be specified only once")
    selected = data_index.pairs(config, args.suite, args.benchmark, args.task)
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("limit must be positive")
        selected = selected[:args.limit]
    if args.command == "list":
        for pair in selected:
            print(f"{pair['benchmark']}/{pair['task']}")
        return
    if args.command == "data-check":
        print(json.dumps(data_index.check(config, selected), indent=2))
        return
    profiles = list(getattr(args, "models", None) or ([] if args.command == "rewrite" else [args.executor]))
    if args.command in ("rewrite", "adapt"):
        profiles.append(args.rewriter)
    if args.command != "rewrite" and any(p["benchmark"] == "tessl" for p in selected):
        profiles.append(config["judge"])
    for profile in profiles:
        credential(model_spec(config, profile))
    if args.out.exists():
        raise ValueError("Choose a new output directory; existing runs are never overwritten")
    data_index.check(config, selected)
    args.out.mkdir(parents=True)
    write_json(args.out / "selection.json", {"pairs": selected})
    # Configuration stores environment-variable names, never key values.
    write_json(args.out / "config.json", config)
    if args.command == "evaluate":
        from harnesses.runner import run_trial
        if args.repeats < 1:
            raise ValueError("repeats must be positive")
        fields = ["benchmark", "task", "executor", "condition", "repeat", "reward", "status"]
        with (args.out / "scores.csv").open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            for pair in selected:
                for model in (args.models or [args.executor]):
                    for repeat in range(args.repeats):
                        conditions = args.conditions if repeat % 2 == 0 else list(reversed(args.conditions))
                        for condition in conditions:
                            dest = args.out / pair["benchmark"] / pair["task"] / model / condition / str(repeat)
                            print(f"{pair['benchmark']}/{pair['task']} {model} {condition} repeat={repeat}", flush=True)
                            result = run_trial(config, pair, model, dest, no_skill=condition == "no_skill")
                            writer.writerow({k: repeat if k == "repeat" else result[k] for k in fields})
                            stream.flush()
        return
    for pair in selected:
        dest = args.out / pair["benchmark"] / pair["task"]
        print(f"{args.command}: {pair['benchmark']}/{pair['task']}", flush=True)
        if args.command == "rewrite":
            from evolution.rewrite import rewrite
            task = data_index.resolve(config, pair)
            original = data_index.skills(task, pair["benchmark"])
            for arm in args.arms:
                target = dest / arm / "skills"
                target.parent.mkdir(parents=True)
                rewrite(config, task, pair["benchmark"], args.rewriter, arm, original, target)
        else:
            from evolution.pipeline import run
            run(config, pair, args.executor, dest, args.command, args.arms,
                rounds=getattr(args, "rounds", 1), rewriter=getattr(args, "rewriter", None),
                evidence_enabled=not getattr(args, "no_evidence", False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # No traceback that might include an HTTP request with credentials.
        config_path = parser().parse_args().config
        try:
            cfg = load_config(config_path) if config_path.exists() else {}
        except Exception:
            cfg = {}
        print("Error: " + redact(str(exc), cfg), file=sys.stderr)
        sys.exit(1)
