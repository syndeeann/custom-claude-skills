---
name: ai-prompt-expert
description: "Turns a video script or narration into clean, copy-ready generation prompts for Google Flow (Veo, Omni) and other AI video generators, built for real-life, photoreal footage. Every prompt shows what its narration line says, keeps on-screen people from lip-syncing an off-screen narrator, avoids repeated words, and follows the platform's own prompting guidance; a lint step checks all of it before the prompts are saved to video-projects/PROJECT/prompts/ in the owner's GitHub repo and pushed. Use it whenever the user wants prompts for Flow, Veo, Omni, Runway, Kling, Sora or any AI video tool, wants a script's visuals turned into prompts, or says a generated clip looks fake, shows the wrong picture, has subtitles or has people talking, in any project (Kwento: Kilabot, TikTok Shop ads, or a new one)."
metadata:
  category: content
  version: "1.0.0"
  media: video
  projects: [kwento-kilabot, tiktok-shop-ads]
---

# AI Prompt Expert

Writes the prompts that go into Google Flow and other AI video generators. A good prompt for real-life
footage does four jobs at once, and this skill checks all four:

1. **Shows what the narration says**: every phrase of the line has a picture, in the order it is heard.
2. **No dubbing**: when a narrator speaks, nobody on screen moves their lips.
3. **Clean wording**: no repeated words, no empty quality words, one action per clip, nothing a generator
   tends to fumble.
4. **Looks like real footage**: a real camera behaviour, a real light source, real textures.

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
- **Real-life look**: name a lens or a real camera behaviour, a real light source, and one or two textures. Skip
  empty quality words (8K, masterpiece, ultra-realistic).
- **No morphing or sequences**: no "turns into", no "then". Slow, simple, physical actions only.

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
no text overlays). Say plainly that prompts raise the hit rate but clips still need review, and that
`flow-clip-qa` is the next step once the clips exist. Don't paste all the prompts unless asked; the file is
the deliverable.
