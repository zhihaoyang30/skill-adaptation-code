#!/usr/bin/env python3
"""Integrity gate for rewritten skills.

Every rewrite — meta-skill, baseline, or one-sentence arm alike — passes this
gate before it is installed, so no curve can be raised by putting an answer
into a skill. A rejected rewrite keeps the incumbent skill.

Checks, in order:
  1. non-empty;
  2. SKILL.md keeps its YAML frontmatter and the same `name:`;
  3. total length under the context budget (a runaway skill crowds the task
     out of the executor's prompt);
  4. anti-leak: tokens that appear in the hidden tests / reference solution
     but in neither the public task material nor the evidence the rewriter was
     shown have no honest route into the skill. One unseen expected *value*
     rejects; a single unseen *identifier* can be a naming coincidence, so only
     two or more reject.
"""
import re

SKILL_CHAR_BUDGET = 64_000

WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_.\-]{4,}|\d+\.\d{2,}")
STRONG = re.compile(r"^(?=.*[_0-9])[A-Za-z_][A-Za-z0-9_.\-]{7,}$")   # specific ids
NUMERIC = re.compile(r"^\d+\.\d{2,}$")                               # expected values
COMMON = {
    "read_csv", "to_csv", "read_excel", "to_excel", "read_json", "to_json",
    "np.array", "os.path", "sys.argv", "json.dumps", "json.loads", "__main__",
    "__name__", "utf-8", "isinstance", "startswith", "endswith", "splitlines",
    "strip", "sort_values", "set_index", "reset_index", "iterrows", "to_dict",
    "matplotlib.pyplot", "subprocess.run", "pathlib.Path", "datetime.datetime",
    "test_outputs.py", "requirements.txt", "python3", "float64", "int64",
}


def secrets_from_tests(test_text: str, public_text: str):
    """(expected values, specific identifiers) present in the tests but not in
    any public task material."""
    nums, ids = set(), set()
    for tok in WORD.findall(test_text):
        if tok in COMMON or tok in public_text:
            continue
        if NUMERIC.match(tok):
            nums.add(tok)
        elif STRONG.match(tok):
            ids.add(tok)
    return nums, ids


def gate(orig: str, new: str, path: str, secrets, evidence: str):
    """Accept or reject one rewritten file.

    Returns (ok, reason, seen, unseen). Tokens the rewriter *was shown* (they
    occur in `evidence`) are the design, not a breach — reported in `seen`,
    never blocked.
    """
    if not new.strip():
        return False, "empty", [], []
    if path.endswith("SKILL.md"):
        m = re.match(r"---\n(.*?)\n---\n", new, re.S)
        if not m:
            return False, "frontmatter gone", [], []
        want = re.search(r"^name:\s*(.+?)\s*$", orig, re.M)
        got = re.search(r"^name:\s*(.+?)\s*$", m.group(1), re.M)
        if not got:
            return False, "no name in frontmatter", [], []
        if want and got.group(1).strip().strip("\"'") != want.group(1).strip().strip("\"'"):
            return False, f"name changed {want.group(1)!r} -> {got.group(1)!r}", [], []
    # No floor: compressing a skill is a behaviour under study. The ceiling is
    # absolute because the skill is injected whole into the executor's prompt.
    if len(new) > SKILL_CHAR_BUDGET:
        return False, f"length {len(new)} over the {SKILL_CHAR_BUDGET} budget", [], []
    nums, ids = secrets
    added = [t for t in (nums | ids) if t in new and t not in orig]
    seen = sorted(t for t in added if t in evidence)
    blind = [t for t in added if t not in evidence]
    hit_n = sorted(t for t in blind if t in nums)
    hit_i = sorted(t for t in blind if t in ids)
    if hit_n:
        return False, "unseen expected values: " + ", ".join(hit_n[:6]), seen, hit_i
    if len(hit_i) >= 2:
        return False, "unseen test identifiers: " + ", ".join(hit_i[:6]), seen, hit_i
    return True, "", seen, hit_i
