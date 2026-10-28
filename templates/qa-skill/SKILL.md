---
name: {{name}}
description: "{{description}}"
metadata:
  category: {{category}}
  version: "0.1.0"
  media: {{media}}
  projects: []
---

# {{title}}

A standalone quality gate. Point it at the files to check, pick a profile, and it returns a pass/fail
verdict with evidence. It checks and reports; it doesn't fix, regenerate or post anything unless the user
asks for that as a separate step.

QC has two halves, and an item passes only when both pass:
1. **Automatic checks**: `scripts/check.py` measures what can be measured.
2. **Review**: you look at what a script can't judge, using the checklist in `references/checklist.md`.

## 1. Get the files

Use attached files where they are; stage files from the user's computer into the workspace first.

## 2. Pick a profile

Profiles in `profiles/` hold each project's rules. Use `generic` unless a project has its own profile.
For a new project, copy `profiles/generic.json`, change only what differs, and add it here.

## 3. Run the automatic checks

```bash
python <skill>/scripts/check.py <files or folder> --profile <name> [--out <dir>]
```

It writes `qa.json` and `qa_report.md`. Exit code 0 = passed, 1 = failed, 2 = no usable input.

TODO: describe any extra inputs (a script, a brief, reference images) and what they unlock.

## 4. Review

Go through `references/checklist.md` section B for every item. Judge each warning (section C).

## 5. Verdict and report

PASS only when the automatic checks passed, every warning was judged acceptable, and the review is clean.
Fill in the review line of `qa_report.md`, then tell the user: the verdict; each failing item with what is
wrong and the cheapest fix (section D); warnings and how you judged them; what couldn't be checked.
Never call an item that failed QC "ready".
