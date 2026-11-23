# Custom Claude skills

My own skills for Claude, one folder per skill. They're standalone, so any project can use them.

## Who is who

Each skill has a first name, and the owner uses it in conversation. When you hear one of these names, it means that skill:

- **Marites** is `storyteller` (writes the video scripts)
- **Senyorita** is `ai-prompt-expert` (the prompt expert for Google Flow and other AI video tools)
- **Angge** is `video-director` (runs a whole AI video, from brief to approval)
- **Cassey** is `video-look-bible` (keeps the look and continuity of a project locked)
- **Etel** is `video-finishing` (colour and sound finishing after Jaiman's cut)
- **Jaiman** is `video-editor` (edits and compiles the clips into one seamless video, with the voice-over in sync)
- **Perpekto** is `flow-clip-qa` (the video QA)
- **Chelsea** is `portfolio-updater` (updates the portfolio when a video is delivered)

The name lives in each skill's `metadata.persona`.

## Skills

The list below is generated from each skill's `SKILL.md`. Don't edit it by hand: run
`python tools/skills.py index` after adding or changing a skill.

<!-- skills:begin -->
### Quality assurance (QA)

| Skill | Name | What it does | Media | Projects | Version |
|---|---|---|---|---|---|
| [`flow-clip-qa`](skills/flow-clip-qa/SKILL.md) | Perpekto | Quality-assurance check for video clips made with Google Flow (Veo, Omni) in any style, photoreal or animated — raw clips, a folder of downloads, or an assembled Reel/ad… | video | kwento-kilabot, tiktok-shop-ads | 1.3.1 |

### Content creation

| Skill | Name | What it does | Media | Projects | Version |
|---|---|---|---|---|---|
| [`ai-prompt-expert`](skills/ai-prompt-expert/SKILL.md) | Senyorita | Turns a video script or narration into clean, copy-ready generation prompts for Google Flow (Veo, Omni) and other AI video generators, in any visual style the video need… | video | kwento-kilabot, tiktok-shop-ads | 1.2.0 |
| [`storyteller`](skills/storyteller/SKILL.md) | Marites | Writes detailed, specific, uncommon video scripts — a hook, beat-by-beat narration, and a ready-to-use visual prompt for every clip — for short-form and AI-generated vid… | text | kwento-kilabot, tiktok-shop-ads | 1.2.0 |
| [`video-look-bible`](skills/video-look-bible/SKILL.md) | Cassey | Builds a locked look bible for an AI video project in any style (photoreal, anime, cartoon, 3D animation, claymation): character, place and product references, Style car… | image | any | 1.0.1 |

### Video production

| Skill | Name | What it does | Media | Projects | Version |
|---|---|---|---|---|---|
| [`video-director`](skills/video-director/SKILL.md) | Angge | The owner's video-creation workflow for every project: when they ask for any video, episode, ad, reel or short, Angge runs the whole job so they never have to call a hel… | video | any | 1.2.0 |
| [`video-editor`](skills/video-editor/SKILL.md) | Jaiman | Edits and compiles generated video clips (Google Flow, Veo, Omni and others) into one seamless video: puts the clips in the story order set by the script, trims and matc… | video | kwento-kilabot, tiktok-shop-ads | 1.2.1 |
| [`video-finishing`](skills/video-finishing/SKILL.md) | Etel | Finishing pass for an AI-generated video in any style (photoreal, anime, cartoon, 3D animation, claymation), after Jaiman (video-editor) has cut it: matches and grades e… | video | any | 1.0.1 |

### Automation

| Skill | Name | What it does | Media | Projects | Version |
|---|---|---|---|---|---|
| [`portfolio-updater`](skills/portfolio-updater/SKILL.md) | Chelsea | Updates the owner's static GitHub Pages portfolio every time a new video or app is delivered: adds it to the right studio in My AI Studio (Ads Videos, Kids, Stories, App… | web | kwento-kilabot, tiktok-shop-ads, portfolio | 1.4.0 |
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
