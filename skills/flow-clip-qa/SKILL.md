---
name: flow-clip-qa
description: "Also called Perpekto: when the owner says Perpekto, this is the skill they mean. Quality-assurance check for video clips made with Google Flow (Veo, Omni) in any style, photoreal or animated — raw clips, a folder of downloads, or an assembled Reel/ad with its cut list. Runs automatic checks (format, black/frozen frames, missing or cut-off narration, sync, duplicate clips, repeated words in the script AND spoken twice in the generated audio) plus a visual review of contact sheets and motion strips (wrong scene, off-style clips, text/watermarks, garbled or off-model faces or hands, morphing products, floaty motion, lip-sync \"dubbing\"), then gives a pass/fail verdict with the cheapest fix for each failing clip. Use it whenever the user wants Flow or other AI-generated video clips checked, reviewed, QC'd or approved before editing or posting — in any project (Kwento: Kilabot, TikTok Shop ads, or a new one), even if they only say \"check these clips\" or \"is this video ready to post?\"."
metadata:
  title: Flow Clip QA
  persona: Perpekto
  role: Quality gate
  order: 4
  summary: "Checks Google Flow clips and finished reels, then gives a pass or fail verdict with the cheapest fix."
  responsibilities:
    - "Runs automatic checks for format, black or frozen frames and cut-off narration"
    - "Reviews contact sheets for wrong scenes, text, watermarks and garbled faces"
    - "Judges each video against its own style, from real-life footage to anime, cartoon and 3D animation"
    - "Reads motion strips for floaty movement, sliding feet and crawling outlines"
    - "Spots lip-sync dubbing, and repeated words in the script and in the audio itself"
    - "Reports a verdict with evidence, and never posts or regenerates"
  category: qa
  version: "1.3.0"
  media: video
  projects: [kwento-kilabot, tiktok-shop-ads]
---

# Flow clip QA

A standalone quality gate for Google Flow clips. It doesn't belong to any one project: point it at
clips, pick a profile, and it returns a verdict. It checks and reports; it does not regenerate, re-edit
or post anything unless the user asks for that as a separate step.

QC has two halves, and a clip passes only when both pass (both are judged against the video's style,
section 2b):
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
| `ugc-ad` | Edited UGC ads with an on-camera creator, spoken prices and captions; adds the listen list and section F of the checklist |
| `tiktok-shop-ads` | TikTok Shop UGC ads (Ate Host narration, hero clips silent, ≥ 60 s content, product must match its photo) |

Pick from context (project name, folder name, what the clips show). For a new project, run `generic`,
and if the user wants project-specific rules, write a small profile JSON for them that overrides only
what differs (see `profiles/kwento-kilabot.json` for the shape) and save it with their project.

## 2b. Check against the video's style

Find the style first: the Style card in the prompt file, the script's `Style` line or the look bible. If none
exists, ask what style was intended before judging, because a cartoon judged as live action fails for the
wrong reasons. Then:

- **Photoreal** videos get every realism check (real weight, a camera someone could hold, real skin and
  texture, light with a source, believable sound).
- **Animated** videos (anime, 2D cartoon, 3D animated, claymation, others) are judged as animation, not as
  live action. Exaggerated motion, squash and stretch, stepped timing, flat colour and stylised proportions
  are correct when the Style card asks for them; don't fail them as "not real".

What fails in every style:
1. **Off-style or style drift**: a clip, or part of a clip, that changes style (turns photoreal, loses its
   outlines, changes shading or palette) or doesn't match the Style card.
2. **Off-model characters**: a face, eye shape, hair, outfit, colours or proportions that change within a
   clip or between clips. In animation, "on model" means matching the character design, not a real face.
3. **Anatomy against the design**: extra or fused fingers, limbs that bend wrongly, eyes that slide. Count
   against the design (a cartoon designed with four fingers passes with four).
4. **Line and surface faults** in drawn styles: outlines that crawl, break or melt from frame to frame,
   colour that flickers inside shapes, backgrounds that warp.
5. **Text, watermarks, stray logos**, morphing objects, wrong scene, dubbing and timing faults, exactly as
   for photoreal.
6. **Copied characters**: anything that looks like a known studio's, show's or brand's character or logo.
   Flag it as a fail; only original characters and the owner's own mascot pass.

Say in the report which style the video was checked against.

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

**Spoken repeats.** `repeats.py` only reads the written line, but Flow can say a word twice or restart a
phrase even from a clean line. `scripts/audio_repeats.py` finds that by sound (no speech recognition
needed): it compares every voiced stretch of the audio with the speech that follows and reports
`speech at A s said again at B–C s`. `flow_qa.py` runs it on every narrated clip, and on the whole final in run
mode. A strong match always fails; a weak match is a warning, or a failure when the profile sets
`audio_repeat_weak_is_problem`. It is a similarity measure, calibrated on synthetic audio: say so, and tell the
user which clip and time to listen to if something still sounds doubled.

## 4. Visual review

Read `check/qc_sheet.png`, then `check/lip_sheet.png` if it exists, and go through the profile's
checklist (`qa.json → visual_review.checklist`) clip by clip — section B of `references/checklist.md`.
Open single frames for a closer look when a tile is too small. Judge each warning (section C).

### Motion strips (what the contact sheet can't show)
The contact sheet samples a few frames, so floaty motion, sliding feet, crawling outlines and a camera that
glides like a machine slip through. For every clip with characters, hands, a moving product or a moving
camera, render a motion strip (8 frames a second, 16 per image) and read it in order:
```bash
ffmpeg -i clip.mp4 -vf "fps=8,scale=160:-1,tile=8x2" check/motion_NN_%02d.png
```
In every style, look for: a face or design that changes between neighbouring frames, a hand that passes
through an object, a background that bends, a sudden change of style. For photoreal, also look for objects
moving at one constant speed with no lift or settle, feet that slide or never press into the ground, and a
camera path too smooth for the shot type. For drawn styles, also look for outlines that boil or break.

### Realism tells (photoreal only)
Each of these is a FAIL for photoreal videos: waxy or plastic skin, light with no source in the scene,
shadows that disagree, colour that jumps between clips, a too-clean or silent soundtrack, sound that doesn't
match the action (a hard object with no hard sound), and very short frantic cuts in an assembled video. For
animated videos, judge sound and cuts against the style instead (cartoon foley and snappy cuts can be right).

### Exact words
The scripts can't hear words. When the owner cares about exact narration and a transcription tool is
connected (for example Descript's transcribe), transcribe the narrated clips and compare them with the
script word for word. Otherwise say the words weren't checked and give the listen list.

### Finished videos (after video-finishing)
Also check the final file: loudness (`ffmpeg -i final.mp4 -af ebur128=peak=true -f null -`; about -14 LUFS
integrated and a true peak below -1 dB unless the profile says otherwise), every caption, price and phone
number spelled exactly as in the script or listing, the real logo with no text on top of it, the same grade
(and, for photoreal, the same grain) across every shot, and nothing cut mid-word at a join.

## 5. Verdict and report

PASS only when the automatic checks passed, every warning was judged acceptable, and the visual review
is clean. Then:

1. For `ugc-ad` (or any video with a spoken price, number or brand word), add a LISTEN LIST to the report: scene, timestamp and approved line for each; say plainly that exact words cannot be machine-checked. Fill in the visual-review result in `qa_report.md` (per clip notes), so the file is a complete record.
2. Tell the user, briefly: the verdict; each failing clip — what's wrong and the cheapest fix
   (section D — for a profile with `"fix_policy": "edit_only"` only the editing fixes; never "regenerate"); warnings and how you judged
   them; anything that couldn't be checked (exact spoken words, motion between sampled frames).
   Send the contact sheet when it helps them see the problem.
3. If the user asks you to fix things, do the cheapest fix, then run the whole check again. Stop after
   2 fix rounds and report what still fails. Never call a clip that failed QC "ready".

When you suggest a fix:
- **Edit before regenerate.** Trims, cutaways, slight reframes, a small slow-down and re-cuts (Jaiman,
  video-finishing) come before spending credits. Say which clips can be saved in the edit.
- **Write regenerate fixes the way Senyorita's rules require**: describe what should be there (lips pressed
  together, a blank wall, a slow single grip, the Style card pasted again) instead of "no talking" or
  "absolutely no text". Negative instructions often backfire. This replaces the negative examples in
  `references/checklist.md` section D.
- **Name the root cause** when the same failure shows up in more than one clip (for example, every
  handheld shot floats, or every wide shot loses the outlines), so the prompt rule gets fixed once for all
  clips.

When a project workflow calls this skill (a scheduled run, a posting pipeline), that workflow decides
what happens after the verdict — posting, approval, logging. This skill only supplies the verdict and
the evidence.
