# Output contract for skill rewrites

Appended to the user message of every rewrite call (meta-skill, no-meta
baseline, and one-sentence arms alike), so that all arms share the same
mechanics and differ only in guidance.

---

## Full-rewrite output contract

Return the complete rewritten file for every file you change:

```text
<<<FILE path=some-skill/SKILL.md>>>
...the entire new contents of the file...
<<<END>>>
```

Return one block per changed file, and return the file *whole* — what you send
replaces the current contents. Leave a file out to keep it unchanged. `path` must
name a file that already exists in the skill, exactly as given.

You may restructure freely: reorder sections, merge, split, delete what the agent
cannot act on. Two things are fixed:

- The frontmatter must survive with the same `name`.
- Do not paste expected outputs, expected numbers, or a solution. A skill that
  works only because it contains the answer is rejected.

If the supplied instruction, trajectory, verifier output, skill, and tool schema
do not support a grounded rewrite, preserve the incumbent:

```text
<<<NO_CHANGE>>>
{"reason":"why a grounded rewrite cannot be made","missing_evidence":["what is missing"]}
<<<END_NO_CHANGE>>>
```
