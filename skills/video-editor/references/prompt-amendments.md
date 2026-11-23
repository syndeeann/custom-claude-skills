# Prompt amendments from QA results

Use when `flow-clip-qa` (Perpekto) fails a generated clip and editing cannot fix it. Give the prompt writer the
clip, the failure, and the wording below. Keep the rest of the prompt unchanged so the face, scene and framing
stay the same.

| QA failure | Amend the prompt with |
|---|---|
| Line cut off, speech runs to the clip end | Shorten the line; add "She finishes speaking by about six seconds, then smiles and holds still." |
| A word is dropped (e.g. "for") or wrong | Put the exact line in quotes, and add "She says it exactly like that, word for word, with no words added or left out." |
| Stutter, repeat or restart | Add "She says it smoothly, clearly and only once, with no repeated words, no stuttering and no restarts." |
| Price garbled, rushed or said in a different form | One price per clip. Write the exact spoken form the owner gave in the line ("one thousand nine hundred fifty pesos per day"), add "She says every number in full, slowly and clearly." Never change the form on your own. |
| Coined or brand word mispronounced | Spell it as plain words ("unlimited mileage"); keep the brand spelling for on-screen text only. |
| Face differs from the reference | Add "Keep her face, hair and clothes identical to the attached photo." |
| Text, subtitles, watermark in the picture | Add "No subtitles, no text, no watermarks, no logos." |
| Mouth moves while an off-screen voice plays | Add "Nobody on screen speaks; lips stay closed." |
| Audio generation failed | Retry the same prompt once; credits are refunded. |

Rules: spoken lines are exact, short and in one take; one idea per clip; the on-screen caption carries brand
spellings; never change business facts (names, prices, numbers, contact details).
