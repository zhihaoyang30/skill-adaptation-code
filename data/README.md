# Upstream task indexes

These files are references to existing benchmark releases, not a new dataset.
Task content, skills, inputs, and grading materials must be read from the upstream
sources pinned in `sources.json`. `fetch` downloads those releases and resolves
missing DocOps task skill folders from the same release's shared skills.

| Benchmark | `screening.json` | `selected.json` |
|---|---:|---:|
| SkillsBench | 87 | 32 |
| DocOps | 186 | 32 |
| Tessl | 334 | 39 |
| Total | 607 | 103 |

`selected.json` is a subset of `screening.json`. Task identities and skill
references match across both indexes. The packager checks the counts, unique
identities, and subset relationship.

Use `--suite screening` to evaluate the 607 tasks and `--suite selected` to run
adaptation or self-evolution on the 103 pairs. To select pairs using your own
models, evaluate the larger index and pass the resulting scores to `screen`.
Its output can be supplied as `--suite runs/selected.json`.

Each pair has `benchmark`, `task`, `path`, `skills`, and `skill_paths` fields.
Paths are relative to the corresponding upstream repository/archive root. A task
with several skills is one observation carrying the full bundle. The SkillsBench
`taxonomy-tree-merge` task is under `tasks-extra/` in the pinned release.

No source data or original experiment scores are bundled. Upstream licenses apply
independently to the downloaded benchmarks and their constituent skills.
