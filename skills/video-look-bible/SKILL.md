---
name: video-look-bible
description: "Builds a locked look bible for an AI video project in any style (photoreal, anime, cartoon, 3D animation, claymation): character, place and product references, Style card, palette and light, before any clip is made. Use it whenever a video has a recurring character, place, product or mascot, when the owner wants a new style or cast for a project, or when clips don't match each other from shot to shot."
metadata:
  title: Look Bible
  role: Continuity and style keeper
  order: 6
  summary: "Locks the style, characters, places and products of a video before any clip is generated, so every clip matches."
  responsibilities:
    - "Writes the Style card for the video, from real-life footage to anime, cartoon and 3D animation"
    - "Makes reference sheets for every recurring character, place and product"
    - "Uses the owner's real photos, logo and mascot instead of inventing them"
    - "Keeps characters original, never copied from a studio or brand"
    - "Saves the bible where Marites, Senyorita and Perpekto can find it"
  category: content
  version: "1.0.0"
  media: image
  projects: []
---

# Video look bible

Consistency doesn't come from the video model. It comes from locked references that go with every prompt.
This skill makes those references once per project (or per season) and saves them where the storyteller
(Marites), prompt writer (Senyorita) and QA (Perpekto) can find them. It doesn't write scripts, prompts or
clips.

Run it after the script exists and before the first prompt. Re-run it only when a look changes on purpose
(new outfit, new location, new style).

## 1. Inputs
- The script (`video-projects/<project>/script/NNN-<slug>.md`): its `Style` line, Look anchors, cast list,
  places and props.
- Anything real the owner supplies: product photos, the business logo, real location photos, their mascot.
  **Real images always beat generated ones.** Never invent the look of a product or logo.
- **The style.** From the script, then the owner, then the project profile. If none says, ask once
  (real-life or animated, and which kind), because every reference depends on it.
- Anything else missing: ask once only if a wrong guess would waste the set. Otherwise assume and say so.

## 2. The Style card (first, for the whole project)
One block that every prompt will end with: the style family, 5 to 8 concrete visual traits, line and
shading, palette (3 to 5 colours, hex values when known), how light behaves, how things move, frame-rate
feel, aspect ratio, and what counts as off-style.

| Family | Traits to lock |
|---|---|
| Photoreal live action | lens look, real light sources and direction, skin and surface texture, slight film grain added in finishing, 24 fps |
| 3D animated feature ("Pixar-like") | rounded appealing shapes, large expressive eyes, soft subsurface skin, soft bounce light, rich colour, stylised proportions |
| Anime / 2D cel | clean ink lines, line weight, 2 to 3 tone cel shading, painted backgrounds, eye highlight style |
| 2D cartoon | outline thickness, flat colour fills, simple shapes, finger count, how mouths are drawn |
| Claymation / stop-motion | clay texture with fingerprints, miniature set materials, practical lights, stepped motion |
| Others (watercolour, paper cut-out, comic, pixel art, low-poly) | the medium's own materials, edges and texture |

When the owner names a studio or show ("Pixar-style", "like an anime"), write the traits, not the name:
generators follow descriptions better, and some refuse studio names. **Original characters only**: never
recreate a studio's, show's or brand's characters, mascots, logos or scenes. The owner's own mascot is fine,
from their image.

## 3. References for each subject
For every recurring **character**:
- One locked text anchor (build, face shape, hair, clothes, colours, one distinctive detail; for real-life
  people also age and skin), pasted word for word into every prompt.
- A reference pack in the Style card's style, made in an image model (Nano Banana or whatever Flow offers):
  front, 3/4, profile and full body, plus a face close-up, on a plain neutral background, with **neutral
  closed-mouth expressions** (open mouths in references push the video model toward talking). For an animated
  character that will speak on camera, add one sheet of mouth shapes and 3 to 4 expressions.
- **Photoreal:** real-skin detail (pores, fine lines, flyaway hair, slight asymmetry); smooth, plastic
  references drift faster across shots.
- **Animated:** a clean model sheet: exact proportions (head-to-body ratio), finger count, line weight and
  colour fills, so "on model" can be checked later.
- Nothing held in the hands, so props don't appear in random shots.

For every recurring **place**: one wide and one medium reference in the style, fixed time of day, the light
source named (window, tube light, streetlight, sky) and its direction.

For every **product / logo**: the owner's photo or file, exact colours, which side faces the camera. In
animated videos, a product can be drawn in the style only if the owner agrees; otherwise show the real photo
in an edit insert.

## 4. Make, compare, lock
1. Generate 4 options per reference. Ask the owner to pick, or pick the one that best fits the Style card
   and say why.
2. Check the pick: same style across the whole pack, hands and fingers against the design, eyes and teeth,
   no text on clothes, only the real logo, no resemblance to a known character, colours that match the
   palette.
3. Lock it: from here on, the anchor, the Style card and the images change only with the owner's say.

## 5. Save
`video-projects/<project>/bible/bible.md` holds the Style card, anchors, palette, light, frame rate, and
which image is which. **Image and video files never go in git**: keep them in the owner's project folder on
their computer (or Flow's asset library) and record the file names in `bible.md`. Commit and push `bible.md`
only (`git pull --rebase origin main`, add, commit, push) in the owner's repo
`syndeeann/custom-claude-skills`.

## 6. Reply
The style that was locked, what references were made, where they're saved, what was assumed, and anything
still missing (e.g. no real product photo). Next step: Senyorita writes prompts that use these references as
ingredients and end with the Style card.
