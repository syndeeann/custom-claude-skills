#!/usr/bin/env python3
"""Jaiman's editing tool: put generated clips in story order, join them without glitches, lay the voice-over on, check sync.

    jaiman_edit.py plan   --clips DIR --script SCRIPT.prompts.json [--out edit.json]
    jaiman_edit.py build  --edit edit.json --clips DIR --out final.mp4 [--vo VO.wav] [--profile NAME|FILE]
    jaiman_edit.py check  --final final.mp4 --edit edit.json [--profile NAME|FILE] [--out report.json]

plan   matches clip files to the script's clip numbers (the order Marites wrote) and writes a cut list.
build  trims every clip, gives all of them the same size/fps/audio format, fades the audio a few ms at every
       joint (no pops), joins them and, if given, lays the voice-over on. One encode at the end.
check  measures the result: black or frozen frames, audio/video length drift, silence gaps, speech that crosses a
       joint, voice-over that starts or ends outside its clip window, loudness. Exit 0 pass, 1 fail.
Needs ffmpeg and ffprobe on the PATH. Reports facts; it never posts or regenerates.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROFILES = Path(__file__).resolve().parent.parent / "profiles"


def die(msg: str, code: int = 2):
    print("ERROR:", msg, file=sys.stderr)
    sys.exit(code)


def run(cmd: list, check=True) -> subprocess.CompletedProcess:
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if check and r.returncode != 0:
        die(f"{cmd[0]} failed: {r.stderr.strip()[-600:]}")
    return r


def need_tools():
    for t in ("ffmpeg", "ffprobe"):
        if not shutil.which(t):
            die(f"{t} not found on PATH")


def load_profile(name: str | None) -> dict:
    p = Path(name) if name and Path(name).exists() else PROFILES / f"{name or 'generic'}.json"
    if not p.exists():
        die(f"profile {name!r} not found in {PROFILES}")
    base = json.loads((PROFILES / "generic.json").read_text(encoding="utf-8"))
    base.update(json.loads(p.read_text(encoding="utf-8")))
    return base


def probe(path: Path) -> dict:
    r = run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path])
    d = json.loads(r.stdout)
    v = next((s for s in d["streams"] if s["codec_type"] == "video"), None)
    a = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    return {"dur": float(d["format"].get("duration", 0)), "v": v, "a": a,
            "vdur": float((v or {}).get("duration") or d["format"].get("duration", 0)),
            "adur": float((a or {}).get("duration") or 0)}


def find_clip(clips: Path, n: int) -> Path | None:
    pats = [re.compile(rf"(^|[^0-9])0*{n}([^0-9]|$)")]
    hits = [f for f in sorted(clips.iterdir()) if f.suffix.lower() in (".mp4", ".mov", ".webm", ".m4v")
            and pats[0].search(re.sub(r"\.[^.]+$", "", f.name).split("clip")[-1])]
    return hits[-1] if hits else None   # newest take last in name order


# ------------------------------------------------------------------------------------------------- plan
def cmd_plan(a) -> int:
    clips = Path(a.clips)
    script = json.loads(Path(a.script).read_text(encoding="utf-8"))["clips"]
    cuts, problems = [], []
    for c in script:
        f = find_clip(clips, c["n"])
        if not f:
            problems.append(f"script clip {c['n']}: no file in {clips} (name it ...clip{c['n']:02d}.mp4)")
            continue
        info = probe(f)
        want = float(c.get("seconds") or info["dur"])
        end = min(info["dur"], want) if want else info["dur"]
        cuts.append({"n": c["n"], "file": f.name, "start": 0.0, "end": round(end, 3),
                     "voiceover": c.get("voiceover", "")})
    stray = [f.name for f in clips.iterdir() if f.suffix.lower() in (".mp4", ".mov", ".webm", ".m4v")
             and f.name not in {c["file"] for c in cuts}]
    if stray:
        print("NOTE: files not in the script (extra takes?):", ", ".join(stray))
    out = Path(a.out)
    out.write_text(json.dumps({"clips": cuts}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for p in problems:
        print("PROBLEM:", p)
    print(f"wrote {out} with {len(cuts)} of {len(script)} clips in script order")
    return 1 if problems else 0


# ------------------------------------------------------------------------------------------------- build
def cmd_build(a) -> int:
    need_tools()
    prof = load_profile(a.profile)
    edit = json.loads(Path(a.edit).read_text(encoding="utf-8"))
    cuts = edit["clips"]
    clips = Path(a.clips)
    W, H = prof["size"]
    fps, fade = prof["fps"], prof["audio_fade_ms"] / 1000
    tmp = Path(tempfile.mkdtemp(prefix="jaiman-"))
    segs = []
    for c in cuts:
        src = clips / c.get("file", "") if c.get("file") else find_clip(clips, c["n"])
        if not src or not src.exists():
            die(f"clip {c['n']}: source file missing")
        d = round(c["end"] - c["start"], 3)
        has_a = probe(src)["a"] is not None
        vf = (f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black,"
              f"setsar=1,fps={fps},format=yuv420p,setpts=PTS-STARTPTS")
        afade = f"afade=t=in:d={fade},afade=t=out:st={max(d - fade, 0):.3f}:d={fade}"
        af = (f"aresample=48000,aformat=channel_layouts=stereo,{afade}" if has_a else None)
        out = tmp / f"seg{c['n']:03d}.mp4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", c["start"], "-t", d, "-i", src]
        if not has_a:
            cmd += ["-f", "lavfi", "-t", d, "-i", "anullsrc=r=48000:cl=stereo"]
        cmd += ["-vf", vf]
        cmd += (["-af", af] if af else [])
        cmd += ["-map", "0:v:0", "-map", "0:a:0" if has_a else "1:a:0", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", str(prof["crf"]), "-g", str(fps), "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-t", d, out]
        run(cmd)
        segs.append(out)
    lst = tmp / "list.txt"
    lst.write_text("".join(f"file '{s}'\n" for s in segs), encoding="utf-8")
    joined = tmp / "joined.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", joined])
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    if a.vo:
        duck = prof["bed_gain_db"]
        fc = (f"[0:a]volume={duck}dB[bed];[1:a]aresample=48000,aformat=channel_layouts=stereo,"
              f"adelay={int(a.vo_offset * 1000)}|{int(a.vo_offset * 1000)}[vo];"
              f"[bed][vo]amix=inputs=2:duration=first:normalize=0,loudnorm=I={prof['lufs']}:TP=-1.5:LRA=11[aout]")
        run(["ffmpeg", "-y", "-v", "error", "-i", joined, "-i", a.vo, "-filter_complex", fc, "-map", "0:v", "-map",
             "[aout]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    else:
        run(["ffmpeg", "-y", "-v", "error", "-i", joined, "-af", f"loudnorm=I={prof['lufs']}:TP=-1.5:LRA=11",
             "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out])
    shutil.rmtree(tmp, ignore_errors=True)
    total = sum(c["end"] - c["start"] for c in cuts)
    print(f"built {out}: {len(cuts)} clips, {total:.1f}s, {W}x{H} @ {fps}fps")
    return 0


# ------------------------------------------------------------------------------------------------- check
def detect(final: Path, flt: str, kind: str) -> str:
    args = ["ffmpeg", "-hide_banner", "-nostats", "-i", final]
    args += (["-vf", flt, "-an"] if kind == "v" else ["-af", flt, "-vn"])
    return run(args + ["-f", "null", "-"], check=False).stderr


def speech_spans(final: Path, noise_db: float, min_gap: float, total: float) -> list[tuple[float, float]]:
    log = detect(final, f"silencedetect=noise={noise_db}dB:d={min_gap}", "a")
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", log)]
    sil, i = [], 0
    for s in starts:
        e = ends[i] if i < len(ends) else total
        i += 1
        sil.append((max(s, 0.0), e))
    spans, t = [], 0.0
    for s, e in sil:
        if s - t > 0.05:
            spans.append((t, s))
        t = e
    if total - t > 0.05:
        spans.append((t, total))
    return spans


def cmd_check(a) -> int:
    need_tools()
    prof = load_profile(a.profile)
    final = Path(a.final)
    cuts = json.loads(Path(a.edit).read_text(encoding="utf-8"))["clips"]
    info = probe(final)
    problems, warnings, facts = [], [], {}
    W, H = prof["size"]
    v = info["v"] or {}
    if (v.get("width"), v.get("height")) != (W, H):
        problems.append(f"size is {v.get('width')}x{v.get('height')}, the profile wants {W}x{H}")
    expected = sum(c["end"] - c["start"] for c in cuts)
    if abs(info["vdur"] - expected) > prof["length_tolerance_s"]:
        problems.append(f"video is {info['vdur']:.2f}s but the cut list adds up to {expected:.2f}s")
    if not info["a"]:
        problems.append("no audio track")
    else:
        drift = abs(info["vdur"] - info["adur"])
        facts["av_drift_ms"] = round(drift * 1000)
        if drift * 1000 > prof["av_drift_ms"]:
            problems.append(f"audio and video lengths differ by {drift * 1000:.0f} ms (limit {prof['av_drift_ms']}): sync will drift")
    log = detect(final, f"blackdetect=d={prof['black_s']}:pic_th=0.98", "v")
    blacks = re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", log)
    for s, e in blacks:
        problems.append(f"black frames {float(s):.2f}-{float(e):.2f}s (a gap or missing clip)")
    log = detect(final, f"freezedetect=n=-60dB:d={prof['freeze_s']}", "v")
    for s in re.findall(r"freeze_start: ([\d.]+)", log):
        warnings.append(f"picture frozen from {float(s):.2f}s for {prof['freeze_s']}s+ (a stalled or looped clip)")
    log = detect(final, "ebur128=peak=true", "a")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", log)
    if m:
        facts["lufs"] = float(m[-1])
        if abs(facts["lufs"] - prof["lufs"]) > prof["lufs_tolerance"]:
            warnings.append(f"loudness {facts['lufs']} LUFS, target {prof['lufs']} ± {prof['lufs_tolerance']}")
    # speech against joints
    bounds, t = [], 0.0
    for c in cuts:
        t0 = t
        t += c["end"] - c["start"]
        bounds.append((c["n"], t0, t))
    # with a separate voice-over file, measure that (the music/ambience bed in the mix hides the gaps); else the final
    if a.vo:
        vo_dur = probe(Path(a.vo))["dur"]
        spans = [(s + a.vo_offset, e + a.vo_offset)
                 for s, e in speech_spans(Path(a.vo), prof["speech_noise_db"], prof["speech_gap_s"], vo_dur)]
        facts["measured_on"] = "voice-over file"
    else:
        spans = speech_spans(final, prof["speech_noise_db"], prof["speech_gap_s"], info["adur"] or info["dur"])
        facts["measured_on"] = "final audio"
    facts["speech_spans"] = [(round(s, 2), round(e, 2)) for s, e in spans]
    tol = prof["joint_tolerance_s"]
    for n, t0, t1 in bounds[:-1]:
        for s, e in spans:
            if s < t1 - tol and e > t1 + tol and (e - s) < prof["max_sentence_s"]:
                warnings.append(f"speech {s:.2f}-{e:.2f}s runs across the joint after clip {n} at {t1:.2f}s: check the line isn't cut or doubled")
    for n, t0, t1 in bounds:
        inside = [(s, e) for s, e in spans if s < t1 and e > t0]
        if cuts[n - 1].get("voiceover") and not inside:
            problems.append(f"clip {n} should have narration ({cuts[n - 1]['voiceover'][:40]}…) but its window {t0:.1f}-{t1:.1f}s is silent")
        for s, e in inside:
            if e > t1 + prof["tail_over_s"] and n < len(bounds):
                problems.append(f"clip {n}: narration ends {e - t1:.2f}s after its picture moves on (voice-over is out of sync)")
            if s < t0 - prof["tail_over_s"] and n > 1:
                problems.append(f"clip {n}: narration starts {t0 - s:.2f}s before its picture")
    if spans and spans[-1][1] > expected + prof["tail_over_s"]:
        problems.append(f"narration runs to {spans[-1][1]:.2f}s but the picture ends at {expected:.2f}s (voice-over cut off)")
    ok = not problems
    print(("PASS" if ok else "FAIL") + f": {final.name}  {info['vdur']:.1f}s  {len(cuts)} clips")
    for p in problems:
        print("  PROBLEM:", p)
    for w in warnings:
        print("  warning:", w)
    print("  facts:", json.dumps(facts))
    if a.out:
        Path(a.out).write_text(json.dumps({"pass": ok, "problems": problems, "warnings": warnings, "facts": facts}, indent=2) + "\n")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("plan"); c.add_argument("--clips", required=True); c.add_argument("--script", required=True)
    c.add_argument("--out", default="edit.json"); c.set_defaults(fn=cmd_plan)
    c = sub.add_parser("build"); c.add_argument("--edit", required=True); c.add_argument("--clips", required=True)
    c.add_argument("--out", required=True); c.add_argument("--vo"); c.add_argument("--vo-offset", type=float, default=0.0)
    c.add_argument("--profile"); c.set_defaults(fn=cmd_build)
    c = sub.add_parser("check"); c.add_argument("--final", required=True); c.add_argument("--edit", required=True)
    c.add_argument("--profile"); c.add_argument("--out"); c.add_argument("--vo", help="the voice-over file used in build"); c.add_argument("--vo-offset", type=float, default=0.0)
    c.set_defaults(fn=cmd_check)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
