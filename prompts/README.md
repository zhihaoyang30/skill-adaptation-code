# Prompts

Reusable system prompts and the shared rewrite contract:

| file | role |
|---|---|
| `meta_skill.md` | **The meta-skill S.** Four rubric-derived failure classes (EXE / CTX / IF / REF) ordered by execution depth, an earliest-breakpoint rule, and one local prescription per class. Used as the *system* message of every meta-arm rewrite. |
| `no_meta_baseline.md` | The contract-only baseline S is measured against: identical role framing and hard rules, zero rewrite guidance. |
| `one_sentence_rewrite.md` | The one-sentence instruction arm ("This skill document is not friendly to a weak model. Rewrite it."). |
| `output_contract.md` | The FILE / NO_CHANGE output contract appended to every arm's user message. |
| `failure_capsule.md` | The deterministic evidence format the rewriter sees in self-evolution. |

All three guidance prompts share the same hard rules (same `name:` in the
frontmatter, no pasted answers, NO_CHANGE escape hatch) so the arms differ in
guidance only.
