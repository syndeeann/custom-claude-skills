# Flow clip QA checklist

The full checklist, merged from the Kwento: Kilabot and TikTok Shop ads workflows. `flow_qa.py` does
part A by itself; part B is your own look at the sheets; part C turns failures into fixes.

## Contents
- A. Automatic checks (what `flow_qa.py` decides)
- B. Visual review (what you decide from the sheets)
- C. Judging warnings
- D. Fixing failures — cheapest fix first
- E. Verdict and report

---

## A. Automatic checks

**Problems — the clip or video fails:**

| Check | Clips mode | Run mode (assembled final) |
|---|---|---|
| Readable video, audio track present | ✓ | ✓ |
| Orientation / exact resolution / codecs | orientation | resolution + H.264/AAC |
| Black frames in the middle of a clip | ✓ (edges are a warning) | ✓ |
| Narrated clip with little or no speech heard | ✓ | ✓ |
| Speech runs into the last 0.3 s (line cut off) | ✓ | — |
| Same file twice / two clips that look identical | ✓ | ✓ |
| Clips missing, extra, repeated or out of order in the cut | — | ✓ |
| A segment's audio doesn't match its own source clip | — | ✓ |
| Voice-over out of sync (> profile `sync_ms`, 60 ms by default) | — | ✓ |
| Video and audio lengths differ by > 0.4 s | — | ✓ |
| Content shorter than profile `final.min_content_s` | — | ✓ |
| Repeated words in the script (see below) | ✓ | ✓ |

Repeated words (problems): the same word twice in a row ("ring ring", "papalapit nang papalapit"); a
content word twice in one clip's line ("Walang gumagalaw. Walang tumitingin."); the same two-word phrase
in two different clips. Warning: a content word in 3+ clips. Small Tagalog/English function words
(ang, ng, sa, na, ko, the, a …) are ignored; add more with the profile's `extra_stopwords`.

**Warnings — a judgment call (section C):** frozen picture, black frames at a clip edge, audio clipping,
total silence inside a line, speech much longer than the line, speech heard in a clip that should be
silent, no lead-in before the first word, clip length outside the profile range, fps mismatch, file over
the size cap, script/clip count mismatch.

What the script cannot hear: the exact words. There is no speech recognition, so it catches missing,
cut, swapped and padded lines by timing and energy — not a single wrong word. When the user cares about
exact wording, say so in the report and suggest they listen to the flagged clips.

## B. Visual review

Read `check/qc_sheet.png` (frames from every clip, labelled with the clip number) and, when it exists,
`check/lip_sheet.png` (4 larger frames per clip that shows people, labelled N.1–N.4). Zoom in with a
second Read of individual frames (`check/qc_NNa.png`, `check/lip_NNk.png`) when a tile is too small to
judge. Work through the profile's checklist, which `qa.json → visual_review.checklist` repeats. The core
items, for every project:

1. **Right scene.** Each clip shows what its prompt asked for. With a script, compare with
   `expected_visuals`; without one, judge whether the clip is coherent and on-brief.
2. **No text.** No letters, subtitles, captions, watermarks or stray logos. Flow loves to draw signs,
   screens and labels — look at backgrounds too.
3. **Faces.** Natural, and the same from the first frame to the last — no melting, warping, extra eyes.
4. **Hands.** Five fingers, plausible grip, nothing fused through an object.
5. **Objects.** Keep their shape, colour and size; nothing morphs, appears or vanishes.
6. **Consistency across clips.** A recurring character keeps the same face, hair and clothes.
7. **No redundant clip.** No two clips are the same shot; order matches the story.
8. **Lip check — no dubbing.** In the lip sheet, compare the mouth across N.1–N.4. While a voice-over
   plays, only the person who is actually the speaker may move their lips, in sync. An off-screen
   narrator means nobody on screen moves their mouth. Mouth opening, closing or changing shape across
   the four frames = FAIL for that clip. A mouth that stays the same shape is fine.
9. **Project rules** from the profile — e.g. for product ads, the product must match the listing photo
   in every clip it appears; a wrong-looking product is a fail.

Be honest about what frames can't show: motion between samples (a one-frame glitch, unnatural walking).
If something looks borderline, call it out as "check by watching" rather than passing it silently.

## C. Judging warnings

| Warning | Pass when | Otherwise |
|---|---|---|
| Frozen picture ≥ 2.5 s | it is a deliberate still shot (a product hero, a static wide) | trim or regenerate |
| Black frames at a clip edge | they will be trimmed in the edit | trim before assembling |
| Silence inside the line | the script has a deliberate pause there | a word was dropped → regenerate |
| Speech much longer than the line | the line is slow on purpose | Flow repeated or added words → regenerate |
| Speech in a clip that should be silent | it is ambient sound, not words | regenerate without voices |
| No lead-in before the first word | the first word sounds complete | regenerate with a half-second pause |
| Audio clipping | barely over, sounds clean | lower the gain when assembling |
| File over the size cap | — | re-encode at a lower bitrate |
| Clip length outside range | — | usually harmless; check the edit still fits |

Record how you judged each warning in the report.

## D. Fixing failures — cheapest fix first

Regenerating in Flow costs credits, so try free fixes first:

1. **Re-cut (free):** out of sync, audio doesn't match its clip, clips out of order, missing/extra clip
   in the cut → fix the cut list and re-assemble.
2. **Re-download (free):** same file twice, identical-looking clips → a download mix-up; fetch the right
   clip from the Flow project (identify it by its spoken line).
3. **Trim (free):** black/frozen frames, a glitch or a bad frame at a clip edge → trim it out, as long
   as no spoken word is cut and the video stays long enough.
4. **Rewrite the line (cheap):** repeated words → rewrite that clip's line with the same meaning and
   word count, then regenerate only that clip.
5. **Regenerate (costs credits):** line cut off or missing, garbled face or hands, morphing object or
   product, text in the picture, wrong scene, dubbing, a glitch in the middle of a clip → regenerate
   only that clip, with the prompt changed to prevent the failure (e.g. "Absolutely no text …",
   "Anyone on screen keeps their lips closed", a shorter line for a cut-off line, a simpler hand action).
   The same weakness is usually in other prompts too — fix the rule everywhere before generating more.

Re-run `flow_qa.py` after every fix. Stop after 2 fix rounds and report what still fails.

## E. Verdict and report

- **PASS** only when the automatic checks passed, every warning was judged acceptable, and the visual
  review found nothing. **FAIL** otherwise — a clip that failed QC is never described as ready.
- Fill in the "Visual review" line of `qa_report.md` (pass/fail and notes per clip) so the file is a
  complete record.
- Tell the user: overall verdict; each failing clip with what is wrong and the cheapest fix; warnings and
  how you judged them; what couldn't be checked (exact words, motion between frames).
