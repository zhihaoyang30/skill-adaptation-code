# Failure capsule — the evidence shown to the rewriter

In self-evolution, the rewriter sees evidence from the executor's previous
attempt. The evidence is extracted deterministically from the run (no model in
the loop) and packaged in this format:

```
## Failure capsule (deterministically extracted)

OUTCOME: <failed | passed | partial>
REWARD: <continuous reward in [0,1], or unknown>

FAILED CHECKS TO REPAIR:
- <verifier check name>: <message excerpt>

PASSED CHECKS TO PRESERVE:
- <verifier check name>

NON-FAILURE CHECK STATUSES:
- <skipped / pending checks>

TOOL CALLS: <n> total; <k> failed
FIRST FAILED TOOL CALL:
- <tool name + arguments excerpt>
LAST RECORDED WRITE-LIKE ACTION:
- <tool name + arguments excerpt>

Use the raw evidence below to ground a patch. Do not copy hidden
expected values into the skill.
```

Below the capsule, the user message includes:

1. **The task instruction** (verbatim, capped).
2. **The current skill files** (verbatim).
3. **A trajectory digest** — tool calls and messages in order, with the
   injected skill text removed, middle truncated when over ~9k characters
   (keep both ends, drop the middle).
4. **The verifier output** for the failed attempt.
5. **The output contract** (`output_contract.md`).

The rewriting prompt (meta-skill / no-meta / one-sentence) is the *system*
message; everything above is the *user* message. See
`evolution/evidence.py` for the reference implementation.
