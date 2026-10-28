# Prompt file format

One Markdown file per script, read by `scripts/prompt_lint.py`, so the clip blocks must follow this format.

## Where files go

```
video-projects/<project>/
  script/    NNN-<slug>.md            written by the storyteller
  prompts/   NNN-<slug>.md            written by this skill, same NNN-slug as its script
             NNN-<slug>.json          exported from the .md by the lint
```

## The file

```markdown
# <Title> — generation prompts

- **Project:** <project>
- **Script:** video-projects/<project>/script/NNN-<slug>.md
- **Platform:** Google Flow, Veo 3.1 Fast (or the model chosen per mode)
- **Aspect:** 9:16
- **Date:** 2026-10-28
- **Profile:** <profile name>

## Look anchors

- **<Name>:** the locked descriptor, copied word for word from the script. Pasted word for word into every
  prompt where this subject appears.

## Reference images

- **<role>:** the file to upload and what it is for (only when the platform takes reference images).

## Clips

### Clip 01 — HOOK (8s)
- **Narration:** the exact line from the script.
- **Mode:** voiceover
- **Covers:** "phrase of the line" → picture that shows it; "next phrase" → its picture
- **Prompt:** the whole paste-ready prompt, one paragraph, ending with the profile's closing line.
- **Review:** what to check on the generated clip (lips still, product matches the photo, no text overlay).
```

### Block rules

- Heading `### Clip NN — LABEL (Ns)`, numbered from 01 without gaps. The length must be one the profile allows.
- Fields use exactly `- **Narration:**`, `- **Mode:**`, `- **Covers:**`, `- **Prompt:**`, `- **Review:**`. A field may
  continue on following lines.
- **Mode** is `voiceover`, `on-camera` or `hero`. A hero clip writes `- **Narration:** none` and needs no Covers.
- **Covers** is a `;`-separated list of `"phrase" → picture`. Each phrase must appear in the narration, together
  the phrases must cover most of its content words, and each picture's key words must appear in the prompt.
- **Prompt** is a single paragraph. Locked anchors, the profile's `base_look` and the closing line are copied
  verbatim; everything else is written fresh and has no repeated words.
- **Anchors** are a bullet list under `## Look anchors`; the lint finds them in prompts by their exact text.

## The exported JSON

`python scripts/prompt_lint.py <file.md> --profile <name> --export-json <file.json>` writes:

```json
{
  "title": "...", "project": "...", "platform": "...", "aspect": "9:16",
  "clips": [
    {"n": 1, "seconds": 8, "mode": "voiceover", "hero": false, "voiceover": "...", "visual": "the prompt"}
  ]
}
```

The `clips` use the field names `flow-clip-qa` accepts through `--script`, with the prompt as the expected
visual.
