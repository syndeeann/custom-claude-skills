# Realism, no-dubbing and narration-to-picture

Read this before writing the first prompt in a conversation. It covers how to get footage that looks
filmed rather than generated, how to keep an on-screen character from "dubbing" the narrator, and how to
make every picture match its narration line.

## A. Look: real-life footage

Google's Veo guidance recommends a five-part structure: cinematography, subject, action, context, and style
and ambiance, and it says realism comes from naming the lens, the lighting, the film look and the mood. Build
each prompt in that order, then add audio and the closing line.

- **Cinematography**: shot size plus one real camera behaviour: locked-off tripod, handheld, slow push-in,
  slow pull-back, slow pan, low angle, overhead, over-the-shoulder. Add a lens or focus cue (35mm look,
  shallow depth of field, macro for small detail). Avoid drone swoops, whip pans and orbits; they are
  where generators lose coherence.
- **Subject**: the locked Look anchor, pasted verbatim, so the same person, place or product appears in
  every clip.
- **Action**: one slow, simple, physical action that could be filmed in one real take. Let the action fill
  the clip's length so the model has no empty time to fill with invented business.
- **Context**: where and when, in specific physical terms (a night bus terminal; a kitchen with a window over
  the sink), and the weather or time of day.
- **Light and look**: light from a source that exists in the scene, with its colour (green-tinted fluorescent
  tubes, low sun through a window, sodium streetlight haze, overcast daylight). Then one or two textures that
  real footage has and generated footage skips: dust, worn paint, fabric creases, flyaway hair, condensation,
  fingerprints, rain on glass, fine grain.
- **Skip empty quality words** such as 8K, masterpiece, ultra-realistic, hyper-detailed. They add no
  information. Concrete lens, light and texture cues do the work.
- **Describe, don't negate.** Google's guide recommends describing what you want rather than using "no"
  phrasing, and community testing finds that negative instructions about speech can backfire. Say "lips
  pressed together" and "a quiet room", not "no talking". The one exception is the closing line.

## B. No dubbing: nobody on screen speaks the narration

Generators were trained on footage where people on screen are usually talking, so a visible face, a
camera-facing look or an empty stretch of clip invites speech and lip movement. These steps keep the voice
off the screen. Items 5 and 6 come from community troubleshooting rather than Google's guide, so treat them
as good practice that you verify against your own results.

1. **Mode decides everything.** In `voiceover` and `hero` clips nobody on screen speaks. Only in `on-camera`
   clips does one named person speak, and the exact line goes in quotation marks with that speaker named.
2. **Frame faces away.** From behind, over the shoulder, in silhouette, hands only, or an object in close-up.
   When the profile says faces are never shown, this is mandatory.
3. **If a face must be visible**, write the mouth positively: lips pressed together, mouth closed and still,
   calm expression, eyes on an object and never into the camera.
4. **No speech words in the prompt** for voiceover clips: no says, talking, whispering, voice, dialogue,
   conversation, and no quoted text anywhere. Quoted text is read as dialogue.
5. **Fill the audio track with named ambient sound**: two or three specific sounds (rain on glass, a fridge
   hum, a hook creaking). An empty audio description invites invented dialogue.
6. **Reference images with open mouths or expressive faces** push the model toward speech. Choose neutral
   closed-mouth references.
7. **If lips move anyway**, regenerate with the face further away or turned, then fall back to a hands-only
   or object shot. Don't try to fix it by adding "no talking".

## C. The picture must match the narration

Each clip carries a `Covers` line that maps every phrase of the narration to a picture, and the lint checks
that the mapped pictures really appear in the prompt.

- **Concrete words → the literal thing.** "Umbrella" is the umbrella, "ledger" is the ledger.
- **Abstract words → the nearest visible evidence.** "Died six years ago" becomes thick dust and a yellowed tag;
  "he was afraid" becomes a hand that stops mid-reach. Never rely on a face to carry an emotion.
- **Time** becomes light or a simple cue (first light, rain, a streetlight coming on), not a readable clock.
- **Numbers** become countable objects only up to about three; above that, show one object and let the
  narration carry the number.
- **Order**: pictures appear in the order the phrases are heard. For a two-sentence line, a timestamped
  split (the first half of the clip, then the second half) with one image each can help, but keep it to
  one continuous shot and one location.
- **Don't contradict the line.** Extra background is fine; anything that changes the meaning is not.
- **Nothing visible that the line doesn't earn**, if it would distract from the line's point.

## D. Things generators fumble, and what to do instead

| Problem | Instead |
|---|---|
| Extra or merged fingers, fiddly hand work | Medium or wide shot, slow single grip, hands partly out of frame, object held steady |
| Faces drift or melt between clips | Fewer faces, from behind, locked anchors, reference images |
| Garbled signs, labels, screens | Avoid readable text; if a name or number must appear, add it in editing |
| Product changes shape | Use the listing photo as a reference image, one slow action, tight steady shot |
| Subtitles or captions appear | The closing line; a negative-prompt field if the interface has one; avoid screens, interviews and podcast-style framing |
| Unwanted speech or lip movement | Section B |
| Clocks and exact times wrong | Light cues instead of a readable clock |
| Crowds look uncanny | Empty space, a single figure, distant silhouettes |
| Liquids, tearing and pouring look wrong | Slow simple version, or cut to the result |
| Clips don't match each other | Same anchors, same light direction and time of day, a reference image, or first-and-last-frame linking |

## E. Fix ladder when a clip comes back wrong

Cheapest first: regenerate once unchanged → simplify the prompt (fewer elements, one action) → reframe (move
the camera away, turn the face away) → switch to a reference image or first-frame input → change model or
quality tier → change the shot to something the generator does reliably, and have the narration carry the
detail.
