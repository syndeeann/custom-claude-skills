---
name: storyteller
description: "Writes detailed, specific, uncommon video scripts — a hook, beat-by-beat narration, and a ready-to-use visual prompt for every clip — for short-form and AI-generated video (Reels, Shorts, TikTok, Google Flow/Veo clips), then saves each one to video-projects/PROJECT/script/ in the owner's GitHub repo and pushes it. Picks an angle the audience hasn't seen before, checks every line for length, repeated words and clichés, and keeps facts honest. Use it whenever the user wants a video script, story, narration, voice-over, horror story, ad script or a new video idea written, in any project (Kwento: Kilabot, TikTok Shop ads, or a new one), even if they only say \"write the next script\" or \"give me a story about X\"."
metadata:
  title: Storyteller
  role: Script writer
  order: 1
  summary: "Writes detailed, uncommon video scripts: a hook, beat-by-beat narration and a visual prompt for every clip."
  responsibilities:
    - "Picks an angle the audience has not seen before"
    - "Writes narration clip by clip within the word budget"
    - "Checks every line for clichés and repeated words"
    - "Saves the script to the project folder on GitHub"
  category: content
  version: "1.0.0"
  media: text
  projects: [kwento-kilabot, tiktok-shop-ads]
---

# Storyteller

Writes video scripts worth watching: an angle the viewer hasn't seen, a hook that earns the first three
seconds, something new in every clip, and a visual prompt per clip so the script goes straight into Flow. It
writes and saves the script. It doesn't generate, edit or post video; those are separate steps in the
project's workflow.

A script is finished only when all four hold: the angle survived the cliché test, every line passes the swap
test, the lint passes, and the script is pushed to the repo.

Read `references/craft.md` before writing the first script in a conversation. The exact file layout is in
`references/script-format.md`, and `references/example-script.md` is a complete finished script.

## 1. Pin down the brief

You need: the **project**, the **topic or premise** (or "surprise me"), the **language**, the **length**
(number of clips), whether it's **fiction or real facts**, and any must-haves (a product listing, a character,
an ending).

- Take what the user gave you and fill the rest from the profile. Ask at most one short question, and only
  when a wrong guess would waste the whole script (an ad with no product details, say). Otherwise assume, and
  say your assumptions at the top of the reply.
- If nobody is around to answer, assume and put the assumptions in the script's Quality notes.
- For "surprise me" or no topic, choose one yourself from the profile's `idea_wells` and a quick search, using
  the angle method below.

## 2. Pick a profile

Profiles in `profiles/` hold each project's language, pace, runtime, voice and visual rules:

| Profile | Use for |
|---|---|
| `generic` | any project without its own profile (the default) |
| `kwento-kilabot` | Kwento: Kilabot Tagalog horror Reels/Shorts |
| `tiktok-shop-ads` | TikTok Shop UGC ads with the Taglish Ate Host |

Choose from the project name or what the user describes. For a new project, use `generic`; if the user wants
project-specific rules, write a small profile JSON that overrides only what differs (copy the shape of
`profiles/kwento-kilabot.json`) and save it in `profiles/`. Project rules never go in this file or the
scripts.

## 3. Research (when the script touches the real world)

Non-fiction, ads, and anything leaning on real folklore, history or customs: search first, on the
specifics you plan to use. Collect checkable details and their source URLs for the Fact sheet. For ads, the
facts come from the listing or the owner, not from the web. Fiction needs no research, but check any real
tradition you borrow. Never invent a statistic, date, quote or name for a real event.

## 4. Find an uncommon angle

This is what makes the script worth watching; don't skip it for speed. Follow section A of
`references/craft.md`: write the five obvious versions and ban them, generate at least eight alternative
angles using the levers, kill the weak ones, pick the one with the strongest concrete detail and a clear
turn, and write its one-sentence promise.

## 5. Write the script

Set the clip count from the length asked, or from the profile's runtime, in clips of the profile's
`clip_seconds`. Plan the beats first (hook, setup, escalation, turn, payoff), then write each clip to
`references/craft.md` sections B to F: hook shapes, one idea per clip, a turn at 60-70%, no repeated words,
lines that fit the clip, locked Look anchors, filmable visual prompts. Obey the profile's `style_rules` and
`visual_rules`. Then score the draft (section G) and rewrite anything below 4 out of 5.

Write the whole file in the format of `references/script-format.md`.

## 6. Save, lint, push

```bash
python <skill>/scripts/new_project.py <project> --topic "<working title>"        # creates script/ and prints the paths
# write the .md to the path it printed, then:
python <skill>/scripts/script_lint.py <that .md> --profile <name> --export-json <the .prompts.json path>
```

- Fix every `PROBLEM` and re-run. Judge each `warning`: fix it or keep it on purpose (and say so in the Beat
  or Quality notes). Stop after 3 rounds and report what still fails; never push a script that fails the
  lint and call it done.
- The JSON is only written when the lint has no problems, so a pushed `.prompts.json` always matches its `.md`.
- Scripts live in the owner's GitHub repo (`syndeeann/custom-claude-skills`) under
  `video-projects/<project>/script/`. If the repo isn't in the workspace, attach and clone it first. Then:

```bash
git pull --rebase origin main
git add video-projects/<project>/script/
git commit -m "script(<project>): NNN <title>"
git push origin main
```

If the push is rejected, pull with rebase and push again once, then report the error instead of retrying.
Never commit media files.

## 7. Reply

Keep it short: the title, the one-sentence promise, and why it is uncommon; the path in the repo; the lint
result and any warning you kept on purpose; assumptions you made and anything unverified. Give the full
narration only if the user asks to see it; the file is the deliverable. Offer the next step only if there
is a natural one (for example, checking the clips with `flow-clip-qa` once they exist).
