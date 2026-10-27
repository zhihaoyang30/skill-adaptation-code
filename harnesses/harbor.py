"""Run native SkillsBench/DocOps Docker tasks and their original verifiers."""
import asyncio
import contextlib
import os
import shutil

from core import credential, model_spec, reward
from harnesses.bridge import claude_endpoint


@contextlib.contextmanager
def temporary_env(values):
    old = {k: os.environ.get(k) for k in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


async def native_trial(task, bundle, model, out, benchmark, runtime):
    from harbor.models.trial.config import AgentConfig, TaskConfig, TrialConfig
    from harbor.trial.trial import Trial

    is_sb = benchmark == "skillsbench"
    klass = "InjectedOpenHands" if is_sb else "InjectedClaudeCode"
    kwargs = {"bundle": str(bundle) if bundle else None,
              "version": runtime.get("openhands_version", "1.28.1") if is_sb else runtime.get("claude_version", "2.1.114")}
    if is_sb:
        kwargs.update(max_iterations=runtime.get("max_iterations", 100), reasoning_effort=None)
    config = TrialConfig(task=TaskConfig(path=task), trial_name="trial", trials_dir=out / "native",
                         agent=AgentConfig(import_path=f"harnesses.agents:{klass}", model_name=model,
                                           override_timeout_sec=runtime.get("agent_timeout", 1800), kwargs=kwargs))
    trial = await Trial.create(config)
    return (await trial.run()).model_dump(mode="json")


def run(config, pair, task, bundle, executor, out):
    spec = model_spec(config, executor)
    runtime = config.get("runtime", {})
    benchmark = pair["benchmark"]
    if benchmark == "skillsbench":
        provider = "anthropic" if spec.get("api_format") == "anthropic" else "openai"
        default_base = "https://api.anthropic.com" if provider == "anthropic" else "https://api.openai.com/v1"
        with temporary_env({"LLM_API_KEY": credential(spec), "LLM_BASE_URL": spec.get("base_url", default_base)}):
            data = asyncio.run(native_trial(task, bundle, provider + "/" + spec["model"], out, benchmark, runtime))
    else:
        with claude_endpoint(spec, runtime) as (base, key, model):
            with temporary_env({"ANTHROPIC_BASE_URL": base, "ANTHROPIC_API_KEY": key,
                                "ANTHROPIC_AUTH_TOKEN": key, "CLAUDE_CODE_OAUTH_TOKEN": ""}):
                data = asyncio.run(native_trial(task, bundle, model, out, benchmark, runtime))
    native = out / "native/trial"
    for name in ("trajectory.json", "claude-code.txt"):
        p = native / "agent" / name
        if p.exists():
            shutil.copyfile(p, out / ("trajectory.json" if name.endswith(".json") else "transcript.jsonl"))
    if (native / "verifier").exists():
        shutil.copytree(native / "verifier", out / "verifier")
    error = data.get("exception_info")
    score = ((data.get("verifier_result") or {}).get("rewards") or {}).get("reward")
    if score is not None:
        score = reward(score)
    if error and error.get("exception_type") not in ("AgentTimeoutError",):
        return {"status": "infrastructure_error", "reward": None, "error_type": error.get("exception_type")}
    return {"status": "scored" if score is not None else "unscored", "reward": score,
            "harness": "OpenHands SDK" if benchmark == "skillsbench" else "Claude Code", "agent_timeout": bool(error)}
