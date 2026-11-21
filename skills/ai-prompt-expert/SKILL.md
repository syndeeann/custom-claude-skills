---
name: ai-prompt-expert
description: "Also called Senyorita: when the owner says Senyorita, this is the skill they mean. Turns a video script or narration into clean, copy-ready generation prompts for Google Flow (Veo, Omni) and other AI video generators, in any visual style the video needs: photoreal live action, anime, 2D cartoon, 3D animation (Pixar-like), claymation and more. Every prompt shows what its narration line says, keeps on-screen characters from lip-syncing an off-screen narrator, avoids repeated words, keeps one style locked across clips, and follows the platform's own prompting guidance; a lint step checks it before the prompts are saved to video-projects/PROJECT/prompts/ in the owner's GitHub repo and pushed. Use it whenever the user wants prompts for Flow, Veo, Omni, Runway, Kling, Sora or any AI video tool, wants a script's visuals turned into prompts, or says a clip looks fake, off-style, shows the wrong picture, has subtitles or has people talking, in any project (Kwento: Kilabot, TikTok Shop ads, or a new one)."
metadata:
  title: AI Prompt Expert
  persona: Senyorita
  role: Video prompt engineer
  order: 2
  summary: "Turns a script into clean prompts for Google Flow and other AI video generators, in any style from photoreal to anime, cartoon and 3D animation."
  responsibilities:
    - "Writes one prompt per clip with no repeated words"
    - "Shows on screen what the narrator says"
    - "Keeps the on-screen character from dubbing the narrator"
    - "Keeps looks consistent with reusable character and place descriptions"
    - "Locks one visual style per video, from real-life footage to anime, cartoon and 3D animation"
  category: content
  version: "1.2.0"
  media: video
  projects: [kwento-kilabot, tiktok-shop-ads]
---

# AI Prompt Expert

Writes the prompts that go into Google Flow and other AI video generators, for photoreal or animated videos.
A good prompt does four jobs at once, and this skill checks all four:

1. **Shows what the narration says**: every phrase of the line has a picture, in the order it is heard.
2. **No dubbing**: when a narrator speaks, nobody on screen moves their lips.
3. **Clean wording**: no repeated words, no empty quality words, one action per clip, nothing a generator
   tends to fumble.
4. **Looks right for its style**: photoreal clips look filmed (a real camera behaviour, a real light source,
   real textures); animated clips look like one well-made animation, in the same style in every clip
   (section 2b).

It writes prompts. It doesn't generate, check or post the clips; `flow-clip-qa` checks the clips afterwards. No
prompt can guarantee a flawless clip, since generators are probabilistic. What this skill does is remove the
known causes of bad clips and give a short fix ladder for the rest (`references/realism.md`).

Read `references/realism.md` before writing the first prompt in a conversation. Platform details are in
`references/platforms.md`, the file layout in `references/prompt-format.md`, and a finished example in
`references/example-prompts.md`.

## 1. Get the inputs

- **The script.** Normally the storyteller's file at `video-projects/<project>/script/NNN-<slug>.md`. Use its
  Voiceover lines word for word, and its Look anchors and Beat notes. If the user pastes narration instead,
  use that; if they give only a topic, ask them to run the storyteller first or offer to do it.
- **The platform.** Default is Google Flow. If the user names another tool (Runway, Kling, Sora, Pika, Luma...),
  follow section 6 of this file before writing.
- **Reference images** (a product photo, a character or place image): use them as the platform's reference
  inputs instead of describing from memory, and list them in the file.
- **The look bible.** If `video-projects/<project>/bible/bible.md` exists (made by video-look-bible), use its
  style, anchors, palette, light direction, time of day and frame rate exactly, and name which reference
  image goes with each clip. If it doesn't exist and the video has a recurring character, place or product,
  suggest making it first.
- **Current model limits.** `references/platforms.md` was last checked on 2026-10-28 and is already out of
  date: Gemini Omni 1.2 Flash (released 2026-11-05) makes clips up to 15 s, supports multi-turn editing and
  follows references more closely, and it is in Flow. Before planning clip lengths, check Flow's current
  models page, update `platforms.md` with the date, and if a chosen length isn't in the profile's
  `allowed_seconds`, update that profile first so the lint accepts it.
- **Anything missing**: assume from the profile and say so at the top of the reply. Ask at most one question,
  only when a wrong guess would waste the whole set.

## 2. Pick a profile

Profiles in `profiles/` hold each project's look, clip modes and closing line:

| Profile | Use for |
|---|---|
| `generic` | any project without its own profile (the default) |
| `kwento-kilabot` | Kwento: Kilabot horror: off-screen narrator, faces never shown speaking |
| `tiktok-shop-ads` | TikTok Shop UGC ads: on-camera Ate Host clips, voiceover clips and silent hero clips |

For a new project, use `generic`, and if the user wants project-specific rules write a small profile JSON that
overrides only what differs (copy the shape of `profiles/kwento-kilabot.json`). Project rules never go in this
file.

## 2b. Pick and lock the style

Every video has exactly one style, written once as a **Style card** at the top of the prompt file and pasted
word for word at the end of every prompt, before the closing line (like a Look anchor; set it as the
profile's `base_look` so the lint treats it as exempt text). Take the style from the script's `Style` line,
the look bible or the owner's request. If none says, use the profile's default; if the profile has none, ask
once (photoreal or animated, and which kind), because the wrong style wastes the whole set.

A Style card names: the style family, 5 to 8 concrete visual traits, line and shading, palette, how light
behaves, how things move, the frame-rate feel, and what would count as off-style. Starting points (adjust
to the owner's brief):

| Family | Visual traits to write | Motion |
|---|---|---|
| Photoreal live action | lens, real light source, skin and surface texture | real weight: start, contact, settle |
| 3D animated feature ("Pixar-like") | rounded appealing shapes, large expressive eyes, soft subsurface skin, soft bounce light, rich saturated colour, shallow depth of field | squash and stretch, clear anticipation and follow-through |
| Anime / 2D cel | clean ink line art, 2 to 3 tone cel shading, painted backgrounds, bold highlights in the eyes | held poses with snappy moves, a slight stepped feel |
| 2D cartoon | thick even outlines, flat bright colour, simple shapes, minimal texture | bouncy, exaggerated, rubbery timing |
| Claymation / stop-motion | sculpted clay with fingerprints and tool marks, miniature sets, practical lights | slightly stepped, handmade jitter |
| Others (watercolour, paper cut-out, comic book, pixel art, low-poly) | the medium's own materials and edges | what that medium can do |

Rules for every style:
- **Describe the look, don't lean on a name.** The owner may say "Pixar-style" or "Ghibli-like" as
  shorthand. Translate it into traits like the ones above: some generators ignore or refuse studio and
  artist names, and traits are what the model can follow.
- **Original characters only.** Never recreate a studio's, show's or brand's characters, mascots, logos or
  scenes, even in a new style. The owner's own mascot (e.g. a business mascot) is fine, from their image.
- **One style per video.** No clip may drift into another style (an anime clip that turns photoreal halfway,
  a 3D clip that goes flat). Keep the Style card, palette and light direction identical across clips.
- **Style decides which realism rules apply.** The photoreal rules (real lens, real texture, real weight, a
  camera someone could hold) are for photoreal videos. Animated styles use their own camera and motion
  language, and exaggerated motion is correct there. Every style keeps: one action per clip, no morphing,
  consistent characters, no generated text, the no-dubbing rules for voiceover clips, and pictures that
  match the narration.
- **The lint.** Its lens and light warnings assume a camera. For animated clips, still name the framing and a
  light (animation has staged light too); if a lens cue doesn't fit (2D cel), keep the warning on purpose and
  say so in the clip's Review line.
- **On-camera speech in animation.** Animated characters speaking on camera is a strength of cartoon and 3D
  styles: use `on-camera` mode with the line in quotes and the speaker named (or a `"dialogue": true`
  profile for two or more talking characters).

## 3. Plan each clip before writing it

For every clip, decide three things and write them down:

- **Mode.** `voiceover`: an off-screen narrator speaks and nobody on screen does. `on-camera`: one visible
  person speaks the line (only when the script or profile says so). `hero`: a silent clip with no line.
- **Covers.** Split the narration into its phrases and give each phrase a concrete, filmable picture:
  `"phrase" → picture; "phrase" → picture`. Concrete words become the literal thing. Abstract words become the
  nearest visible evidence (a death becomes years of dust; dread becomes a hand that stops). Time and numbers
  become light, objects or a simple cue, never a readable clock or sign. Pictures appear in the order the
  phrases are heard.
- **Shot.** One continuous shot with one main action. Vary the camera and framing from the neighbouring clips.
- **Motion with weight.** Write the action in three parts: the start (a reach, a shift of weight), the contact
  (a hand closes on the cup, a foot presses into wet sand) and how it settles (the cup lifts with a small
  wobble, the door swings and stops). In photoreal clips that is real physics; in animated clips use the
  style's version (anticipation, squash and stretch, follow-through). Actions written with no force come out
  floaty in every style.
- **Takes.** Mark hard clips (hands, characters moving, products in motion) as `takes: 2-3`, so the owner
  generates options instead of re-prompting after one try.

## 4. Write the prompt

One paragraph per clip, in this order (the five-part structure Google recommends for Veo, plus audio and a
clean-frame line): **shot and lens → subject (locked Look anchor, pasted verbatim) → one action → setting →
light and look → audio → the profile's closing line.**

Rules that the lint enforces:

- **No repeated words** inside a prompt: vary the vocabulary (light, glow, lit, sheen). Locked anchors, the
  profile's base look and the closing line are exempt because they are copied verbatim on purpose.
- **Describe, don't negate.** Generators handle "no X" badly, so describe what is there: closed lips, a quiet
  room, a hand that stops. The one exception is the closing line.
- **Voiceover and hero clips**: no quoted text, no speech words (says, talking, voice, dialogue), no camera-facing
  faces. Any visible person is framed from behind, in silhouette or by their hands, or has lips pressed
  together and eyes on an object. Name two or three specific ambient sounds so the audio track is filled.
- **On-camera clips**: the exact narration goes in quotation marks with a named speaker, and nobody else speaks.
  Exception: a profile with `"dialogue": true` (animated shows with two or more talking characters) lets each
  speaker's line be quoted separately, with a named speaker each; the quoted lines in order must equal the
  Narration word for word, and each character's voice is described once in the prompt.
- **Look for the style**: photoreal clips name a lens or a real camera behaviour, a real light source, and one
  or two textures; animated clips end with the Style card and name the framing and light. Skip empty quality
  words (8K, masterpiece, ultra-realistic) in every style.
- **No morphing or sequences**: no "turns into", no "then". Simple actions only (slow and physical for
  photoreal; clear and readable for animation).
- **Photoreal only, a camera someone could hold**: for handheld shots, name the small natural movement (slight
  sway, a small reframe as the subject moves). A perfectly smooth, floating camera reads as generated.
  Locked-off tripod shots stay locked.
- **Photoreal only, real imperfection, not low quality**: ask for real-world texture (scuffs, creases, uneven
  light), never for blur, low resolution or heavy grain. Grain and softness are added in finishing, the same
  for every clip.
- **Text the generator must not draw**, in every style: if a sign, price, phone number or caption is needed,
  leave it out of the prompt and put it on the clip's `Edit text` line, so it is added as real text in the
  edit.

## 5. Lint, save, push

```bash
mkdir -p video-projects/<project>/prompts
# write video-projects/<project>/prompts/NNN-<slug>.md (same NNN-slug as the script), then:
python <skill>/scripts/prompt_lint.py <that .md> --profile <name> --script <the script .md> \
       --export-json video-projects/<project>/prompts/NNN-<slug>.json
```

- Fix every `PROBLEM` and re-run. Judge each `warning`: fix it or keep it on purpose and say why in the clip's
  Review line. Stop after 3 rounds and report what still fails; never push prompts that fail the lint.
- `--script` compares each Narration with the script's Voiceover, word for word, so prompts can't drift from
  the narration.
- The JSON is only written when the lint passes, and uses the field names `flow-clip-qa` accepts through
  `--script`.
- Push to the owner's repo (`syndeeann/custom-claude-skills`; attach and clone it first if it isn't in the
  workspace):

```bash
git pull --rebase origin main
git add video-projects/<project>/prompts/
git commit -m "prompts(<project>): NNN <title>"
git push origin main
```

If the push is rejected, pull with rebase and push once more, then report the error. Never commit media files.

## 6. Other platforms

For anything other than Flow: search for that platform's current official prompting guide first, because
limits and features change. Then answer the adapter questions in `references/platforms.md` (clip length,
audio, reference images, negative-prompt field, aspect ratio) and write the same structure within those
limits. Run the lint with `--profile` as usual; it checks the wording rules, not platform limits, so check
those yourself.

## 7. Reply

Keep it short: where the prompts were saved, the platform and model suggested for each mode (for example,
ingredients need a model that supports them), the lint result and any warning kept on purpose, assumptions
made, and what to look at first when reviewing the generated clips (lips still, product matches the photo,
no text overlays, every clip in the same style). Say plainly that prompts raise the hit rate but clips still
need review: `flow-clip-qa` checks the raw clips, `video-editor` (Jaiman) cuts them and `video-finishing`
finishes the look and sound. Don't paste all the prompts unless asked; the file is
the deliverable.
