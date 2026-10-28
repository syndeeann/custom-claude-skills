#!/usr/bin/env python3
"""Standalone quality check for Google Flow clips — works for any project.

    python flow_qa.py <video files and/or folders> [--profile NAME|FILE] [--script FILE] [--out DIR]
    python flow_qa.py <run_dir> [--profile NAME|FILE]            # assembled final + cut list (auto-detected)

Two modes, picked automatically:

  clips  Raw Flow clips (one or many files, or a folder of them). Each clip is checked on its own and
         against the others. Clips are numbered in file-name order, so clip N matches line N of --script.
  run    A run folder in the Kilabot / TikTok-ads layout (brief.json + prompts.json + edit.json + clips/ +
         <id>-final.mp4). Checks the assembled final against its cut list and source clips — the same gate
         as the old scripts/qc.py — and writes qc.json + check/ into the run folder, as before.

Automatic checks
  clips mode  readable · video + audio present · orientation/fps/codecs · length · black frames ·
              frozen picture · audio clipping · narration present when a line is expected · speech in a
              clip that should be silent · line cut off at the end / no lead-in · silence inside a line
              (dropout) · speech much longer than the line (Flow repeating words) · duplicate files ·
              identical-looking clips · repeated words in the script
  run mode    everything from the old qc.py: completeness/order · duplicates · per-segment audio identity ·
              sync (|lag| <= profile sync_ms) · narration present · black/frozen/dropouts/clipping ·
              exact format · size cap · minimum content length · repeated words in the script

It also renders the sheets for Claude's visual review (references/checklist.md):
  qc_sheet.png   frames from every clip, labelled with the clip number
  lip_sheet.png  4 larger frames per clip that shows people — for the "no dubbing" lip check

Writes <out>/qa.json and <out>/qa_report.md (run mode: qc.json in the run folder). Exit 0 = automatic
checks passed, 1 = failed, 2 = bad input. The automatic checks are only half of QC: a clip passes only
after the visual review too.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from repeats import check as repeat_check  # noqa: E402

VIDEO_EXT = {".mp4", ".mov", ".webm", ".mkv", ".m4v"}
FONTS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/System/Library/Fonts/Helvetica.ttc",
         "C:/Windows/Fonts/arialbd.ttf"]
FONT = next((f for f in FONTS if Path(f).exists()), None)
PEOPLE = re.compile(r"\b(man|men|woman|women|guard|agent|agents|boy|girl|child|kid|lola|lolo|mother|father|nanay|tatay|"
                    r"teacher|student|vendor|host|ate|kuya|narrator|person|people|face|faces|character|crowd|"
                    r"coworkers?|friend|couple|family|she|he|her|his|they|someone|figure|silhouette)\b", re.I)


# ----------------------------------------------------------------------------------------------- helpers
def sh(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return r.stdout + r.stderr


def probe(path: Path) -> dict:
    out = sh(["ffprobe", "-v", "error", "-show_entries",
              "stream=codec_type,codec_name,width,height,r_frame_rate,duration:format=duration,size",
              "-of", "json", str(path)])
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {}


def streams(pr: dict) -> tuple[dict, dict]:
    ss = pr.get("streams") or []
    return (next((s for s in ss if s.get("codec_type") == "video"), {}),
            next((s for s in ss if s.get("codec_type") == "audio"), {}))


def fps_of(v: dict) -> float:
    try:
        a, b = (v.get("r_frame_rate") or "0/1").split("/")
        return float(a) / float(b or 1)
    except (ValueError, ZeroDivisionError):
        return 0.0


def frame(path: Path, t: float, w: int = 64, h: int = 114) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1",
                          "-vf", f"scale={w}:{h},format=gray", "-f", "rawvideo", "-"],
                         capture_output=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(raw, np.uint8).astype(float).reshape(h, w) if len(raw) == w * h else np.zeros((h, w))


def pcm(path: Path, start: float = 0, dur: float | None = None) -> np.ndarray:
    cmd = ["ffmpeg", "-nostdin", "-v", "error", "-ss", str(start)] + (["-t", str(dur)] if dur else []) + \
          ["-i", str(path), "-vn", "-ac", "1", "-ar", "8000", "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(raw, np.int16).astype(float)


def lag_ms(ref: np.ndarray, sig: np.ndarray, max_ms: int = 1500) -> float:
    """Offset of ref inside sig (positive = sig audio is late), via normalized cross-correlation of envelopes."""
    def env(x):
        k = 80
        n = len(x) // k
        e = np.abs(x[: n * k]).reshape(n, k).mean(1)
        return (e - e.mean()) / (e.std() + 1e-9)
    a, b = env(ref), env(sig)
    m = max_ms // 10
    best, arg = -1e9, 0
    for s in range(-m, m + 1):
        x, y = (a[: len(a) - s], b[s: s + len(a) - s]) if s >= 0 else (a[-s:], b[: len(a) + s])
        n = min(len(x), len(y))
        if n < 50:
            continue
        c = float(np.dot(x[:n], y[:n]) / n)
        if c > best:
            best, arg = c, s
    return arg * 10.0


def energy_db(x: np.ndarray, k: int = 400) -> np.ndarray:
    """dB energy per 50 ms window (x = 8 kHz mono pcm)."""
    n = len(x) // k
    if n == 0:
        return np.zeros(0)
    return 20 * np.log10(np.sqrt((x[: n * k].reshape(n, k) ** 2).mean(1)) + 1)


def voiced(x: np.ndarray) -> np.ndarray:
    """Boolean per 50 ms window: voice-band energy well above the clip's quiet floor."""
    e = energy_db(x)
    if len(e) == 0:
        return e.astype(bool)
    floor = np.percentile(e, 20)
    return e > max(floor + 12, e.max() - 25)


def speech_ratio(x: np.ndarray) -> float:
    if len(x) < 4000:
        return 0.0
    return float(voiced(x).mean())


def longest_dead(x: np.ndarray, start_w: int = 4, end_w: int = 4) -> float:
    """Longest run of total silence (seconds), ignoring the first/last few windows."""
    e = energy_db(x)
    dead = e < 5
    run = best = 0
    for v in dead[start_w: len(dead) - end_w]:
        run = run + 1 if v else 0
        best = max(best, run)
    return best * 0.05


def drawtext(label: str, size: int) -> str:
    font = f"fontfile={FONT}:" if FONT else ""
    return f"drawtext={font}text='{label}':x=8:y=8:fontsize={size}:fontcolor=yellow:box=1:boxcolor=black@0.6"


def tile_sheet(tiles: list[Path], cols: int, out: Path) -> Path | None:
    tiles = [t for t in tiles if t.exists()]
    if not tiles:
        return None
    rows = (len(tiles) + cols - 1) // cols
    lst = out.parent / (out.stem + "_list.txt")
    lst.write_text("".join(f"file '{p.name}'\n" for p in tiles))
    sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-vf", f"tile={cols}x{rows}:padding=4", "-frames:v", "1", str(out)])
    return out if out.exists() else None


def grab(src: Path, t: float, out: Path, w: int, h: int, label: str, size: int) -> Path:
    sh(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(t, 0):.2f}", "-i", str(src), "-frames:v", "1",
        "-vf", f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,{drawtext(label, size)}",
        str(out)])
    return out


# ----------------------------------------------------------------------------------------------- profiles / script
def load_profile(arg: str | None) -> dict:
    base = json.loads((HERE.parent / "profiles" / "generic.json").read_text(encoding="utf-8"))
    if not arg or arg == "generic":
        return base
    p = Path(arg)
    if not p.exists():
        p = HERE.parent / "profiles" / f"{arg}.json"
    if not p.exists():
        names = sorted(x.stem for x in (HERE.parent / "profiles").glob("*.json"))
        sys.exit(f"profile '{arg}' not found; available: {', '.join(names)} (or a path to a .json file)")
    prof = json.loads(p.read_text(encoding="utf-8"))

    def merge(a: dict, b: dict) -> dict:
        out = dict(a)
        for k, v in b.items():
            out[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
        return out
    return merge(base, prof)


def load_script(path: Path | None) -> list[dict]:
    """prompts.json-style {"clips": [...]}, a JSON list (of dicts or strings), or a text file: one clip per
    non-empty line, optionally "3: line" / "3. line" / "Clip 3 - line"; "-" or "(none)" = no spoken line."""
    if not path:
        return []
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        d = json.loads(text)
        items = d.get("clips", []) if isinstance(d, dict) else d
        return [x if isinstance(x, dict) else {"voiceover": str(x)} for x in items]
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^(clip\s*)?\d+\s*[:.)\-–]\s*", "", line, flags=re.I)
        if line.lower() in {"-", "(none)", "none", "(no line)", "(hero)"}:
            line = ""
        out.append({"voiceover": line})
    return out


def spoken(c: dict) -> str:
    return ((c.get("voiceover") or "") + " " + (c.get("dialogue") or "")).strip()


def shows_people(c: dict) -> bool:
    txt = (c.get("visual") or "") + " " + (c.get("prompt") or "")[:400]
    if "is off-screen" in (c.get("prompt") or "") and not PEOPLE.search(c.get("visual") or ""):
        return False
    return bool(PEOPLE.search(txt))


# ----------------------------------------------------------------------------------------------- clips mode
def check_clips(files: list[Path], prof: dict, script: list[dict], out: Path) -> dict:
    fmt, cl = prof["format"], prof["clip"]
    problems, warnings, per_clip = [], [], []
    out.mkdir(parents=True, exist_ok=True)
    chk = out / "check"
    chk.mkdir(exist_ok=True)

    if script and len(script) != len(files):
        warnings.append(f"script has {len(script)} clips but {len(files)} video files were given — "
                        f"clip N is matched to script line N by file-name order; check the pairing")

    hashes, mids, durs = {}, {}, {}
    for i, f in enumerate(files, 1):
        c = script[i - 1] if i <= len(script) else {}
        line = spoken(c)
        hero = bool(c.get("hero"))
        info = {"n": i, "file": f.name}
        P, W = [], []
        pr = probe(f)
        v, a = streams(pr)
        if not v:
            P.append("not a readable video")
            per_clip.append({**info, "problems": P, "warnings": W})
            problems += [f"clip {i} ({f.name}): {m}" for m in P]
            continue
        d = float(v.get("duration") or (pr.get("format") or {}).get("duration") or 0)
        durs[i] = d
        w, h, fps = v.get("width"), v.get("height"), fps_of(v)
        info.update(resolution=f"{w}x{h}", fps=round(fps, 2), duration=round(d, 2))
        orient = fmt.get("orientation")
        if orient == "vertical" and w and h and w >= h:
            P.append(f"{w}x{h} is not vertical (9:16)")
        elif orient == "horizontal" and w and h and h >= w:
            P.append(f"{w}x{h} is not horizontal (16:9)")
        if fmt.get("fps") and abs(fps - fmt["fps"]) > 0.5:
            W.append(f"{fps:.2f} fps (project uses {fmt['fps']})")
        if not a:
            (P if fmt.get("require_audio", True) else W).append("no audio track")
        if cl.get("min_s") and d < cl["min_s"] - 0.05:
            W.append(f"only {d:.1f}s long (expected ≥ {cl['min_s']}s)")
        if cl.get("max_s") and d > cl["max_s"] + 0.05:
            W.append(f"{d:.1f}s long (expected ≤ {cl['max_s']}s)")

        hashes.setdefault(hashlib.md5(f.read_bytes()).hexdigest(), []).append(i)
        mids[i] = [frame(f, d * x) for x in (0.25, 0.5, 0.75)]

        # picture: black frames (edges = trim, middle = regenerate) and frozen picture
        blk = sh(["ffmpeg", "-nostdin", "-v", "info", "-i", str(f), "-vf",
                  f"blackdetect=d={prof['black_s']}:pic_th=0.98", "-an", "-f", "null", "-"])
        for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", blk):
            s, e = float(s), float(e)
            if s < 0.5 or e > d - 0.5:
                W.append(f"black frames {s:.1f}–{e:.1f}s at the clip edge (trim them)")
            else:
                P.append(f"black frames {s:.1f}–{e:.1f}s in the middle of the clip")
        frz = sh(["ffmpeg", "-nostdin", "-v", "info", "-i", str(f), "-vf",
                  f"freezedetect=n=0.0015:d={prof['freeze_s']}", "-an", "-f", "null", "-"])
        for s in re.findall(r"freeze_start: ([\d.]+)", frz):
            W.append(f"picture frozen {prof['freeze_s']}s+ from {float(s):.1f}s (OK only for a deliberate still shot)")

        # audio: clipping, speech presence / timing / dropouts
        if a:
            vol = sh(["ffmpeg", "-nostdin", "-v", "info", "-i", str(f), "-af", "volumedetect", "-vn", "-f", "null", "-"])
            m = re.search(r"max_volume: (-?[\d.]+) dB", vol)
            if m and float(m.group(1)) > -0.3:
                W.append(f"audio peaks at {m.group(1)} dB (possible clipping)")
            x = pcm(f)
            sr = speech_ratio(x)
            info["speech_ratio"] = round(sr, 2)
            mode = prof.get("speech_expected", "script")
            expect = bool(line) or (mode == "always" and not hero)
            silent_expected = hero or (bool(script) and not line and mode != "always") or mode == "never"
            vo = voiced(x)
            if expect:
                if sr < 0.15:
                    P.append(f"little or no narration heard (speech {sr:.0%}) — line missing or cut")
                elif len(vo) > 10:
                    idx = np.flatnonzero(vo)
                    first, last = idx[0] * 0.05, (idx[-1] + 1) * 0.05
                    info.update(speech_start=round(first, 2), speech_end=round(last, 2))
                    tail = prof.get("speech_tail_s", 0.3)
                    if d - last < tail:
                        P.append(f"speech runs to the very end ({d - last:.2f}s left) — the line is probably cut off")
                    if first < 0.1:
                        W.append("speech starts in the first 0.1s — no lead-in, the first word may be clipped")
                    if line:
                        nw = len(re.findall(r"[\wñÑ'’-]+", line))
                        allowed = nw * prof.get("seconds_per_word", 0.45) * 1.8 + 1.0
                        if last - first > allowed:
                            W.append(f"speech lasts {last - first:.1f}s for a {nw}-word line — Flow may have repeated "
                                     f"or added words; listen to it")
                    dead = longest_dead(x)
                    if dead >= 0.7:
                        W.append(f"{dead:.1f}s of total silence inside the line (check for a dropped word)")
            elif silent_expected and sr >= 0.35 and prof.get("flag_unexpected_speech", True):
                W.append(f"speech-like audio ({sr:.0%}) in a clip that should have no voice-over — listen for stray talking")
        per_clip.append({**info, "line": line, "problems": P, "warnings": W})
        problems += [f"clip {i}: {m}" for m in P]
        warnings += [f"clip {i}: {m}" for m in W]

    # duplicates across clips
    for grp in hashes.values():
        if len(grp) > 1:
            problems.append(f"clips {grp} are the same file (download mix-up)")
    keys = list(mids)
    for x in range(len(keys)):
        for y in range(x + 1, len(keys)):
            fa, fb = mids[keys[x]], mids[keys[y]]
            diffs = [float(np.abs(p - q).mean()) for p, q in zip(fa, fb) if p.std() >= 3 and q.std() >= 3]
            if diffs and max(diffs) < 4.0:
                problems.append(f"clips {keys[x]} and {keys[y]} look identical (pixel diff ≤ {max(diffs):.1f}) — redundant clip?")

    # mark cross-clip failures on the clips they involve, so the per-clip table is truthful
    for msg in problems:
        if m := re.match(r"clips \[([\d, ]+)\] are the same file", msg):
            hit = [int(x) for x in m.group(1).split(",")]
        elif m := re.match(r"clips (\d+) and (\d+) look identical", msg):
            hit = [int(m.group(1)), int(m.group(2))]
        else:
            continue
        for c in per_clip:
            if c["n"] in hit:
                c["problems"].append(msg)

    # repeated words in the script
    if script and prof.get("repeats", True):
        rp, rw = repeat_check(script, prof.get("extra_stopwords", []))
        problems += [f"repeated words in script: {m}" for m in rp]
        warnings += [f"repeated words in script: {m}" for m in rw]

    # sheets for the visual review
    tiles, lip_tiles, lip_clips = [], [], []
    for i, f in enumerate(files, 1):
        d = durs.get(i)
        if not d:
            continue
        for k, fr in enumerate((0.2, 0.5, 0.8)):
            tiles.append(grab(f, d * fr, chk / f"qc_{i:02d}{'abc'[k]}.png", 180, 320, str(i), 26))
        c = script[i - 1] if i <= len(script) else {}
        if prof.get("lip_check", True) and (not script or shows_people(c) or not c.get("visual")):
            lip_clips.append(i)
            for k, fr in enumerate((0.15, 0.38, 0.62, 0.85)):
                lip_tiles.append(grab(f, d * fr, chk / f"lip_{i:02d}{k}.png", 360, 640, f"{i}.{k + 1}", 30))
    sheet = tile_sheet(tiles, 9, chk / "qc_sheet.png")
    lip = tile_sheet(lip_tiles, 4, chk / "lip_sheet.png") if lip_tiles else None
    visuals = {str(i): (script[i - 1].get("visual", "") if i <= len(script) else "") for i in range(1, len(files) + 1)}
    return {"mode": "clips", "passed": not problems, "problems": problems, "warnings": warnings,
            "clips": per_clip,
            "visual_review": {"sheet": str(sheet.relative_to(out)) if sheet else None,
                              "sheet_layout": "3 frames per clip (20%, 50%, 80%), labelled with the clip number",
                              "lip_sheet": str(lip.relative_to(out)) if lip else None,
                              "lip_check_clips": lip_clips, "expected_visuals": visuals,
                              "checklist": prof.get("visual_checklist", [])}}


# ----------------------------------------------------------------------------------------------- run mode
def is_run_dir(p: Path) -> bool:
    return p.is_dir() and all((p / n).exists() for n in ("brief.json", "prompts.json", "edit.json"))


def check_run(run_dir: Path, prof: dict) -> dict:
    brief = json.loads((run_dir / "brief.json").read_text(encoding="utf-8"))
    script = json.loads((run_dir / "prompts.json").read_text(encoding="utf-8"))["clips"]
    edit = json.loads((run_dir / "edit.json").read_text(encoding="utf-8"))
    tid = brief.get("topic_id") or brief.get("ad_id")
    final = run_dir / f"{tid}-final.mp4"
    if not final.exists():
        sys.exit(f"{final.name} not found in {run_dir} — assemble the video first (or pass the clips folder for clips mode)")
    cuts = edit["clips"]
    fps = prof["format"].get("fps") or 24
    problems, warnings, info = [], [], {}

    ns = [c["n"] for c in cuts]
    if ns != list(range(1, len(script) + 1)):
        problems.append(f"cut list clips {ns} != script clips 1..{len(script)} in order (missing, extra, repeated or out of order)")

    srcs = {c["n"]: run_dir / "clips" / f"{tid}-clip{c['n']:02d}.mp4" for c in cuts}
    hashes = {}
    for n, p in srcs.items():
        if not p.exists():
            problems.append(f"clip {n}: source file missing")
            continue
        hashes.setdefault(hashlib.md5(p.read_bytes()).hexdigest(), []).append(n)
    for group in hashes.values():
        if len(group) > 1:
            problems.append(f"clips {group} are the same file (download mix-up)")
    mids = {c["n"]: frame(srcs[c["n"]], (c["start"] + c["end"]) / 2) for c in cuts if srcs[c["n"]].exists()}
    keys = list(mids)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = mids[keys[i]], mids[keys[j]]
            if a.std() >= 3 and b.std() >= 3 and float(np.abs(a - b).mean()) < 4.0:
                problems.append(f"clips {keys[i]} and {keys[j]} look identical (mean pixel diff "
                                f"{float(np.abs(a - b).mean()):.1f}) — redundant clip?")

    src_audio = {c["n"]: pcm(srcs[c["n"]], c["start"], c["end"] - c["start"]) for c in cuts if srcs[c["n"]].exists()}

    def corr(a, b):
        m = min(len(a), len(b)) // 80 * 80
        if m < 800:
            return -1.0
        ea = np.abs(a[:m]).reshape(-1, 80).mean(1)
        eb = np.abs(b[:m]).reshape(-1, 80).mean(1)
        return float(np.corrcoef(ea, eb)[0, 1]) if ea.std() > 0 and eb.std() > 0 else -1.0

    t, seg_times, worst = 0.0, [], 0.0
    for c in cuts:
        n = c["n"]
        d = int((c["end"] - c["start"]) * fps) / fps
        seg_times.append((n, t, d))
        if n not in src_audio:
            t += d
            continue
        out = pcm(final, t, d)
        lag = lag_ms(src_audio[n], out)
        worst = max(worst, abs(lag))
        if abs(lag) > prof["sync_ms"]:
            problems.append(f"clip {n} at {t:.1f}s: voice-over out of sync by {lag:+.0f} ms")
        own = corr(src_audio[n], out)
        others = [(corr(src_audio[k], out), k) for k in src_audio if k != n]
        best_other = max(others) if others else (-1.0, None)
        if own < 0.5 or best_other[0] > own + 0.05:
            problems.append(f"clip {n} at {t:.1f}s: audio doesn't match its own clip (own {own:.2f}, clip {best_other[1]} {best_other[0]:.2f})")
        line = spoken(script[n - 1]) if n <= len(script) else ""
        sr = speech_ratio(out)
        if line and sr < 0.15:
            problems.append(f"clip {n} at {t:.1f}s: little or no narration heard (speech {sr:.0%}) — line missing or cut")
        if line and len(out) > 16000 and longest_dead(out) >= 0.7:
            warnings.append(f"clip {n} at {t:.1f}s: {longest_dead(out):.1f}s of total silence inside the clip (check for a dropout)")
        t += d
    info["worst_lag_ms"] = worst
    story_end = t

    blk = sh(["ffmpeg", "-nostdin", "-v", "info", "-t", f"{story_end:.2f}", "-i", str(final), "-vf",
              f"blackdetect=d={prof['black_s']}:pic_th=0.98", "-an", "-f", "null", "-"])
    for s, e in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", blk):
        problems.append(f"black frames {float(s):.1f}–{float(e):.1f}s")
    frz = sh(["ffmpeg", "-nostdin", "-v", "info", "-t", f"{story_end:.2f}", "-i", str(final), "-vf",
              f"freezedetect=n=0.0015:d={prof['freeze_s']}", "-an", "-f", "null", "-"])
    for s in re.findall(r"freeze_start: ([\d.]+)", frz):
        warnings.append(f"picture frozen for {prof['freeze_s']}s+ from {float(s):.1f}s (fine for a static shot — check the sheet)")
    vol = sh(["ffmpeg", "-nostdin", "-v", "info", "-i", str(final), "-af", "volumedetect", "-vn", "-f", "null", "-"])
    m = re.search(r"max_volume: (-?[\d.]+) dB", vol)
    if m and float(m.group(1)) > -0.3:
        warnings.append(f"audio peaks at {m.group(1)} dB (possible clipping)")

    fmt = prof["format"]
    pr = probe(final)
    v, a = streams(pr)
    res = [tuple(r) for r in fmt.get("resolutions") or []]
    if res and (v.get("width"), v.get("height")) not in res:
        problems.append(f"resolution {v.get('width')}x{v.get('height')} is not one of {['%dx%d' % r for r in res]}")
    if (fmt.get("video_codec") and v.get("codec_name") != fmt["video_codec"]) or \
       (fmt.get("audio_codec") and a.get("codec_name") != fmt["audio_codec"]):
        problems.append(f"codecs must be {fmt.get('video_codec')} + {fmt.get('audio_codec')} "
                        f"(got {v.get('codec_name')} + {a.get('codec_name')})")
    vd, ad = float(v.get("duration", 0)), float(a.get("duration", 0))
    if abs(vd - ad) > 0.4:
        problems.append(f"video {vd:.2f}s vs audio {ad:.2f}s")
    size_mb = int((pr.get("format") or {}).get("size", 0)) / 1e6
    info.update(duration=round(vd, 2), size_mb=round(size_mb, 2), content_s=round(story_end, 2))
    if fmt.get("max_mb") and size_mb >= fmt["max_mb"]:
        warnings.append(f"file is {size_mb:.1f} MB — over the {fmt['max_mb']} MB upload limit")
    fin = prof.get("final") or {}
    if fin.get("min_content_s") and story_end < fin["min_content_s"]:
        problems.append(f"content is {story_end:.1f}s without the end card — needs ≥ {fin['min_content_s']}s")
    if fin.get("max_content_s") and story_end > fin["max_content_s"]:
        warnings.append(f"content is {story_end:.1f}s — over the {fin['max_content_s']}s target")

    if prof.get("repeats", True):
        rp, rw = repeat_check(script, prof.get("extra_stopwords", []))
        problems += [f"repeated words in script: {x}" for x in rp]
        warnings += [f"repeated words in script: {x}" for x in rw]

    chk = run_dir / "check"
    chk.mkdir(exist_ok=True)
    tiles, lip_tiles, lip_clips = [], [], []
    for n, t0, d in seg_times:
        for frac, tag in ((0.25, "a"), (0.75, "b")):
            tiles.append(grab(final, t0 + d * frac, chk / f"qc_{n:02d}{tag}.png", 180, 320, str(n), 26))
        c = script[n - 1] if n <= len(script) else {}
        if prof.get("lip_check", True) and shows_people(c):
            lip_clips.append(n)
            for k, frac in enumerate((0.15, 0.38, 0.62, 0.85)):
                lip_tiles.append(grab(final, t0 + d * frac, chk / f"lip_{n:02d}{k}.png", 360, 640, f"{n}.{k + 1}", 30))
    tile_sheet(tiles, 8, chk / "qc_sheet.png")
    lip = tile_sheet(lip_tiles, 4, chk / "lip_sheet.png") if lip_tiles else None
    visuals = {str(n): (script[n - 1].get("visual", "") if n <= len(script) else "") for n, _, _ in seg_times}
    return {"mode": "run", "passed": not problems, "problems": problems, "warnings": warnings, "info": info,
            "visual_review": {"sheet": "check/qc_sheet.png",
                              "sheet_layout": "2 frames per clip (a = 25%, b = 75%), labelled with the clip number",
                              "lip_sheet": "check/lip_sheet.png" if lip else None, "lip_check_clips": lip_clips,
                              "expected_visuals": visuals, "checklist": prof.get("visual_checklist", [])}}


# ----------------------------------------------------------------------------------------------- report
def report_md(res: dict, prof: dict, target: str) -> str:
    L = [f"# QA report — {target}", "",
         f"- Profile: **{prof.get('name')}** · mode: {res['mode']} · {datetime.now():%Y-%m-%d %H:%M}",
         f"- Automatic checks: **{'PASSED' if res['passed'] else 'FAILED'}** "
         f"({len(res['problems'])} problems, {len(res['warnings'])} warnings)",
         "- Visual review: **pending** (Claude fills this in after reading the sheets)", ""]
    if res.get("info"):
        L += ["## Info", ""] + [f"- {k}: {v}" for k, v in res["info"].items()] + [""]
    L += ["## Problems (must fix)", ""] + ([f"- {p}" for p in res["problems"]] or ["- none"]) + [""]
    L += ["## Warnings (judgment call)", ""] + ([f"- {w}" for w in res["warnings"]] or ["- none"]) + [""]
    if res.get("clips"):
        L += ["## Clips", "", "| # | file | length | res | speech | status |", "|---|---|---|---|---|---|"]
        for c in res["clips"]:
            st = "FAIL" if c["problems"] else ("check" if c["warnings"] else "ok")
            L.append(f"| {c['n']} | {c['file']} | {c.get('duration', '?')}s | {c.get('resolution', '?')} | "
                     f"{c.get('speech_ratio', '–')} | {st} |")
        L.append("")
    vr = res["visual_review"]
    L += ["## Visual review", "", f"- Contact sheet: `{vr['sheet']}` ({vr['sheet_layout']})",
          f"- Lip sheet: `{vr['lip_sheet']}` (clips {vr['lip_check_clips']})" if vr["lip_sheet"] else "- Lip sheet: none",
          "", "Checklist:"] + [f"- [ ] {x}" for x in vr["checklist"]] + [""]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="video files and/or folders, or one run folder")
    ap.add_argument("--profile", default="generic", help="profile name (see profiles/) or path to a profile .json")
    ap.add_argument("--script", type=Path, help="script: prompts.json, JSON list, or a text file with one line per clip")
    ap.add_argument("--out", type=Path, help="where to write qa.json, qa_report.md and the sheets")
    ap.add_argument("--mode", choices=["auto", "clips", "run"], default="auto")
    args = ap.parse_args()
    prof = load_profile(args.profile)
    ins = [Path(x).expanduser().resolve() for x in args.inputs]

    if args.mode == "run" or (args.mode == "auto" and len(ins) == 1 and is_run_dir(ins[0])):
        res = check_run(ins[0], prof)
        res["profile"] = prof.get("name")
        (ins[0] / "qc.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (ins[0] / "check" / "qa_report.md").write_text(report_md(res, prof, ins[0].name), encoding="utf-8")
        out_note = {"qc_json": str(ins[0] / "qc.json"), "report": str(ins[0] / "check" / "qa_report.md")}
    else:
        files: list[Path] = []
        for p in ins:
            if p.is_dir():
                files += sorted(q for q in p.iterdir() if q.suffix.lower() in VIDEO_EXT and not q.name.startswith("."))
            elif p.suffix.lower() in VIDEO_EXT and p.exists():
                files.append(p)
            else:
                print(f"skipping {p} (not a video file or folder)", file=sys.stderr)
        if not files:
            print("no video files found", file=sys.stderr)
            return 2
        script_path = args.script
        if not script_path and len(ins) == 1 and ins[0].is_dir():
            for cand in ("prompts.json", "script.json", "script.txt", "script.md"):
                if (ins[0] / cand).exists():
                    script_path = ins[0] / cand
                    break
        script = load_script(script_path)
        out = (args.out or ((ins[0] if ins[0].is_dir() else ins[0].parent) / f"qa-{datetime.now():%Y%m%d-%H%M%S}")).resolve()
        res = check_clips(files, prof, script, out)
        res["profile"] = prof.get("name")
        res["script"] = str(script_path) if script_path else None
        (out / "qa.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (out / "qa_report.md").write_text(report_md(res, prof, ", ".join(p.name for p in ins)), encoding="utf-8")
        out_note = {"out": str(out), "qa_json": str(out / "qa.json"), "report": str(out / "qa_report.md")}

    summary = {k: res[k] for k in ("mode", "passed", "problems", "warnings")}
    summary.update(out_note, sheet=res["visual_review"]["sheet"], lip_sheet=res["visual_review"]["lip_sheet"])
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
