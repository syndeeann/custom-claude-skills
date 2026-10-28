# Platform notes

Generators change often. Anything here that bears on a decision should be re-checked against the source
before you rely on it; the dates say when it was last read.

## Google Flow (checked 2026-10-28)

From Google's Flow Help page on models and supported features:

| Model | Clip lengths | Notes |
|---|---|---|
| Veo 3.1 Lite | 4, 6, 8 s (8 s only for ingredients and extensions) | text, frames and ingredients to video; extending supported |
| Veo 3.1 Fast | 4, 6, 8 s (8 s only for ingredients) | text, frames and ingredients to video |
| Veo 3.1 Quality | 4, 6, 8 s | text and frames to video; **no ingredients** |
| Gemini Omni Flash 1.1 | 4, 6, 8, 10 s | text, frames and ingredients to video; video-to-video editing up to 10 s |

All listed models support both aspect ratios (9:16 vertical and 16:9). The page doesn't say how many
reference images are allowed or describe audio, so check in the app.

What follows for the work:

- **Product or character that must match a photo**: use ingredients-to-video with the photo as the reference
  image, on Veo 3.1 Fast or Lite or on Omni. Quality can't take ingredients. Refer to the image by its role
  in the prompt ("the blender in the reference").
- **Linking two clips smoothly**: frames-to-video with a first and last frame.
- **Audio**: Google's Veo guide writes dialogue in quotation marks with the speaker named, sound effects as
  SFX, and background sound as ambient. For voiceover clips, put only ambient sound in the prompt.
- **Timestamp prompting**: Google's guide describes splitting one generation into timed segments, each with
  its own shot, action or sound. Use it for a two-sentence narration only, keeping one continuous shot.
- **Prompt length**: short, structured prompts hold up best. The lint warns above the profile's word limit.

Sources: [Ultimate prompting guide for Veo 3.1](https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1),
[Learn about Flow models and supported features](https://support.google.com/flow/answer/16352836).

## Any other platform (Runway, Kling, Sora, Pika, Luma, Hailuo...)

Don't write from memory. Search for the platform's current official prompt guide and answer these questions
first; the answers decide what the prompt can say:

| Question | Why it matters |
|---|---|
| Longest clip, and which lengths are allowed? | decides the narration length per clip |
| Does it generate audio? | if not, drop the audio sentence and add sound in editing |
| Does it take reference images, first/last frames, or character references? | decides how products and people stay consistent |
| Is there a separate negative-prompt field? | put the exclusions there instead of the closing line |
| Which aspect ratios and resolutions? | vertical 9:16 for Reels, Shorts and TikTok |
| How long a prompt does it read well? | trim to fit; the lint's word limits are a Flow-era default |
| Does the guide name a prompt structure? | follow the platform's own order if it differs |

Then write the same ingredients (shot and lens, locked anchor, one action, setting, light and look, closing)
in the platform's preferred order. The lint checks wording rules, not platform limits, so check those
yourself, and say in the reply which platform and model each prompt was written for.
