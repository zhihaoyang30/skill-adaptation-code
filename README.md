<div align="center">

# Evolving to Match Capabilities

<h3 align="center">Improving Harness Self-Evolution via Skill Adaptation</h3>

<p align="center" style="line-height:1.5;margin:0.4em 0 0.3em;">
<span style="white-space:nowrap;"><b><a href="https://zhihaoyang30.github.io/">Zhihao Yang</a></b><sup>1,7,*</sup></span>,
<span style="white-space:nowrap;"><b><a href="https://haojinw0027.github.io/">Haojin Wang</a></b><sup>2,*</sup></span>,
<span style="white-space:nowrap;"><b><a href="https://chtholly17.github.io/">Juncheng Wu</a></b><sup>3,*</sup></span>,
<span style="white-space:nowrap;"><a href="https://itheresaapocalypse.github.io/">Kuan Zhang</a><sup>4</sup></span>,
<span style="white-space:nowrap;"><a href="https://scholar.google.com/citations?user=JWxSJVgAAAAJ&hl=zh-CN">Yukun Chen</a><sup>1</sup></span>,
<span style="white-space:nowrap;"><a href="https://rainbowluocs.github.io/">Run Luo</a><sup>5</sup></span>,
<span style="white-space:nowrap;"><a href="https://yaojie.lu/">Yaojie Lu</a><sup>6</sup></span>,
<span style="white-space:nowrap;"><a href="https://yuyinzhou.github.io/">Yuyin Zhou</a><sup>3</sup></span>,
<span style="white-space:nowrap;"><b><a href="https://openreview.net/profile?id=~Lu_Wang26">Lu Wang</a></b><sup>4,†</sup></span>,
<span style="white-space:nowrap;"><b><a href="https://scholar.google.com/citations?user=pA88bm4AAAAJ&hl=en">Xianpei Han</a></b><sup>6,†</sup></span>
</p>

<p align="center" style="font-size:0.85em;line-height:1.5;margin:0 0 0.6em;">
<span style="white-space:nowrap;"><sup>1</sup>University of Chinese Academy of Sciences</span> &nbsp;
<span style="white-space:nowrap;"><sup>2</sup>Independent Researcher</span> &nbsp;
<span style="white-space:nowrap;"><sup>3</sup>University of California, Santa Cruz</span> &nbsp;
<span style="white-space:nowrap;"><sup>4</sup>Tsinghua University</span> &nbsp;
<span style="white-space:nowrap;"><sup>5</sup>National University of Singapore</span> &nbsp;
<span style="white-space:nowrap;"><sup>6</sup>Chinese Information Processing Laboratory, Institute of Software, Chinese Academy of Sciences</span> &nbsp;
<span style="white-space:nowrap;"><sup>7</sup>School of Advanced Interdisciplinary Sciences, University of Chinese Academy of Sciences</span><br>
<span style="white-space:nowrap;"><sup>*</sup>Equal contribution</span> &nbsp;
<span style="white-space:nowrap;"><sup>†</sup>Corresponding authors</span>
</p>

<p align="center">
  <a href="https://arxiv.org/abs/2610.33024"><img src="https://img.shields.io/badge/arXiv-b31b1b?style=for-the-badge&logo=arxiv&logoColor=white" alt="arXiv"></a>
  <a href="https://zhihaoyang30.github.io/skill-adaptation/"><img src="https://img.shields.io/badge/Project%20Page-1f6feb?style=for-the-badge&logo=googlechrome&logoColor=white" alt="Project Page"></a>
  <a href="https://zhihaoyang30.github.io/skill-adaptation/paper.pdf"><img src="https://img.shields.io/badge/Paper-PDF-B4503A?style=for-the-badge&logo=adobeacrobatreader&logoColor=white" alt="Paper"></a>
  <a href="https://github.com/zhihaoyang30/skill-adaptation-code"><img src="https://img.shields.io/badge/Code-GitHub-181717?style=for-the-badge&logo=github&logoColor=white" alt="Code"></a>
</p>

</div>

<p align="center">
  <img src="assets/fig3_pipeline.png" alt="Meta-skill construction and harness self-evolution" width="100%">
</p>

## Overview

The same agent skill can lift a strong model and sink a weaker one. This paper diagnoses why, distills the diagnosis into a fixed **meta-skill** that rewrites skills to match the executor, and shows that this improves both one-shot **skill adaptation** and five-round **harness self-evolution** across seven executors.

This repository holds the reproduction code. Interactive figures and the paper PDF are on the [project page](https://zhihaoyang30.github.io/skill-adaptation/). Run existing benchmark tasks with different API models, measure the effect of human-written skills, adapt those skills, and compare self-evolution with and without the meta-skill.

Evaluated on **103 skill-sensitive task–skill pairs**, screened from 607 pairs across SkillsBench, DocOps, and Tessl:

| Setting | Result |
|---|---|
| **One-shot skill adaptation** (Kimi-K3 rewrites, no execution evidence) | **+5.1 ~ +14.1** points over the original skills, for all three weak executors |
| **Five-round self-evolution** (each model rewrites its own skill) | **+2.0 ~ +5.1** points over the same loop without the meta-skill, across **all seven executors** |

In **86% of failed weak-model runs**, the violated requirement is already stated in the skill. Skills that improve GPT-5.6-luna by **+31.1** points reduce Gemma-4-E4B by **−8.8** points.

## Data

This work does **not** introduce a new dataset. Tasks, inputs, skills, and verifiers come from their original releases:

| Benchmark | Source | Executor | Score |
|---|---|---|---|
| SkillsBench | [benchflow-ai/skillsbench](https://github.com/benchflow-ai/skillsbench) | OpenHands SDK | Native deterministic verifier reward |
| DocOps | [icip-cas/DocOps](https://github.com/icip-cas/DocOps) | Claude Code | Native document-state verifier reward |
| Tessl | [tesslio/task-evals-for-skills](https://huggingface.co/datasets/tesslio/task-evals-for-skills) | Claude Code | Normalized task-completion rubric score |

`data/sources.json` pins public revisions and the Tessl archive checksum. `data/screening.json` indexes **607 tasks** (87 SkillsBench, 186 DocOps, 334 Tessl); `data/selected.json` provides a **103-pair subset** (32, 32, 39) for adaptation and self-evolution. Every selected pair is included in the larger index with the same task and skill references. Each row contains only a benchmark, an upstream task ID/path, and skill identifiers/source paths. A multi-skill bundle is one pair. See [data/README.md](data/README.md) for the index format.

`--suite selected` uses the 103 pairs; `--suite screening` uses the 607 tasks. `--suite upstream` enumerates the larger fetched releases. To screen a different cohort, supply your own index in the same format. A new `screen` result is always derived from the scores you supply.

## Install

Use Python 3.12+, Git, Docker Engine, and Docker Compose v2. Run commands from this repository's root. Linux is the default execution environment.

```bash
git clone https://github.com/zhihaoyang30/skill-adaptation-code.git
cd skill-adaptation-code
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp configs/example.json configs/local.json
```

Edit `configs/local.json` with your endpoint URLs and exact served model names. `executor` solves tasks, `rewriter` performs one-shot adaptation, and `judge` scores Tessl. Self-evolution uses the **executor's own model profile** for rewriting.

Set credentials in the shell; the program reads only the environment-variable names declared in the config:

```bash
export EXECUTOR_API_KEY='your-executor-api-key'
export REWRITER_API_KEY='your-rewriter-api-key'
export JUDGE_API_KEY='your-judge-api-key'
python run.py doctor
```

You can use one key for several profiles by pointing their `api_key_env` fields at the same environment variable. Only credentials for the requested operation are required. The doctor reports missing credentials without printing their values; it does not call the model APIs.

For an OpenAI-compatible endpoint, use `"api_format": "openai"` and a base URL ending in `/v1`. For native Anthropic Messages, use `"api_format": "anthropic"` and a base URL such as `https://api.anthropic.com`. Models must support the tool calls required by their executor. Provider-specific generation options go in `parameters` for rewriting and judging; for example, replace `max_tokens` with `max_completion_tokens` if your provider requires it. No fixed model allowlist is used.

Claude Code expects Anthropic Messages. For an OpenAI-compatible executor, the runner starts a temporary authenticated LiteLLM bridge automatically. On Linux it discovers the Docker bridge gateway. On Docker Desktop, set `runtime.bridge_host` to `host.docker.internal`. On a remote Docker engine, set it to a reachable address of the machine running this command. API protocol compatibility does not imply identical model behavior across providers.

## Fetch upstream tasks

```bash
python run.py fetch
python run.py data-check
python run.py list --benchmark skillsbench --limit 5
```

Downloads live under `data/upstream/`, controlled by `data_root`. `fetch` refuses to overwrite an existing checkout. Missing DocOps task skill folders are materialized from that release's shared `skills/` directory. The index records the original skill paths. The DocOps repository also contains its required Docker image archives; allow enough disk space for that upstream download.

DocOps tasks need the base images supplied by DocOps:

```bash
bash data/upstream/docops/docker/load_images.sh x86
```

Build the Tessl executor image once:

```bash
docker build -f docker/claude.Dockerfile -t skill-adaptation-claude:2.1.114 .
```

SkillsBench and DocOps run their existing task Dockerfiles and verifiers through pinned Harbor adapters. Tessl runs each task in a fresh Claude Code container. The complete skill bundle is available under `/skills`; all `SKILL.md` bodies are injected into the task prompt. Skill-off trials remove the bundle from the container. This keeps skill delivery fixed instead of evaluating skill retrieval.

## Start with one task

Choose a task ID from `list`. The following examples use a real indexed SkillsBench task:

```bash
python run.py evaluate --benchmark skillsbench --task weighted-gdp-calc \
  --out runs/baseline

python run.py adapt --benchmark skillsbench --task weighted-gdp-calc \
  --executor executor --rewriter rewriter --arms meta one_sentence \
  --out runs/adaptation

python run.py evolve --benchmark skillsbench --task weighted-gdp-calc \
  --executor executor --arms meta no_meta --rounds 5 \
  --out runs/evolution

python run.py summarize --runs runs/evolution --out runs/evolution-summary
```

Remove `--task` to run all indexed pairs in a benchmark, or remove both filters to run all 103. `--limit 1` is useful for a first infrastructure check. Choose a new output directory for each invocation; existing runs are never silently replaced. Commands make real API calls and run upstream task environments.

## Reproduce the workflow

1. **Measure skill gain.** `evaluate` runs `no_skill` and `with_skill` on the same tasks. Use `--models PROFILE_A PROFILE_B ...` for multiple API profiles and `--repeats N` for paired repeated measurements. Its `scores.csv` feeds screening directly.
2. **Select sensitive pairs.** Assign model profiles to capability tiers, then apply the paper's gain and tier-gap threshold, `tau = 0.10`, frontier saturation at `0.95`, and weak-tier ceiling at `0.80`.
3. **Inspect failures.** Each trial saves its trajectory and native verifier evidence. `evolution/evidence.py` builds a deterministic failure capsule for rewriting. The four failure classes and prescriptions are in `prompts/meta_skill.md`; the paper's diagnosis step is qualitative and is not represented as an automatic ground-truth classifier.
4. **Adapt once.** `adapt` rewrites the original bundle before any rollout and exposes no trajectory or verifier evidence. A chosen external rewriter can be compared under `meta`, `no_meta`, and `one_sentence` guidance. Each command also evaluates the original bundle.
5. **Self-evolve.** `evolve` evaluates round 0, then rewrites from the preceding round's evidence and evaluates rounds 1–5. The executor rewrites its own bundle. An original-skill control is rerun at every round, and arms are interleaved within each task.
6. **Compare outcomes.** `summarize` emits per-benchmark, per-model, per-arm curves and task-paired gains against the same-round original control. It reports paired sample counts and does not merge the three benchmarks into a task-count-weighted average.

For a seven-model screening configuration, copy `configs/screening.example.json`, fill in the model profiles and keys, then run:

```bash
python run.py --config configs/screening.local.json evaluate \
  --suite screening \
  --models frontier_a frontier_b moderate_a moderate_b weak_a weak_b weak_c \
  --out runs/screening
python run.py --config configs/screening.local.json screen \
  --scores runs/screening/scores.csv --out runs/selected.json
python run.py evolve --suite runs/selected.json --rounds 5 --out runs/selected-evolution
```

The selector requires both conditions for every configured model and the same repeat IDs per pair. It averages repeats within each model before averaging models within a tier. Infrastructure failures remain unscored and halt the command; they are never silently converted to zero or dropped from screening. Newly selected IDs need not match the paper under new models or endpoints.

## Ablations and reusable rewriting

| Comparison | Command options |
|---|---|
| No skill vs. original human skill | `evaluate --conditions no_skill with_skill` |
| Meta guidance vs. contract-only guidance | `evolve --arms meta no_meta` |
| Meta guidance vs. one-sentence rewriting | `adapt --arms meta one_sentence` |
| External rewriter choice | Run `adapt --rewriter PROFILE` separately for each profile |
| Execution-evidence ablation | `evolve --no-evidence` |
| Number of evolution rounds | `evolve --rounds N` |
| Repeated baseline measurement | `evaluate --repeats N` |

To produce rewritten skills without executing the task:

```bash
python run.py rewrite --benchmark skillsbench --task weighted-gdp-calc \
  --rewriter rewriter --arms meta --out runs/rewritten-skills
```

Every arm shares the output contract and validity gate. The gate checks existing paths, valid frontmatter, unchanged skill names, a 64,000-character per-file ceiling, and hidden-token leakage. It is a heuristic token check, not a proof that a rewrite cannot encode an answer. Hidden tests/reference solutions are used only locally by the gate and are never put in the rewriter prompt. Verifier feedback from the last rollout is visible in evidence-enabled evolution.

A format error receives one format-repair request. An invalid revision or `NO_CHANGE` keeps the preceding bundle and is still evaluated. A rejected multi-file response changes no files. Evolution is a linear chain, with no keep-best selection or rollback based on reward.

Tessl judging can be repeated without rerunning the executor:

```bash
python run.py judge --task TASK_ID --trial runs/YOUR_RUN/tessl/TASK_ID/PROFILE/with_skill/0
```

Only the task-completion rubric determines reward. Duplicate, unknown, missing, non-finite, or out-of-range judge scores are rejected. Judging overwrites that trial's local judgment; keep a copy if comparing judges.

## Layout

```text
run.py                                    unified command-line interface
core.py                                   config, paths, hashes, and result utilities
models.py                                 OpenAI/Anthropic rewriting and judging clients
data_index.py                             pinned source download and task resolution
analysis.py                               per-benchmark summaries and paired gains
configs/                                  model and screening templates
data/                                     upstream sources, 607-task index, and 103-pair subset
harnesses/                                OpenHands/Claude Code runners and API bridge
evolution/                                evidence, rewrite gate, adaptation/evolution loop
screening/                                tier-based pair selection
prompts/                                  meta, contract-only, and one-sentence prompts
interfaces/                               executor tool descriptions supplied to the rewriter
docker/                                   reproducible Tessl executor image
tests/                                    protocol, scoring, isolation, and CLI tests
tools/package.py                          allowlisted, privacy-checked source ZIP
```

OpenHands uses the SDK adapter and the tool set listed in `interfaces/openhands.json`. Model revisions, provider settings, and upstream environments can affect numerical results. Generated outputs remain local under the chosen run directory.

## Validate and package

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python tools/package.py --out dist/skill-adaptation-code.zip
```

The source-only tests do not call paid model APIs. The packager uses an explicit file allowlist and rejects common credential/private-path patterns. It never includes local config files, `.env`, upstream data, or run output.

## Citation

```bibtex
@misc{yang2026evolvingmatchcapabilitiesimproving,
      title={Evolving to Match Capabilities: Improving Harness Self-Evolution via Skill Adaptation},
      author={Zhihao Yang and Haojin Wang and Juncheng Wu and Kuan Zhang and Yukun Chen and Run Luo and Yaojie Lu and Yuyin Zhou and Lu Wang and Xianpei Han},
      year={2026},
      eprint={2610.33024},
      archivePrefix={arXiv},
      primaryClass={cs.LG},
      url={https://arxiv.org/abs/2610.33024},
}
```

## License

This code is MIT licensed; see [LICENSE](LICENSE). Downloaded benchmarks, skills, and runner dependencies retain their upstream licenses.
