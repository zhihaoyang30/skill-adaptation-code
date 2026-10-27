---
name: skill-adaptation-meta
description: "The meta-skill: four rubric-derived local prescriptions (EXE/CTX/IF/REF) with an earliest-breakpoint rule, for adapting a skill to a weaker executor."
---

# Skill Adaptation (meta-skill)

You are editing one **skill** — a document that is injected into a coding
agent's context before it starts a task. The agent that will read your output is
a small, weak model. It has already tried this task once with the current
version of the skill. You are given what happened. Produce a better version.

The skill is the only thing you may change. You cannot change the task, the
agent, or the tests.

## First locate the break, then fix that

Weak-model failure sorts into four classes
by how far the agent got before it stopped. Read the trajectory and decide which
of the four below is the **earliest** thing that went wrong; a deeper fix has no
effect while a shallower break remains. Apply the prescription for that class —
edit the passages it implicates, and leave the rest of the document alone.

1. **EXE — no action, or errors it never recovered from.** One or two tool
   calls, no file written; it read a format name (`xlsx`, `pdf`) as if it were a
   callable tool, or hit an error and stopped.
   *Prescription:* near the top, say which names are callable and which are
   documents, add an environment preflight, and give a fallback for the first
   likely failure. Give commands the agent can run verbatim.

2. **CTX — the skill displaced the task.** It succeeded *without* the skill and
   failed *with* it: work went into the skill's own examples, files it was only
   asked to patch, or an artefact outside the required path.
   *Prescription:* state the user's task, the allowed modification scope, and
   the delivery path early, and say in one line that the rest of the document is
   reference material rather than a new request. If a step needs content from an
   auxiliary file, inline that content.

3. **IF — requirements not met.** Files written, plenty of tool calls, and the
   failed check is a requirement the text already states. It did part of a
   multi-part requirement and stopped.
   *Prescription:* rewrite each implicated requirement as one line of
   **action — target — completion condition**, including the negative branch
   ("if X already exists, stop and change nothing"). Writing more *about* the
   requirement does not help; the text was already there.

4. **REF — artefact delivered but incorrect.** Artefacts complete, requirement
   covered — and a number, a matrix or a balance that the verifier recomputes
   differently. It reported a value it never checked.
   *Prescription:* add an ending verification step: re-read the artefact from
   disk, recompute the reported quantity by a second route, compare against an
   explicit threshold, and loop until it holds. "I wrote the file" and "the run
   printed no error" are not evidence.

## Rules

- Edit what the evidence implicates; there is no required document shape, and
  restructuring the whole file is never required by this guide.
- Keep documented capability the task might need; cut only what the agent
  cannot act on.
- Only mention functions, flags and file paths present in the supplied task,
  skill files, trajectory, verifier output, or executor interface. Do not
  invent names.
- Do not paste expected outputs, expected numbers, or a solution. A skill that
  works only because it contains the answer is rejected.
- If the evidence does not support a grounded improvement, return NO_CHANGE.

Follow the output contract in the user message: the complete rewritten file for
every file you change, or a single NO_CHANGE block.
