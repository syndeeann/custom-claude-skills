# Script file format

A script is one Markdown file. `scripts/script_lint.py` reads it, so the clip blocks must follow the format
below exactly. The `.prompts.json` next to it is exported from the Markdown by the lint script, never written
by hand, so the two can't disagree.

## Where files go

```
video-projects/
  <project>/                 one folder per video project, lowercase-with-hyphens
    script/                  everything the storyteller writes for this project
      001-<topic-slug>.md           the script (source of truth)
      001-<topic-slug>.prompts.json exported from the .md, for the QA skills and the Flow workflow
      002-<topic-slug>.md
```

`scripts/new_project.py` creates the folders and prints the next file names.

## The Markdown file

```markdown
# <Title>

- **Project:** <project>
- **Script no.:** 001
- **Date:** 2026-10-28
- **Type:** Fiction | Non-fiction | Ad
- **Language:** <language>
- **Format:** vertical, <n> clips x <s> s = about <total> s
- **Profile:** <profile name>

## Angle

**Promise:** one sentence: who or what, the specific strange thing, the consequence, the unusual way in.

**Why it's uncommon:** two or three sentences.

**Obvious versions rejected:** a list of the five obvious scripts from the craft guide, one line each.

## Fact sheet

Only for Non-fiction and Ad. One line per checkable claim: the claim, then where it came from (URL, or
"product listing", or "owner").

## Look anchors

One locked descriptor per recurring character, place or product, written once, pasted verbatim into every
visual prompt where it appears.

## Script

### Clip 01 — HOOK (8s)
- **Voiceover:** the exact line to record.
- **Visual:** the full Flow prompt for this clip, ending with the profile's required closing words.
- **Sound:** music and effects, or "silence".
- **Beat:** the new information or turn this clip delivers (and any deliberate callback).

### Clip 02 — SETUP (8s)
...

## Full narration

The voiceover lines joined in order, as one block to read through or record in one take.

## Quality notes

Scores out of 5 with a one-line reason each: hook, uncommonness, clarity, payoff, voice. Then anything the
owner should know: assumptions made, unverified details, which parts of a legend are traditional and which are
invented, how the length compares with the profile's runtime.
```

### Clip block rules

- Heading: `### Clip NN — LABEL (Ns)`, numbered from 01 without gaps. The label is a one-word beat name such
  as HOOK, SETUP, ESCALATION, TURN, PAYOFF. The `(8s)` is the clip length; leave it out to use the profile's
  `clip_seconds`.
- The four fields use exactly `- **Voiceover:**`, `- **Visual:**`, `- **Sound:**`, `- **Beat:**`. A field may
  continue on following lines.
- A clip with no spoken line writes `- **Voiceover:** none` and adds `- **Hero:** yes`.
- The lint measures each Voiceover against the clip length and the profile's pace, so the line should fit.

## The exported JSON

`python scripts/script_lint.py <script.md> --profile <name> --export-json <file>` writes:

```json
{
  "title": "...", "project": "...", "language": "...",
  "clips": [
    {"n": 1, "seconds": 8, "label": "HOOK", "beat": "...", "voiceover": "...", "visual": "...", "hero": false}
  ]
}
```

The `clips` list uses the same field names as the `prompts.json` that `flow-clip-qa` accepts through
`--script`, so a script can be checked against its clips without conversion.
