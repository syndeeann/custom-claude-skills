---
name: flow-clip-qa
description: "Also called Perpekto: when the owner says Perpekto, this is the skill they mean. Quality-assurance check for video clips made with Google Flow (Veo, Omni) — raw clips, a folder of downloads, or an assembled Reel/ad with its cut list. Runs automatic checks (format, black/frozen frames, missing or cut-off narration, sync, duplicate clips, repeated words in the script) plus a visual review of contact sheets (wrong scene, text/watermarks, garbled faces or hands, morphing products, lip-sync \"dubbing\"), then gives a pass/fail verdict with the cheapest fix for each failing clip. Use it whenever the user wants Flow or other AI-generated video clips checked, reviewed, QC'd or approved before editing or posting — in any project (Kwento: Kilabot, TikTok Shop ads, or a new one), even if they only say \"check these clips\" or \"is this video ready to post?\"."
metadata:
  title: Flow Clip QA
  persona: Perpekto
  role: Quality gate
  order: 3
  summary: "Checks Google Flow clips and finished reels, then gives a pass or fail verdict with the cheapest fix."
  responsibilities:
    - "Runs automatic checks for format, black or frozen frames and cut-off narration"
    - "Reviews contact sheets for wrong scenes, text, watermarks and garbled faces"
    - "Spots lip-sync dubbing and repeated words"
    - "Reports a verdict with evidence, and never posts or regenerates"
  category: qa
  version: "1.0.1"
  media: video
  projects: [kwento-kilabot, tiktok-shop-ads]
---

# Flow clip QA

A standalone quality gate for Google Flow clips. It doesn't belong to any one project: point it at
clips, pick a profile, and it returns a verdict. It checks and reports; it does not regenerate, re-edit
or post anything unless the user asks for that as a separate step.

QC has two halves, and a clip passes only when both pass:
1. **Automatic checks** — `scripts/flow_qa.py` measures what can be measured.
2. **Visual review** — you read the contact sheet and lip sheet it renders and judge what a script can't.

The full checklist (what each check means, how to judge warnings, the fix ladder) is in
`references/checklist.md`. Read it before your first review in a conversation.

## 1. Get the clips into the workspace

- **Attached files:** use them where they are.
- **On the user's computer** (e.g. `~/Downloads/Kwento Kilabot/`, `~/Downloads/TikTok Shop Ads/`, a Flow
  downloads folder): stage the files into the workspace through the device bridge, then check the copies.
- **A run folder in a repo** (has `brief.json`, `prompts.json`, `edit.json`, `clips/`, `<id>-final.mp4`):
  use the folder itself — the script detects it and checks the assembled final against its cut list.

Video files stay out of git; don't commit clips or sheets.

## 2. Pick a profile

Profiles (in `profiles/`) hold each project's format rules and visual checklist:

| Profile | Use for |
|---|---|
| `generic` | any project without its own profile (the default) |
| `kwento-kilabot` | Kwento: Kilabot horror Reels/Shorts (vertical 24 fps, off-screen narrator, strict no-dubbing) |
| `tiktok-shop-ads` | TikTok Shop UGC ads (Ate Host narration, hero clips silent, ≥ 60 s content, product must match its photo) |

Pick from context (project name, folder name, what the clips show). For a new project, run `generic`,
and if the user wants project-specific rules, write a small profile JSON for them that overrides only
what differs (see `profiles/kwento-kilabot.json` for the shape) and save it with their project.

## 3. Run the automatic checks

```bash
pip install numpy --break-system-packages -q 2>/dev/null; which ffmpeg ffprobe   # needs ffmpeg + numpy
python <skill>/scripts/flow_qa.py <clips or folder> --profile <name> [--script <file>] [--out <dir>]
python <skill>/scripts/flow_qa.py <run_dir> --profile <name>        # assembled final + cut list
```

- **`--script`** makes the check much sharper: it tells which clips should have narration, catches
  lines that are cut off or padded, checks repeated words, and gives the expected visual for each clip.
  Accepts a `prompts.json` (`{"clips": [{"voiceover", "visual", "hero", …}]}`), a JSON list, or a text
  file with one line per clip in clip order (`-` for a clip with no spoken line). A `prompts.json` or
  `script.txt` inside the clips folder is picked up automatically. Without a script, ask the user for
  the lines only if narration matters to them — otherwise run without and say what that skips.
- Clips are numbered in file-name order, so clip N pairs with script line N. If the names don't sort
  in story order, pass the files in the right order instead of the folder.
- Output: `qa.json`, `qa_report.md` and `check/qc_sheet.png` + `check/lip_sheet.png` in `--out`
  (default: a `qa-<timestamp>` folder beside the clips). Run mode writes `qc.json` and `check/` into the
  run folder, the same files the projects' original qc.py wrote, so existing workflows keep working.
- Exit code 0 = automatic checks passed, 1 = failed, 2 = no usable input.

To check a script before spending Flow credits, run only the repeated-words check:
`python <skill>/scripts/repeats.py <script file>`.

## 4. Visual review

Read `check/qc_sheet.png`, then `check/lip_sheet.png` if it exists, and go through the profile's
checklist (`qa.json → visual_review.checklist`) clip by clip — section B of `references/checklist.md`.
Open single frames for a closer look when a tile is too small. Judge each warning (section C).

## 5. Verdict and report

PASS only when the automatic checks passed, every warning was judged acceptable, and the visual review
is clean. Then:

1. Fill in the visual-review result in `qa_report.md` (per clip notes), so the file is a complete record.
2. Tell the user, briefly: the verdict; each failing clip — what's wrong and the cheapest fix
   (re-cut → re-download → trim → rewrite the line → regenerate, section D); warnings and how you judged
   them; anything that couldn't be checked (exact spoken words, motion between sampled frames).
   Send the contact sheet when it helps them see the problem.
3. If the user asks you to fix things, do the cheapest fix, then run the whole check again. Stop after
   2 fix rounds and report what still fails. Never call a clip that failed QC "ready".

When a project workflow calls this skill (a scheduled run, a posting pipeline), that workflow decides
what happens after the verdict — posting, approval, logging. This skill only supplies the verdict and
the evidence.
