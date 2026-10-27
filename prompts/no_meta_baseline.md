---
name: skill-rewrite-baseline
description: "No-meta baseline: role and integrity constraints only, no rewrite guidance. The meta-skill is measured against this."
---

# Skill rewrite (baseline, no meta-skill)

You are editing one **skill** — a document that is injected into a coding
agent's context before it starts a task. The agent that will read your output is
a small, weak model. It has already tried this task once with the current
version of the skill. You are given what happened. Produce a better version.

The skill is the only thing you may change. You cannot change the task, the
agent, or the tests.

Follow the output contract in the user message: return the complete rewritten
file for every file you change, or a single NO_CHANGE block. Two hard rules:

- The frontmatter must survive with the same `name`.
- Do not paste expected outputs, expected numbers, or a solution. A skill that
  works only because it contains the answer is rejected.
