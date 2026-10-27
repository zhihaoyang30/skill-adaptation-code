"""One-shot adaptation and linear self-evolution with interleaved controls."""
import shutil
from pathlib import Path

from core import write_json
from data_index import resolve, skills
from evolution.rewrite import rewrite
from harnesses.runner import run_trial


def run(config, pair, executor, out, mode, arms, rounds=5, rewriter=None, evidence_enabled=True):
    out = Path(out).resolve()
    if out.exists():
        raise ValueError(f"Output already exists: {out}")
    if rounds < 1:
        raise ValueError("rounds must be positive")
    task = resolve(config, pair)
    original = skills(task, pair["benchmark"])
    out.mkdir(parents=True)
    history = []

    def execute(arm, number, bundle, no_skill=False):
        path = out / arm / f"r{number}" / "trial"
        result = run_trial(config, pair, executor, path, bundle, no_skill)
        row = {**result, "arm": arm, "round": number, "mode": mode, "trial": path.relative_to(out).as_posix()}
        history.append(row)
        write_json(out / "history.json", history)
        return path, result["reward"]

    if mode == "adapt":
        if not rewriter:
            raise ValueError("One-shot adaptation needs a rewriter profile")
        # Rewrite first, without running the executor or exposing baseline results.
        for arm in arms:
            bundle = out / arm / "r1/skills"
            bundle.parent.mkdir(parents=True)
            rewrite(config, task, pair["benchmark"], rewriter, arm, original, bundle)
        execute("original", 1, original)
        for arm in arms:
            execute(arm, 1, out / arm / "r1/skills")
    else:
        # Same executor and rewriter profile for self-evolution; each arm starts fresh.
        previous = {}
        bundles = {}
        execute("original", 0, original)
        for arm in arms:
            bundle = out / arm / "r0/skills"
            bundle.parent.mkdir(parents=True)
            shutil.copytree(original, bundle)
            bundles[arm] = bundle
            previous[arm] = execute(arm, 0, bundle)
        for number in range(1, rounds + 1):
            execute("original", number, original)
            # Alternate arm order to reduce order effects from serving drift.
            order = arms if number % 2 else list(reversed(arms))
            for arm in order:
                bundle = out / arm / f"r{number}" / "skills"
                bundle.parent.mkdir(parents=True)
                rewrite(config, task, pair["benchmark"], executor, arm, bundles[arm], bundle,
                        previous[arm] if evidence_enabled else None)
                bundles[arm] = bundle
                previous[arm] = execute(arm, number, bundle)
    return history
