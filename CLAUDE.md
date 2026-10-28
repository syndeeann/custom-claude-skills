# custom-claude-skills

The owner's library of standalone Claude skills, mostly QA (quality-assurance) skills that any project can
use. One folder per skill under `skills/`; nothing in the tooling is specific to one skill.

## Rules
- A skill must stay project-independent. Project-specific rules go in that skill's `profiles/<project>.json`,
  never in its scripts or `SKILL.md` body.
- New QA skill: `python tools/skills.py new <name> [--media …] [--description …]` (or `--from <skill>`),
  then fill in every TODO. Keep `SKILL.md` under 500 lines; put long checklists in `references/`.
- Before committing: `python tools/skills.py validate && python tools/skills.py index` and commit the
  updated `README.md`. CI fails on an out-of-date index.
- Bump `metadata.version` in `SKILL.md` when a skill's behaviour changes.
- Never commit media files (clips, renders, contact sheets), `qa-*` output folders or `dist/`.
- A QA skill reports a verdict and evidence; it doesn't post, approve or regenerate. Those belong to the
  project workflow that calls it.
