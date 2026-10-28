# Custom Claude skills

My own skills for Claude, one folder per skill. They're standalone, so any project can use them.

## Skills

The list below is generated from each skill's `SKILL.md`. Don't edit it by hand: run
`python tools/skills.py index` after adding or changing a skill.

<!-- skills:begin -->
### Quality assurance (QA)

| Skill | What it does | Media | Projects | Version |
|---|---|---|---|---|
| [`flow-clip-qa`](skills/flow-clip-qa/SKILL.md) | Quality-assurance check for video clips made with Google Flow (Veo, Omni) — raw clips, a folder of downloads, or an assembled Reel/ad with its cut list. | video | kwento-kilabot, tiktok-shop-ads | 1.0.0 |

### Content creation

| Skill | What it does | Media | Projects | Version |
|---|---|---|---|---|
| [`storyteller`](skills/storyteller/SKILL.md) | Writes detailed, specific, uncommon video scripts — a hook, beat-by-beat narration, and a ready-to-use visual prompt for every clip — for short-form and AI-generated vid… | text | kwento-kilabot, tiktok-shop-ads | 1.0.0 |
<!-- skills:end -->

## Layout

```
skills/
  <skill-name>/            one folder per skill; the folder name is the skill name
    SKILL.md               what the skill does and how Claude runs it (frontmatter + instructions)
    scripts/               code the skill runs
    references/            longer docs Claude reads when needed (checklists, guides)
    profiles/              per-project settings (QA skills), e.g. kwento-kilabot.json
templates/
  qa-skill/                starting point for a new QA skill
video-projects/
  <project>/script/        scripts written by the storyteller skill (text only), one folder per project
tools/skills.py            create, check, index and package skills
dist/                      built .skill files (not committed; CI builds them)
```

## Add a new QA skill

```bash
python tools/skills.py new thumbnail-qa --media image --description "Checks thumbnails before posting…"
# or start from an existing one:
python tools/skills.py new reel-caption-qa --from flow-clip-qa
```

Then fill in the TODOs in `skills/<name>/`, and run:

```bash
python tools/skills.py validate     # name, description, files the skill mentions, valid JSON/Python
python tools/skills.py index        # refresh the list above
```

Or just ask Claude: "add a new QA skill to my custom-claude-skills repo that checks …".

Each skill's `SKILL.md` frontmatter carries its listing info:

```yaml
---
name: flow-clip-qa                 # = folder name, lowercase-with-hyphens
description: "What it does and when to use it (≤ 1024 characters)"
metadata:
  category: qa                     # groups the index: qa, content, automation, …
  version: "1.0.0"
  media: video                     # what it checks: video, image, audio, text
  projects: [kwento-kilabot]       # projects with their own profile; empty = any
---
```

To add a project to an existing QA skill, add a profile JSON to `skills/<name>/profiles/` that overrides
only what differs from `generic.json`.

## Install a skill in Claude

- **From GitHub Actions:** every push builds `dist/<name>.skill` files. Download the "skills" artifact
  from the latest run, open the `.skill` file in Claude, and click **Save skill**.
- **Locally:** `python tools/skills.py package <name>` builds `dist/<name>.skill`.
- **In a Claude Code project:** copy `skills/<name>/` into that project's `.claude/skills/`.

## Checks on every push

`.github/workflows/skills.yml` validates every skill, fails if the index above is out of date, and
packages all skills.
