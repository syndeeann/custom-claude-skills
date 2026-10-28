#!/usr/bin/env python3
"""Lint a storyteller script and export its clips as JSON.

    python scripts/script_lint.py <script.md> [--profile kwento-kilabot] [--export-json <file>]

Reads the clip blocks of a script written in the format in references/script-format.md and checks:

  - structure: clips numbered 1..n, each with a visual; non-fiction and ads have a Fact sheet
  - voiceover length against clip length and the profile's pace (too long = cut off, too short = padded)
  - the first sentence of the hook is short
  - clichés and forbidden phrases from the profile's "avoid" list
  - repeated words: twice in a row, twice in one line, the same two-word phrase in two clips
  - the same visual used for two clips
  - total runtime against the profile's total_seconds, when it has one

Profiles live in ../profiles/*.json; the named profile overrides generic.json ("avoid" lists are combined).
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
""".split())

NONE_WORDS = {"", "-", "—", "–", "none", "(none)", "n/a", "silence", "(hero)"}


def load_profile(name: str) -> dict:
    def read(n: str) -> dict:
        p = Path(n) if n.endswith(".json") else PROFILES / f"{n}.json"
        if not p.exists():
            sys.exit(f"profile '{n}' not found (looked for {p})")
        return json.loads(p.read_text(encoding="utf-8"))

    prof = read("generic")
    if name != "generic":
        extra = read(name)
        avoid = list(prof.get("avoid", [])) + list(extra.get("avoid", []))
        prof.update(extra)
        prof["avoid"] = list(dict.fromkeys(avoid))
    return prof


def words(text: str) -> list[str]:
    return [w for w in re.findall(r"[\wñÑ'’-]+", text.lower().replace("’", "'")) if w.strip("'-")]


def content(ws: list[str]) -> list[str]:
    return [w for w in ws if w not in STOP and len(w) >= 3]


# ---------------------------------------------------------------------------------------------- parsing
CLIP_RE = re.compile(r"^###\s+Clip\s+(\d+)\b(.*)$", re.M)
FIELD_RE = re.compile(r"^-\s+\*\*([A-Za-z ]+?):\*\*\s*(.*)$")


def parse_clips(md: str, default_seconds: float) -> list[dict]:
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
        label = re.sub(r"\(\d+(?:\.\d+)?\s*s\)", "", head).strip(" —–-:")
        vo = fields.get("voiceover", "").strip()
        clips.append({
            "n": n,
            "seconds": float(sec.group(1)) if sec else default_seconds,
            "label": label,
            "beat": fields.get("beat", ""),
            "voiceover": "" if vo.lower() in NONE_WORDS else vo,
            "visual": fields.get("visual", ""),
            "hero": fields.get("hero", "").lower().startswith(("y", "t")),
        })
    return clips


def header_value(md: str, key: str) -> str:
    m = re.search(rf"^-\s+\*\*{re.escape(key)}:\*\*\s*(.+)$", md, re.M | re.I)
    return m.group(1).strip() if m else ""


# ---------------------------------------------------------------------------------------------- checks
def lint(md: str, prof: dict) -> tuple[list[dict], list[str], list[str], list[str]]:
    clips = parse_clips(md, float(prof["clip_seconds"]))
    problems: list[str] = []
    warnings: list[str] = []
    rows: list[str] = []

    if not clips:
        return clips, ["no '### Clip NN' blocks found — see references/script-format.md"], warnings, rows

    if [c["n"] for c in clips] != list(range(1, len(clips) + 1)):
        problems.append(f"clips must be numbered 1..{len(clips)} in order, found {[c['n'] for c in clips]}")

    # Fact sheet for anything that makes checkable claims
    kind = header_value(md, "Type").lower()
    if kind.startswith(("non", "ad")):
        sheet = re.search(r"^##\s+Fact sheet\s*$(.*?)(?=^##\s|\Z)", md, re.M | re.S | re.I)
        if not sheet or not sheet.group(1).strip():
            problems.append("Type is Non-fiction/Ad but there is no filled-in '## Fact sheet'")
        elif kind.startswith("non") and "http" not in sheet.group(1):
            warnings.append("Fact sheet has no source URLs")

    spw = float(prof["seconds_per_word"])
    lo, hi = prof.get("fill", [0.55, 0.9])
    for c in clips:
        n = c["n"]
        wc = len(re.findall(r"[\w'’-]+", c["voiceover"]))
        cap = c["seconds"] / spw
        if not c["visual"]:
            problems.append(f"clip {n}: no Visual prompt")
        elif len(c["visual"].split()) < 15:
            warnings.append(f"clip {n}: visual prompt is only {len(c['visual'].split())} words — too vague to generate")
        if not c["beat"]:
            warnings.append(f"clip {n}: no Beat (what new thing does this clip deliver?)")
        if not c["voiceover"]:
            if not c["hero"]:
                warnings.append(f"clip {n}: no voiceover and not marked '- **Hero:** yes'")
            rows.append(f"clip {n:>2}  {c['seconds']:>4.0f}s  silent")
            continue
        fill = wc / cap
        rows.append(f"clip {n:>2}  {c['seconds']:>4.0f}s  {wc:>3} words  {fill:>4.0%} of {cap:.0f}-word capacity")
        if wc > cap:
            problems.append(f"clip {n}: {wc} words won't fit {c['seconds']:.0f}s (about {cap:.0f} at this pace) — it will be cut off")
        elif fill > hi:
            warnings.append(f"clip {n}: {wc} words fills {fill:.0%} of the clip — no room to breathe, aim for {hi:.0%} or less")
        elif fill < lo:
            warnings.append(f"clip {n}: {wc} words fills only {fill:.0%} of the clip — add substance or let it be a deliberate hold")

    # hook
    first = next((c for c in clips if c["voiceover"]), None)
    if first:
        sentence = re.split(r"(?<=[.!?…])\s", first["voiceover"], maxsplit=1)[0]
        limit = int(prof.get("hook_first_sentence_max_words", 14))
        if len(words(sentence)) > limit:
            warnings.append(f'hook: first sentence is {len(words(sentence))} words (limit {limit}) — "{sentence}"')

    # clichés and forbidden phrases
    for c in clips:
        low = c["voiceover"].lower().replace("’", "'")
        for phrase in prof.get("avoid", []):
            if phrase.lower() in low:
                problems.append(f'clip {c["n"]}: "{phrase}" is on the avoid list — rewrite it')

    # repeated words
    bigram_at: dict[str, set[int]] = defaultdict(set)
    word_at: dict[str, set[int]] = defaultdict(set)
    for c in clips:
        n, ws = c["n"], words(c["voiceover"])
        for a, b in zip(ws, ws[1:]):
            if a == b:
                problems.append(f'clip {n}: "{a} {a}" — same word twice in a row')
        seen: set[str] = set()
        cw = content(ws)
        for w in cw:
            if w in seen:
                problems.append(f'clip {n}: "{w}" used twice in one line')
            seen.add(w)
            word_at[w].add(n)
        for a, b in zip(cw, cw[1:]):
            bigram_at[f"{a} {b}"].add(n)
    for bg, ns in bigram_at.items():
        if len(ns) > 1:
            problems.append(f'"{bg}" repeated in clips {sorted(ns)}')
    for w, ns in word_at.items():
        if len(ns) >= 3:
            warnings.append(f'"{w}" appears in clips {sorted(ns)} — vary it unless it is the one deliberate callback')

    # repeated shots
    seen_visual: dict[str, int] = {}
    for c in clips:
        key = re.sub(r"\W+", " ", c["visual"].lower()).strip()
        if key and key in seen_visual:
            problems.append(f"clip {c['n']}: same visual as clip {seen_visual[key]}")
        seen_visual.setdefault(key, c["n"])

    # runtime
    total = sum(c["seconds"] for c in clips)
    rows.append(f"total   {total:.0f}s across {len(clips)} clips")
    span = prof.get("total_seconds")
    if span:
        if total < span["min"]:
            problems.append(f"runtime {total:.0f}s is under the profile's minimum of {span['min']}s")
        elif total > span["max"]:
            problems.append(f"runtime {total:.0f}s is over the profile's maximum of {span['max']}s")

    return clips, list(dict.fromkeys(problems)), list(dict.fromkeys(warnings)), rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path, help="the script .md file")
    ap.add_argument("--profile", default="generic", help="profile name in ../profiles or a path to a .json")
    ap.add_argument("--export-json", type=Path, help="write the clips as a prompts.json-style file")
    args = ap.parse_args()

    if not args.script.exists():
        print(f"not found: {args.script}")
        return 2
    md = args.script.read_text(encoding="utf-8")
    prof = load_profile(args.profile)
    clips, problems, warnings, rows = lint(md, prof)
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
            "title": title.group(1).strip() if title else args.script.stem,
            "project": header_value(md, "Project"),
            "language": header_value(md, "Language"),
            "clips": clips,
        }
        args.export_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"exported {args.export_json}")
    elif args.export_json:
        print("not exported: fix the problems first")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
