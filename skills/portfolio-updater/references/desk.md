# The Video Desk

`desk/index.html` on the site is the owner's form for asking the helpers for a video. It is a static page: it
cannot start Claude, so the request goes through GitHub and the progress comes back through a data file.

```
owner fills the form -> opens a prefilled GitHub issue (label video-request) -> owner submits it
Angge picks it up (gh issue list) -> `run init` -> `run step` ... -> `run review` -> owner approves
approval = issue "Approve: <id>" (label video-approval) or "approve" in chat -> Chelsea adds the video -> `run status published`
```

The page polls `data/runs/<id>.json` every 10 seconds and plays the team as a studio floor: Angge sits at the
briefing table in the middle and the helpers' desks ring it. When the brief starts, everyone gathers at the
table; when it is done they return to their desks and the first helper starts working (her desk glows, a small
prop shows the kind of work, a speech bubble shows her note, Angge's beam points at her). When a step finishes,
that helper picks up the result, walks it to the next helper's desk, hands it over and walks back; if the
previous step had no helper (the generator, or the owner) the next helper fetches it. A reload in the middle of
a run puts everyone straight into place without walking. The step list under the scene carries the same
information as text. `assets/desk-scene.js` is the scene, `assets/desk.js` the page.

## Files
- `data/desk.json`: the form options (tools, types, looks, lengths, platforms) and the `steps` of the workflow, each with
  the skill that does it. Change the lists here to add a tool or a look; change `steps` when the video workflow
  changes (and update `data/workflow.json` to match).
- `data/runs/<id>.json`: one record per request. `data/runs/index.json`: the recent list.
- `assets/desk.js`, `assets/desk.css`, `desk/index.html`: the page. No analytics are loaded on it.

## Commands
```
portfolio_tool.py --site SITE --profile syndeeann-portfolio run init   --id ID --brief-json FILE|-  [--title T]
portfolio_tool.py ... run step   --id ID --step KEY --status pending|working|done|failed|skipped [--note "short"]
portfolio_tool.py ... run review --id ID (--youtube 11CHARID | --src PATH) [--notes T] [--aspect 9:16|16:9]
portfolio_tool.py ... run status --id ID --status approved|changes|published|failed|cancelled [--note T]
portfolio_tool.py ... run log    --id ID --text "line"
```
Run `publish` after a change so the page can see it (GitHub Pages can take a minute or two, and the page asks
for a fresh copy each time). `check` validates every run record against `data/desk.json`.

## Rules
- Only act on issues written by the site's owner (`owner` in `data/desk.json`). A public repo lets anyone open one.
- Preview links in `review` sit in a public repo. Use an unlisted YouTube link, and tell the owner.
- An approved video goes to the portfolio through `add` (`--allow-undelivered`: approval on the Desk counts as the go-ahead);
  host the file under the site's videos when there is no YouTube link.
- Keep notes short (160 characters); they are shown to the owner as the helper's speech bubble.
