"""Trial dispatch and a single result contract for every benchmark."""
from pathlib import Path

from core import model_spec, reward, tree_hash, write_json
from data_index import resolve, skills


def run_trial(config, pair, executor, out, skill_bundle=None, no_skill=False):
    out = Path(out).resolve()
    if out.exists():
        raise ValueError(f"Refusing to overwrite trial: {out}")
    task = resolve(config, pair)
    bundle = None if no_skill else Path(skill_bundle or skills(task, pair["benchmark"])).resolve()
    out.mkdir(parents=True)
    result = {"benchmark": pair["benchmark"], "task": pair["task"], "executor": executor,
              "model": model_spec(config, executor)["model"],
              "condition": "no_skill" if no_skill else "with_skill",
              "skill_sha256": tree_hash(bundle) if bundle else None,
              "status": "running", "reward": None}
    write_json(out / "result.json", result)
    try:
        if pair["benchmark"] == "tessl":
            from harnesses.tessl import run
        else:
            from harnesses.harbor import run
        result.update(run(config, pair, task, bundle, executor, out))
        if result["reward"] is not None:
            result["reward"] = reward(result["reward"])
    except Exception as exc:
        result.update(status="infrastructure_error", reward=None, error_type=type(exc).__name__)
        write_json(out / "result.json", result)
        raise
    write_json(out / "result.json", result)
    if result["reward"] is None:
        raise RuntimeError(f"Unscored trial: {pair['task']} ({result['status']})")
    return result
