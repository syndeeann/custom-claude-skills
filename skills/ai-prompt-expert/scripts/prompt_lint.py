#!/usr/bin/env python3
"""Lint AI-video generation prompts and export them as JSON.

    python scripts/prompt_lint.py <prompts.md> [--profile kwento-kilabot] [--script <script.md>]
                                  [--export-json <file>]

Reads a prompt file in the format of references/prompt-format.md and checks, per clip:

  - no dubbing: voiceover/hero prompts have no speech words or quoted text, and any visible person is framed
    away or has a closed mouth (stricter when the profile says faces: away-only); on-camera prompts quote the
    exact narration once, with a named speaker
  - narration coverage: every phrase in Covers is in the narration, the phrases cover most of its content
    words, and each mapped picture really appears in the prompt
  - clean wording: no repeated words (locked anchors, base look and closing line are exempt), no morphing,
    no sequences, no empty quality words, a lens/light/shot cue, no readable-text props
  - structure: closing line present, anchors pasted verbatim, length, allowed clip length, narration fits
  - with --script: each Narration equals the script's Voiceover for that clip, word for word

Profiles live in ../profiles/*.json; the named profile overrides generic.json.
Exit code: 0 = no problems (warnings may remain), 1 = problems, 2 = unusable input.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

PROFILES = Path(__file__).resolve().parent.parent / "profiles"

STOP = set("""
ang ng nang sa na ay at si ni kay mga ko mo niya namin natin nila kami tayo sila ako ikaw ka siya ito iyan iyon yan yon
pa din rin daw raw lang lamang ba po ho nga naman pala kasi kung kapag pag para pero o hindi akong kong mong kang niyang
naming nating di isa isang may mayroon meron ung yung noong nung sabi
the a an and or of to in on at is it i my me you he she we they his her for with but not this that was were be been
from into through over under behind beside near across along toward towards while where when than as by up down out off
about between its their there are has have had will would can could only just very also each both one two three
his hers them then so if no nor its own same such too any all some more most other another
""".split())

NONE_WORDS = {"", "-", "—", "–", "none", "(none)", "n/a", "(hero)"}

PEOPLE = re.compile(r"\b(man|men|woman|women|person|people|child|children|boy|girl|host|clerk|driver|guard|face|faces|"
                    r"figure|figures|shopper|customer|passenger|vendor|nurse|student|mother|father|grandmother|"
                    r"grandfather|neighbou?r|elder|priest|teenager|lady|gentleman|worker)\b", re.I)
AWAY = re.compile(r"(from behind|back to (the )?camera|backs? turned|turned away|silhouette|over-the-shoulder|"
                  r"over the shoulder|hands only|close-up of (her|his|their|the) hands?|face (out of frame|hidden|"
                  r"in shadow|turned away)|faceless|out of frame)", re.I)
CLOSED = re.compile(r"(\b(mouths?|lips?)\b[^.;]{0,30}\b(closed|shut|sealed|still|pressed|together)\b|"
                    r"\b(closed|shut|sealed|pressed)\b[^.;]{0,15}\b(mouths?|lips)\b)", re.I)
SPEECH = re.compile(r"\b(speak(s|ing)?|spoke(n)?|say|says|saying|said|talk(s|ed|ing)?|whisper(s|ed|ing)?|"
                    r"shout(s|ed|ing)?|sing(s|ing)?|sang|mutter(s|ed|ing)?|murmur(s|ed|ing)?|yell(s|ed|ing)?|"
                    r"lip-?sync\w*|dubb(ed|ing)|dialogue|conversation|voices?|voiced|voice-?over|"
                    r"narrat(or|ion|ed|es|ing|e)|chant(s|ed|ing)?)\b", re.I)
CAMERA_FACE = re.compile(r"(\b(looks?|looking|stares?|staring|gazes?|gazing|facing|turns?|eyes?)\b[^.;]{0,12}"
                         r"\b(at|into|to|toward|towards)\b[^.;]{0,6}\b(the )?(camera|lens|viewer)\b|to camera|eye contact)", re.I)
QUOTED = re.compile(r"[\"“]([^\"”]+)[\"”]")
MORPH = re.compile(r"\b(morph\w*|transform\w*|turns? into|changes? into|changing into|dissolv\w*|melts? into)\b", re.I)
SEQUENCE = re.compile(r"\b(then|after that|next|finally|afterwards)\b", re.I)
SPAM = re.compile(r"(masterpiece|\b8k\b|\b4k\b|ultra-?\s?realistic|hyper-?\s?realistic|hyper-?\s?detailed|"
                  r"trending on|award-winning|photorealistic|best quality)", re.I)
TEXTY = re.compile(r"\b(signs?|signage|labels?|lettering|written|writing|posters?|newspapers?|text|words|captions?|"
                   r"subtitles?|logos?|watermarks?|screens?|monitors?|billboards?)\b", re.I)
LENS = re.compile(r"(\b\d{2,3}\s?mm\b|\blens\b|film grain|\bgrain\b|anamorphic|handheld|depth of field|macro|"
                  r"locked-off|tripod|dolly|push-in|pull-back|\bpan\b|\btilt\b|steadicam)", re.I)
LIGHT = re.compile(r"\b(light\w*|lit|daylight|sunlight|sun|lamp|streetlight|fluorescent|tubes?|window|dusk|dawn|"
                   r"overcast|backlit|glow\w*|candle\w*|neon|moonlight|haze|fog\w*|shadow\w*)\b", re.I)
SIZE = re.compile(r"(extreme close-up|close-up|medium shot|wide shot|wide|overhead|low-angle|over-the-shoulder|"
                  r"macro|medium)", re.I)
MOVE = re.compile(r"(push-in|pull-back|slow pan|\bpan\b|\btilt\b|dolly|tracking|handheld|locked-off|crane|zoom)", re.I)
SPEAKER = re.compile(r"\b(says?|saying|speaks?|speaking|tells?|asks?)\b", re.I)
AMBIENT = re.compile(r"\b(ambient|ambience|room tone|sound of|sounds of)\b", re.I)


def load_profile(name: str) -> dict:
    def read(n: str) -> dict:
        p = Path(n) if n.endswith(".json") else PROFILES / f"{n}.json"
        if not p.exists():
            sys.exit(f"profile '{n}' not found (looked for {p})")
        return json.loads(p.read_text(encoding="utf-8"))

    prof = read("generic")
    if name != "generic":
        prof.update(read(name))
    return prof


def norm(text: str) -> str:
    return re.sub(r"[^\w]+", " ", text.lower().replace("’", "'")).strip()


def toks(text: str) -> list[str]:
    return re.findall(r"[\wñ'’-]+", text.lower().replace("’", "'"))


def stem(w: str) -> str:
    w = w.strip("'-")
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def content(text: str) -> list[str]:
    return [stem(w) for w in toks(text) if w.strip("'-") not in STOP and len(w.strip("'-")) >= 3
            and not w.strip("'-").isdigit()]


# ---------------------------------------------------------------------------------------------- parsing
CLIP_RE = re.compile(r"^###\s+Clip\s+(\d+)\b(.*)$", re.M)
FIELD_RE = re.compile(r"^-\s+\*\*([A-Za-z0-9 \-]+?):\*\*\s*(.*)$")


def parse_clips(md: str) -> list[dict]:
    parts = CLIP_RE.split(md)
    clips = []
    for i in range(1, len(parts), 3):
        n, head, body = int(parts[i]), parts[i + 1], parts[i + 2]
        body = re.split(r"^#{1,2}\s", body, maxsplit=1, flags=re.M)[0]
        fields: dict[str, str] = {}
        key = None
        for line in body.splitlines():
            m = FIELD_RE.match(line)
            if m:
                key = m.group(1).strip().lower()
                fields[key] = m.group(2).strip()
            elif key and line.strip() and not line.lstrip().startswith("#"):
                fields[key] += " " + line.strip()
        sec = re.search(r"\((\d+(?:\.\d+)?)\s*s\)", head)
        nar = fields.get("narration", fields.get("voiceover", "")).strip()
        clips.append({
            "n": n,
            "seconds": float(sec.group(1)) if sec else None,
            "label": re.sub(r"\(\d+(?:\.\d+)?\s*s\)", "", head).strip(" —–-:"),
            "narration": "" if nar.lower() in NONE_WORDS else nar,
            "mode": fields.get("mode", "").strip().lower(),
            "covers": fields.get("covers", ""),
            "prompt": fields.get("prompt", "").strip(),
            "review": fields.get("review", ""),
        })
    return clips


def header_value(md: str, key: str) -> str:
    m = re.search(rf"^-\s+\*\*{re.escape(key)}:\*\*\s*(.+)$", md, re.M | re.I)
    return m.group(1).strip() if m else ""


def section(md: str, title: str) -> str:
    m = re.search(rf"^##\s+{re.escape(title)}\s*$(.*?)(?=^##\s|\Z)", md, re.M | re.S | re.I)
    return m.group(1) if m else ""


def parse_anchors(md: str) -> list[dict]:
    out = []
    for line in section(md, "Look anchors").splitlines():
        m = FIELD_RE.match(line)
        if m and m.group(2).strip():
            text = m.group(2).strip()
            out.append({"name": m.group(1).strip(), "text": text, "person": bool(PEOPLE.search(text))})
    return out


def parse_covers(s: str) -> list[tuple[str, str]]:
    return [(a.strip(), b.strip()) for a, b in
            re.findall(r"[\"“]([^\"”]+)[\"”]\s*(?:→|->)\s*(.+?)(?=;\s*[\"“]|$)", s.strip())]


def strip_exempt(prompt: str, anchors: list[dict], prof: dict, quoted: bool) -> str:
    text = prompt
    spans = [a["text"] for a in anchors] + [prof.get("base_look", ""), prof.get("closing", "")]
    for s in sorted((x for x in spans if x), key=len, reverse=True):
        text = re.sub(re.escape(s.rstrip(".")), " ", text, flags=re.I)
    if quoted:
        text = QUOTED.sub(" ", text)
    return text


# ---------------------------------------------------------------------------------------------- checks
def lint(md: str, prof: dict, script_md: str | None) -> tuple[list[dict], list[str], list[str], list[str]]:
    clips = parse_clips(md)
    problems: list[str] = []
    warnings: list[str] = []
    rows: list[str] = []
    if not clips:
        return clips, ["no '### Clip NN' blocks found — see references/prompt-format.md"], warnings, rows

    if [c["n"] for c in clips] != list(range(1, len(clips) + 1)):
        problems.append(f"clips must be numbered 1..{len(clips)} in order, found {[c['n'] for c in clips]}")

    anchors = parse_anchors(md)
    if prof.get("needs_reference_images") and not section(md, "Reference images").strip():
        warnings.append("this profile expects reference images (e.g. the product photo) but '## Reference images' is empty")

    spw = float(prof["seconds_per_word"])
    closing = norm(prof.get("closing", ""))
    base = norm(prof.get("base_look", ""))
    pw = prof.get("prompt_words", {"min": 30, "warn_over": 120, "max": 200})
    modes = prof.get("modes", ["voiceover", "on-camera", "hero"])

    # script comparison
    if script_md is not None:
        script = parse_clips(script_md.replace("**Voiceover:**", "**Narration:**"))
        if len(script) != len(clips):
            problems.append(f"the script has {len(script)} clips but the prompt file has {len(clips)}")
        else:
            for s, c in zip(script, clips):
                if norm(s["narration"]) != norm(c["narration"]):
                    problems.append(f"clip {c['n']}: Narration differs from the script's Voiceover — "
                                    f'script: "{s["narration"]}" / prompts: "{c["narration"]}"')

    narr_bigrams: dict[str, set[int]] = defaultdict(set)
    prev_sig = None
    for c in clips:
        n, p, mode, nar = c["n"], c["prompt"], c["mode"], c["narration"]
        wc = len(p.split())
        rows.append(f"clip {n:>2}  {c['seconds'] or 0:>4.0f}s  {mode or '?':<10} prompt {wc:>3} words  narration {len(nar.split()):>2} words")

        # structure
        if c["seconds"] is None:
            problems.append(f"clip {n}: heading needs the clip length, e.g. '### Clip {n:02d} — HOOK (8s)'")
        elif prof.get("allowed_seconds") and int(c["seconds"]) not in prof["allowed_seconds"]:
            problems.append(f"clip {n}: {c['seconds']:.0f}s isn't an allowed length {prof['allowed_seconds']}")
        if mode not in modes:
            problems.append(f"clip {n}: Mode must be one of {modes}, found '{mode or 'missing'}'")
            continue
        if not p:
            problems.append(f"clip {n}: no Prompt")
            continue
        if mode == "hero" and nar:
            problems.append(f"clip {n}: a hero clip has no narration, but this one does")
        if mode != "hero" and not nar:
            problems.append(f"clip {n}: Mode is {mode} but there is no Narration")
        if nar and c["seconds"] and len(nar.split()) > c["seconds"] / spw:
            problems.append(f"clip {n}: narration is {len(nar.split())} words, more than fits {c['seconds']:.0f}s "
                            f"(about {c['seconds'] / spw:.0f})")

        # length and closing
        if wc < pw["min"]:
            warnings.append(f"clip {n}: prompt is only {wc} words — too thin to steer the generator")
        elif wc > pw["max"]:
            problems.append(f"clip {n}: prompt is {wc} words (max {pw['max']}) — long prompts dilute focus")
        elif wc > pw["warn_over"]:
            warnings.append(f"clip {n}: prompt is {wc} words — shorter prompts hold up better")
        if closing and not norm(p).endswith(closing):
            problems.append(f"clip {n}: the prompt must end with the profile's closing line: \"{prof['closing']}\"")
        if base and base not in norm(p):
            problems.append(f"clip {n}: the profile's base look is missing: \"{prof['base_look']}\"")

        # anchors pasted verbatim
        for a in anchors:
            if re.search(rf"\b{re.escape(a['name'])}\b", p, re.I) and norm(a["text"]) not in norm(p):
                problems.append(f"clip {n}: Look anchor '{a['name']}' must be pasted word for word")

        # repeated words
        body = strip_exempt(p, anchors, prof, quoted=(mode == "on-camera"))
        counts: dict[str, int] = defaultdict(int)
        for w in content(body):
            counts[w] += 1
        reps = sorted(w for w, k in counts.items() if k > 1)
        if reps:
            problems.append(f"clip {n}: repeated words in the prompt: {', '.join(reps)}")

        # realism and wording
        if MORPH.search(p):
            problems.append(f"clip {n}: morphing/transform wording ('{MORPH.search(p).group(0)}') — generators break on it")
        if SEQUENCE.search(body):
            warnings.append(f"clip {n}: sequence word '{SEQUENCE.search(body).group(0)}' — one action per clip")
        if SPAM.search(p):
            warnings.append(f"clip {n}: empty quality word '{SPAM.search(p).group(0)}' — use lens, light and texture instead")
        if not LENS.search(p):
            warnings.append(f"clip {n}: no lens or camera-behaviour cue")
        if not LIGHT.search(p):
            warnings.append(f"clip {n}: no light source or lighting cue")
        text_hit = TEXTY.search(strip_exempt(p, [], {"closing": prof.get("closing", "")}, quoted=False))
        if text_hit:
            warnings.append(f"clip {n}: '{text_hit.group(0)}' — readable text and screens often come out garbled; "
                            "avoid unless it is the product itself")
        if MOVE.search(" ".join(p.split()[:30])) or SIZE.search(" ".join(p.split()[:30])):
            sig = (frozenset(m.lower() for m in SIZE.findall(" ".join(p.split()[:30]))),
                   frozenset(m.lower() for m in MOVE.findall(" ".join(p.split()[:30]))))
            if prev_sig is not None and sig == prev_sig:
                warnings.append(f"clip {n}: same framing and camera move as clip {n - 1} — vary the shot")
            prev_sig = sig

        # people and speech
        person = bool(PEOPLE.search(p)) or any(a["person"] and norm(a["text"]) in norm(p) for a in anchors)
        if mode in ("voiceover", "hero"):
            if QUOTED.search(p):
                problems.append(f"clip {n}: quoted text in a {mode} prompt — generators read quotes as dialogue")
            sp = SPEECH.search(p)
            if sp:
                problems.append(f"clip {n}: speech word '{sp.group(0)}' in a {mode} prompt — describe silence "
                                "positively (closed lips, a quiet room, ambient sound) instead")
            if CAMERA_FACE.search(p):
                warnings.append(f"clip {n}: a face looking into the camera invites speech — look at an object instead")
            if person:
                away, closed = bool(AWAY.search(p)), bool(CLOSED.search(p))
                if prof.get("faces") == "away-only":
                    if not away:
                        problems.append(f"clip {n}: a person is visible but not framed from behind, in silhouette or "
                                        "by their hands — this profile never shows faces")
                elif not (away or closed):
                    problems.append(f"clip {n}: a person is visible with no closed-mouth cue and no face-away "
                                    "framing — the generator may lip-sync the narrator")
                elif closed and not away:
                    warnings.append(f"clip {n}: face visible with closed lips; framing from behind is safer against dubbing")
            if not AMBIENT.search(p):
                warnings.append(f"clip {n}: name the ambient sounds so the audio track is filled (e.g. 'ambient sound: ...')")
            if re.search(r"\bmusic\b|\bscore\b|\bsoundtrack\b", p, re.I):
                warnings.append(f"clip {n}: music in the prompt — add music when editing so the mix stays yours")
        else:  # on-camera
            quotes = QUOTED.findall(p)
            if not any(norm(q) == norm(nar) for q in quotes):
                problems.append(f"clip {n}: the on-camera prompt must quote the exact narration once")
            if len(quotes) > 1:
                warnings.append(f"clip {n}: more than one quoted line — only one person should speak")
            if not person:
                problems.append(f"clip {n}: an on-camera clip needs a visible, named speaker")
            elif not SPEAKER.search(re.sub(QUOTED, " ", p)):
                warnings.append(f"clip {n}: name the speaker next to the quoted line (e.g. 'the host says: \"...\"')")

        # narration coverage
        if nar and mode != "hero":
            entries = parse_covers(c["covers"])
            if not entries:
                problems.append(f"clip {n}: no Covers line (\"phrase\" → picture; ...) mapping the narration to pictures")
            else:
                nar_norm = " " + norm(nar) + " "
                covered: set[str] = set()
                for phrase, pic in entries:
                    if " " + norm(phrase) + " " not in nar_norm:
                        problems.append(f'clip {n}: Covers phrase "{phrase}" isn\'t in the narration')
                        continue
                    covered |= set(content(phrase))
                    kw = [w for w in toks(pic) if w.strip("'-") not in STOP and len(w.strip("'-")) >= 4]
                    if not kw:
                        problems.append(f'clip {n}: Covers picture for "{phrase}" is too vague to check')
                        continue
                    hit = sum(1 for w in kw if w[:5] in p.lower())
                    if hit / len(kw) < 0.5:
                        problems.append(f'clip {n}: the picture for "{phrase}" ({pic}) does not appear in the prompt')
                want = set(content(nar))
                if want:
                    frac = len(want & covered) / len(want)
                    if frac < 0.4:
                        problems.append(f"clip {n}: Covers maps only {frac:.0%} of the narration — most of the line has no picture")
                    elif frac < 0.6:
                        warnings.append(f"clip {n}: Covers maps {frac:.0%} of the narration — add the missing phrases")

        # repeated words in narration
        ws = toks(nar)
        for a, b in zip(ws, ws[1:]):
            if a == b:
                problems.append(f'clip {n}: narration repeats "{a} {a}"')
        cw = content(nar)
        for w in set(cw):
            if cw.count(w) > 1:
                problems.append(f'clip {n}: narration uses "{w}" twice in one line')
        for a, b in zip(cw, cw[1:]):
            narr_bigrams[f"{a} {b}"].add(n)
    for bg, ns in narr_bigrams.items():
        if len(ns) > 1:
            problems.append(f'narration phrase "{bg}" repeated in clips {sorted(ns)}')

    return clips, list(dict.fromkeys(problems)), list(dict.fromkeys(warnings)), rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prompts", type=Path, help="the prompts .md file")
    ap.add_argument("--profile", default="generic", help="profile name in ../profiles or a path to a .json")
    ap.add_argument("--script", type=Path, help="the storyteller script .md, to compare narration word for word")
    ap.add_argument("--export-json", type=Path, help="write the clips as a prompts.json-style file")
    args = ap.parse_args()

    if not args.prompts.exists():
        print(f"not found: {args.prompts}")
        return 2
    if args.script and not args.script.exists():
        print(f"not found: {args.script}")
        return 2
    md = args.prompts.read_text(encoding="utf-8")
    prof = load_profile(args.profile)
    script_md = args.script.read_text(encoding="utf-8") if args.script else None
    clips, problems, warnings, rows = lint(md, prof, script_md)
    if not clips:
        print("PROBLEM:", problems[0])
        return 2

    for r in rows:
        print(r)
    for m in problems:
        print("PROBLEM:", m)
    for m in warnings:
        print("warning:", m)
    print(f"lint ({prof['name']}): " + ("FAIL" if problems else "OK"))

    if args.export_json and not problems:
        title = re.search(r"^#\s+(.+)$", md, re.M)
        out = {
            "title": title.group(1).strip() if title else args.prompts.stem,
            "project": header_value(md, "Project"),
            "platform": header_value(md, "Platform") or prof.get("platform", ""),
            "aspect": header_value(md, "Aspect") or prof.get("aspect", ""),
            "clips": [{"n": c["n"], "seconds": c["seconds"], "mode": c["mode"], "hero": c["mode"] == "hero",
                       "voiceover": c["narration"], "visual": c["prompt"]} for c in clips],
        }
        args.export_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"exported {args.export_json}")
    elif args.export_json:
        print("not exported: fix the problems first")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
