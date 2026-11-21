---
name: video-director
description: "Runs a whole AI video in any style (photoreal, anime, cartoon, 3D animation, claymation) from brief to approved final: script (Marites), look bible, prompts (Senyorita), generation, raw QA (Perpekto), cut (Jaiman), finishing, final QA and the owner's approval, then the portfolio (Chelsea). Use it whenever the owner wants a complete video or a new episode or ad made end to end, or asks what the next step of a video is."
metadata:
  title: Video Director
  role: Director and producer
  order: 0
  summary: "Runs every helper in order, from the brief to the approved final video, and stops at the owner's approval gates."
  responsibilities:
    - "Writes the brief, including the style: real-life, anime, cartoon, 3D animation or claymation"
    - "Runs Marites, the look bible, Senyorita, Perpekto, Jaiman and finishing in the right order"
    - "Keeps a take log so the same failure isn't paid for twice"
    - "Holds every video to the quality bar for its style"
    - "Never posts anything until the owner has watched and approved the final"
  category: production
  version: "1.0.0"
  media: video
  projects: []
---

# Video director

The director doesn't do the craft itself. It runs the owner's helpers in the right order, keeps one shared
record, and stops at the gates. Each step uses its own skill:

| Step | Skill | Output |
|---|---|---|
| 1. Brief | this skill | `video-projects/<project>/brief.md` |
| 2. Script | storyteller (Marites) | `script/NNN-<slug>.md` + `.prompts.json` |
| 3. Look bible | video-look-bible | `bible/bible.md` (Style card + references) |
| 4. Prompts | ai-prompt-expert (Senyorita) | `prompts/NNN-<slug>.md` + `.json` |
| 5. Generate | the owner in Flow, or this skill in the built-in browser | raw clips + take log |
| 6. Raw QA | flow-clip-qa (Perpekto) | verdict per clip |
| 7. Cut | video-editor (Jaiman) | cut + `edit.json`, voice-over in sync |
| 8. Finish | video-finishing | final `.mp4` + finishing settings |
| 9. Final QA | flow-clip-qa (Perpekto) | verdict on the final |
| 10. Approval | the owner | explicit yes |
| 11. Publish | the owner (or a posting step they ask for), then portfolio-updater (Chelsea) | live post + portfolio entry |

## 1. Brief
Project, goal (story, ad, explainer), audience, platform(s), length, aspect, language, must-haves (product,
logo, phone number, character), and the **style**:
- **Photoreal live action** (real-life characters and places), or
- **an animated style**: 3D animated ("Pixar-like"), anime / 2D cel, 2D cartoon, claymation / stop-motion, or
  another medium (watercolour, paper cut-out, comic, pixel art, low-poly).

The style comes from the owner, then the project profile. If neither says, ask; it's the one question worth
asking, because it changes every later step. When the owner names a studio or show, record it as traits in
the brief (rounded shapes, expressive eyes, soft light...) and note that only original characters are used:
never a studio's, show's or brand's characters, mascots or logos. The owner's own mascot is fine.

Fill other gaps from the profile and say what was assumed. Ask at most one question.

## 2. Pick the model for each clip
Models and limits change often: check the platform's current help page before planning (for example, Flow's
model list and clip lengths), and check that the chosen model does the style well with a 1-clip test before
a full batch. Decide per clip: text-to-video, ingredients/reference-to-video (anything that must match a
reference: a character, a product, a logo), or first-and-last-frame (smooth joins). Record the choice and
the source date in the brief.

## 3. Generation (step 5)
- If the owner generates: give them the prompt file, which references go with which clip, and how many takes
  to make (2 to 3 for hard shots).
- If asked to drive Flow in the built-in browser: confirm the credit cost before the first generation and
  before any batch, generate only the clips in the prompt file, and download with names that sort in clip
  order (`NN-take-T.mp4`).
- Keep a **take log** (`video-projects/<project>/takes/NNN.md`): clip, take, model, prompt version,
  keep/reject and why. It stops the same failure being paid for twice.
- If a project profile sets `"fix_policy": "edit_only"`, failed clips are fixed in the edit (Jaiman,
  finishing) and never regenerated.

## 4. The quality bar (definition of done)
A clip or final passes only when a full watch-through at normal speed and a pause-through show none of the
faults for its style.

**Every style:**
- **Style:** every clip matches the Style card; nothing drifts into another style partway through.
- **Characters:** the same face, design, colours, outfit and proportions in every shot; anatomy right for
  the design.
- **Objects and text:** no morphing products, no garbled or changing text, no stray logos or watermarks the
  owner didn't add, nothing resembling a known studio or brand character.
- **Story:** each picture matches its narration line; the order is right.
- **Sound:** a full sound bed and matching foley; no lips moving to an off-screen narrator; on-camera speech
  in sync.
- **Edit:** consistent frame rate, no glitch at a join, no jump-cuts in continuity.

**Photoreal, also:** real weight in motion (no floating, no sliding feet), a camera someone could hold, real
skin and texture, light with a source and shadows that agree, no frantic micro-cuts.

**Animated, also:** motion that follows the style's rules (squash and stretch, snappy timing, stepped
stop-motion), clean lines that don't crawl or melt, flat fills that don't flicker, and characters that stay
on model.

Fix ladder, cheapest first: fix in the edit → re-download or re-cut → rewrite the prompt (one action,
describe what should be there, add the force and contact for motion, paste the Style card again) → switch to
a reference or first-frame input → change model or tier → change the shot to one the generator does reliably
and let the narration carry the detail.

## 5. Honesty and disclosure
- Say plainly that generators are probabilistic: the process raises the hit rate a lot, but some shots need
  retakes or a different shot, and no step can promise zero flaws.
- Realistic AI video must be disclosed where platforms require it (YouTube's altered or synthetic content
  setting, TikTok's AI-generated label, Meta's AI info). Remind the owner to turn it on at upload. Never strip
  provenance data or hide watermarks.
- Never depict a real, identifiable person, a real brand other than the owner's, or a made-up testimonial
  presented as real.

## 6. Gates
- Stop after the script, after the look bible (so the owner sees the style and characters before any credits
  are spent) and after the final QA, unless they said to run straight through.
- **Nothing is posted or pushed to the portfolio until the owner has watched the final and explicitly
  approved it.**

## 7. Reply
At each gate: what's done, the style, the QA verdict with evidence, what's next, and any decision needed. At
the end: the final file, the QA verdict, a reminder about the AI disclosure setting, and the publish step
once approved.
