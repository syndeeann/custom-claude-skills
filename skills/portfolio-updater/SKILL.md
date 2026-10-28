---
name: portfolio-updater
description: "Updates the owner's static GitHub Pages portfolio every time a new video or app is delivered: adds it to the right studio in My AI Studio (Ads Videos, Kids, Stories, Applications), shows a NEW badge for its first 7 days, keeps each studio's own page, the workflow section and the Claude skills section (with a GitHub button) current, then pushes to the live branch. Use it whenever a video has been posted or delivered, a new app is finished, a skill was added or changed, or the user says update my portfolio, add this to my studio, show my latest video or add a new studio, in any project (Kwento: Kilabot, TikTok Shop ads, kids, apps)."
metadata:
  title: Portfolio Updater
  role: Portfolio publisher
  order: 4
  summary: "Adds every delivered video or app to the right studio on the portfolio, with a NEW badge for its first week, and keeps the workflow and skills sections current."
  responsibilities:
    - "Adds each delivered video or app to the portfolio"
    - "Classifies it into Ads, Kids, Stories or Applications"
    - "Shows a NEW badge for 7 days after it is published"
    - "Keeps each studio page, the workflow and the skills showcase up to date"
    - "Pushes the update to the live branch and checks it"
  category: automation
  version: "1.0.0"
  media: web
  projects: [kwento-kilabot, tiktok-shop-ads, portfolio]
---

# Portfolio updater

Keeps the owner's portfolio in step with finished work. The site is static: pages render `data/*.json` in the
browser, so an update is a change to a few JSON files plus a push. This skill makes that change, checks it and
pushes it. It does not generate, check or post video; those belong to the pipeline that calls it, which runs
this skill last, after a video is delivered.

Everything specific to one site (repos, branches, project-to-studio rules, hand-built pages) is in
`profiles/syndeeann-portfolio.json`. Use `profiles/generic.json` as the starting point for another site. The
data formats are in `references/data-formats.md`; how to call this from a pipeline is in
`references/pipeline-hook.md`.

## 1. Get the site

Clone or open the portfolio repo on its live branch (`live_branches` in the profile; for the owner's site that
is `feature/portfolio-v4`, mirrored to `gh-pages`; never the stale `master`). Run every command below from the repo root, or pass `--site DIR`. Add
`--profile syndeeann-portfolio` to each call.

## 2. Add what was delivered

For a video from the reels pipeline, point at its run folder:

```
python scripts/portfolio_tool.py --site SITE --profile syndeeann-portfolio add \
  --run-dir path/to/output/2026-10-28-linya-trese
```

It reads `brief.json` and `run-log.md`, and takes the title, summary, duration, YouTube link and the date it was
posted from them. It refuses a run that is not delivered (no `posted` status), and says so rather than adding
it. Override anything it guesses with `--title`, `--description`, `--youtube`, `--published`, `--folk`.

For anything else, pass the facts directly (`--project`, `--title`, `--description`, `--published`, and
`--youtube` or `--link`). For an app add `--type app --link LIVE_URL --repo SOURCE_URL --platforms Web,Android`.

**Classification.** The project's studio wins (kwento-kilabot is Stories, tiktok-shop-ads is Ads). Otherwise the
studio keywords decide: ads and TikTok products go to Ads Videos, children's content to Kids, web and mobile
apps to Applications, folklore and horror to Stories. If nothing matches, the tool stops and asks for
`--studio`. Never guess a studio; a video in the wrong studio is worse than a short delay. Check the choice
with `classify` first when unsure.

**The NEW badge.** Nothing to do. The page works it out from `published` and the badge disappears after 7 days
(`newBadgeDays` in `data/studios.json`). Re-running `add` for an existing video keeps its first publish date.
Use `--republish` only when the owner wants the badge restarted.

## 3. Keep the other sections current

- A new skill or a changed skill description: `sync-skills --skills-repo PATH_TO_SKILLS_REPO` rebuilds
  `data/skills.json` from each skill's `metadata` (title, role, summary, responsibilities, projects, order).
  A skill that lacks those fields shows with a plain fallback and a warning; fill them in.
- A new kind of output: `new-studio --id ID --name NAME --tagline TEXT --kind video|app --keywords a,b,c`
  adds it to My AI Studio and generates its page at `ID/`. Then add its pipeline to `data/workflow.json`.
- Changed template or styles: `build-pages` regenerates every generated studio page. Hand-built pages
  (listed under `legacy_pages` in the profile) are never overwritten; the tool only edits the video list
  between their marker comments.
- Workflow steps live in `data/workflow.json`. Name the skills that really run in each step, by id. Do not
  list a skill that the pipeline does not use.

## 4. Check, then publish

```
python scripts/portfolio_tool.py --site SITE --profile syndeeann-portfolio check
python scripts/portfolio_tool.py --site SITE --profile syndeeann-portfolio publish --message "Add Kilabot #5"
```

`check` must say OK: valid JSON, every item in a real studio, every studio page present, every skill named in a
workflow present, and the home page hooks intact. `publish` runs `check` again, commits, and pushes to each
live branch. Add the commit trailers the session asks for to the message.

After pushing, open the live page when you can (GitHub Pages takes a minute or two) and look for the NEW badge
on the new card, the studio count, and the studio page. Say plainly if you could not check it.

## Rules

- Only delivered work goes on the portfolio. Private drafts, unposted renders and failed QC stay off.
- Never commit video files. The site links to YouTube or another host; posters come from the host's thumbnail.
- Never edit `analytics.js`, the analytics docs or the owner's CV and photo files.
- Data is rendered as text, never as markup. Do not paste HTML into titles or descriptions.
- Report what changed: the item, its studio, its date, and what you could not verify.
