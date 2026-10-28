# Editing rules

## A. What a seamless video means
- All clips share one size, frame rate and audio format (the build enforces this), so no join jumps or changes speed.
- Cuts land on the end of an idea. Never cut in the middle of a word or a sentence.
- Audio fades 25 ms at each joint (profile `audio_fade_ms`). Longer fades make a dip; shorter ones can pop.
- A clip's first or last half-second is often unstable in generated video (settling, morphing, a freeze). Trim
  it: raise `start` or lower `end` by 0.2 to 0.5 s in `edit.json`.
- Do not stretch or slow a clip to fill time. If a clip is short, say so and ask for a longer take.

## B. Voice-over sync
- Each narration line belongs to the clip with the same number in the script. It starts after the clip begins
  and finishes before the picture moves on (profile `tail_over_s` is the most it may overrun).
- The picture shows what the line says. If clip 4's line is about the door, clip 4 shows the door.
- Fix order: shift `--vo-offset`; trim a clip; use a different take; ask Marites to shorten the line; last, re-do
  the voice-over. A line that is too long for its clip is a script fault, not an editing one.
- On-screen people never move their lips to the narration. If a clip shows someone speaking, that clip fails the
  quality check; ask for a new clip.

## C. Reading the check
| Message | Meaning | Usual fix |
|---|---|---|
| black frames | a gap or a clip that did not load | check the file, rebuild |
| audio/video lengths differ | sync will drift | rebuild; do not re-mux by hand |
| narration silent in its clip | the voice-over is shifted or missing a line | `--vo-offset`, or a missing line |
| narration ends after the picture moves on | the line is late or too long | shift earlier, or shorten the line |
| speech crosses a joint (warning) | a line runs over a cut | fine if the cut is inside a long sentence on purpose, else move the cut |
| picture frozen (warning) | stalled or looped clip | trim or replace the clip |

## D. Hand-off
The final video, `edit.json`, the check output and any warnings go to the owner. Quality check by Perpekto
(`flow-clip-qa`) comes before posting; the portfolio update by Chelsea (`portfolio-updater`) comes after.
