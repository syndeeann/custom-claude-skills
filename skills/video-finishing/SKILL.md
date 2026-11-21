---
name: video-finishing
description: "Finishing pass for an AI-generated video in any style (photoreal, anime, cartoon, 3D animation, claymation), after Jaiman (video-editor) has cut it: matches and grades every shot, adds the style's texture (grain only for real-life footage), sound design, real captions, prices, logos and end cards, sets loudness, and hands the final to Perpekto. Use it whenever the owner wants a cut video to look and sound finished, says a video looks plastic, fake, flat or too clean, or asks for captions, an end card or sound effects."
metadata:
  title: Video Finishing
  role: Colourist and sound designer
  order: 7
  summary: "Gives a cut video its final look and sound for its style: grade, texture, sound design, real captions and end cards."
  responsibilities:
    - "Matches and grades every shot to the video's Style card"
    - "Adds grain and softness only to real-life footage, and keeps anime and cartoon lines crisp"
    - "Builds the sound bed and foley so no scene is silent or too clean"
    - "Adds captions, prices, phone numbers, logos and end cards as real text"
    - "Keeps Flow's watermark and provenance data, and hands the final to Perpekto"
  category: production
  version: "1.0.0"
  media: video
  projects: []
---

# Video finishing

Raw generated clips rarely look finished. Real-life clips come out too sharp, too clean and too saturated;
animated clips can come out with uneven colour, flicker or a style that wobbles between shots; and both
often come with thin or overly tidy sound. Jaiman (video-editor) puts the clips in story order, trims them,
joins them and syncs the voice-over. This skill takes that cut and gives every shot the same finish for its
style, adds the sound design and the on-screen text, and hands the result to Perpekto (flow-clip-qa). It does
not write prompts, generate clips, re-order the story or post anything.

No finishing pass makes every clip perfect. A melted face, an off-model character or a wrong product needs a
regenerate, not a grade. Fix what can be fixed and send the rest back with a clear reason.

## 1. Inputs
- Jaiman's final cut and its `edit.json` (clip order, trims), plus the voice-over and music if they are
  separate files. If there is no cut yet, run Jaiman first; don't assemble here.
- The script / `prompts.json` (narration, hero clips, `Edit text` lines) and the project's `bible.md`
  (**Style card**, palette, frame rate, aspect). The style decides section 2. If no Style card exists, ask
  which style the video is before finishing.
- Logo and end-card files, and the real figures (prices, phone numbers) from the script or listing.
- Perpekto's report on the raw clips, if one exists.
- Work on copies; never edit the originals. Prefer fixing in the edit over re-prompting: a small trim or
  cutaway goes back to Jaiman's `edit.json`.

## 2. Look pass, by style
Apply the same settings to every shot so the video feels like one camera or one animation. Start subtle;
overdoing it looks processed.

**Every style, in this order:**
1. **Upscale** with the generator's own upscale if it has one (check in the app). Never lower the quality on
   purpose to hide flaws: viewers read blurry, low-resolution video as suspicious.
2. **Match shots:** exposure, white balance and colour across clips (`eq`, `colorbalance`); `deflicker` for
   luminance flicker.
3. **Grade** toward the Style card's palette (a LUT at about 50 to 70 percent strength, never 100).

**Then the texture for the style:**

| Style | Softness | Texture | Notes |
|---|---|---|---|
| Photoreal | very light blur (`gblur` sigma 0.3 to 0.6) | fine temporal grain last (`noise=alls=4..8:allf=t`), optional faint vignette | slightly lower saturation, softer highlights |
| 3D animated | none, or the lightest blur only if edges look harsh | none, or very faint grain | keep colours rich; don't desaturate toward film |
| Anime / 2D cel / 2D cartoon | **none** (blur softens line art) | **none** | keep lines crisp and fills flat; fix colour flicker inside shapes with `deflicker` or by regrading |
| Claymation / stop-motion | none | light grain is fine | don't smooth the stepped motion; it's part of the style |
| Other media | per the medium | a paper or canvas texture only if the Style card asks | |

Tested photoreal chain (with a quiet ambience bed under the existing mix):
```bash
ffmpeg -i cut.mp4 -i ambience.wav -filter_complex \
 "[0:v]deflicker=size=5,gblur=sigma=0.4,eq=saturation=0.92:contrast=1.03:gamma=0.98,vignette=angle=PI/5,noise=alls=6:allf=t,format=yuv420p[v];\
  [0:a][1:a]amix=inputs=2:duration=first:weights=1 0.35,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
 -map "[v]" -map "[a]" -c:v libx264 -crf 18 -preset veryfast -r 24 -c:a aac -b:a 192k -movflags +faststart cut_fin.mp4
```
For anime and cartoon, drop `gblur`, `vignette` and `noise`, and keep only the matching and grade steps. Add
`lut3d=file=look.cube` (blended with the original for partial strength) when the project has a LUT. Keep the
frame rate Jaiman delivered.

## 3. Sound design (half of what makes it land)
Silent or too-clean sound gives AI video away in every style. Keep Jaiman's voice-over timing exactly as it
is; only add under and around it.
- **Ambience bed / room tone** under every scene, continuous across cuts within one location.
- **Foley matched to the picture.** Real-life: true sounds (a hard object gets a hard sound, footsteps match
  the surface). Cartoon and 3D animated: the style's own sounds (boings, whooshes, exaggerated steps) when the
  Style card calls for them. Anime: crisp, punchy effects and clean ambience.
- **Music:** licensed, owned, or generated by a tool whose terms allow the use. Never a copyrighted track
  without a licence. Duck it under the voice-over.
- **Loudness:** after the new layers, normalise the final mix again (`loudnorm`, about I=-14 LUFS, TP=-1.5
  dB is a common social-video target; follow the profile or the platform's current spec if it differs).
- Flag any generated speech that shouldn't be there (lips moving to a narrator, invented voices) to Jaiman
  for an audio-only cut; never patch a word.

## 4. Text, logos, end cards
Generators garble text, so all readable text is added here from the clips' `Edit text` lines: captions
(`subtitles` / `ass`), prices, phone numbers, logos, end cards. Match the font and colour to the style (clean
type for real-life, a playful rounded font for cartoons when the Style card fits). Use the real logo file and
colours, keep text off faces and off the logo, and check every number against the script, listing or owner.

## 5. Export and hand-off
- H.264 + AAC, the project's aspect and resolution, `-pix_fmt yuv420p`, `+faststart`. Write to a temporary
  `.mp4` name and rename only when ffmpeg exits 0.
- **Keep provenance:** don't strip C2PA / Content Credentials metadata or try to remove or hide SynthID or
  other watermarks. Platforms read them to label AI content, and the owner discloses AI use anyway.
- Save the finishing settings (style, grade, texture, sound layers, text list) as
  `video-projects/<project>/edit/NNN-<slug>-finish.json`, next to Jaiman's cut list. Media stays out of git.
- Run Perpekto (flow-clip-qa) on the finished file with its cut list and the Style card. Fix and re-check at
  most twice; never call a failed video ready.

## 6. Reply
The QA verdict, the style it was finished for, what was changed, which clips need regenerating and why,
where the final is, and any assumption made. Nothing is posted: the owner reviews and approves first.
