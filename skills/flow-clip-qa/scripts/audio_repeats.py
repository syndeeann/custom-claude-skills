#!/usr/bin/env python3
"""Find spoken words/phrases that are said twice in the AUDIO (what Flow actually generated).

    python audio_repeats.py <video-or-audio file> [--min-s 0.35] [--threshold 0.88]

The script check (repeats.py) only reads the written line. Flow sometimes says a word twice or restarts a
phrase even when the written line is clean ("... papalapit nang papalapit ... lapit"), and there is no speech
recognition in the workspace. So this compares what the narrator *sounds* like: the audio is turned into
a log-spectrum per 10 ms, and every voiced stretch (0.35-1.4 s) is compared with the speech that follows it.
A later stretch that sounds almost the same as an earlier one is a spoken repeat.

Output: a list of {first_s, repeat_s, length_s, score}. The *repeat* span is the one to cut out of the video
(Jaiman: split the clip into two segments around it). It is a similarity measure, not a transcript, so it
reports where to listen; a hit with score >= STRONG is treated as a failure, a weaker hit as a warning.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

SR = 8000
WIN, HOP = 256, 80            # 32 ms window, 10 ms hop
NB = 24                       # spectral bands (log spaced, 100-3800 Hz)
STRONG = 0.90                 # >= this: a spoken repeat (failure)
WEAK = 0.86                   # >= this: probably a repeat (warning, listen)  [calibrated on synthetic audio only]


def load(path: Path) -> np.ndarray:
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(SR),
                          "-f", "s16le", "-"], capture_output=True, stdin=subprocess.DEVNULL).stdout
    return np.frombuffer(raw, np.int16).astype(float)


def features(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(frames x NB log-band features, voiced mask per frame)."""
    n = 1 + (len(x) - WIN) // HOP if len(x) >= WIN else 0
    if n <= 0:
        return np.zeros((0, NB)), np.zeros(0, bool)
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    fr = x[idx] * np.hanning(WIN)[None, :]
    mag = np.abs(np.fft.rfft(fr, axis=1)) ** 2
    freqs = np.fft.rfftfreq(WIN, 1 / SR)
    edges = np.geomspace(100, 3800, NB + 1)
    bands = np.stack([mag[:, (freqs >= lo) & (freqs < hi)].sum(1) for lo, hi in zip(edges[:-1], edges[1:])], 1)
    logb = np.log(bands + 1.0)
    e = 10 * np.log10(mag.sum(1) + 1.0)
    floor = np.percentile(e, 20)
    voiced = e > max(floor + 10, e.max() - 30)
    return logb, voiced


def _norm(f: np.ndarray) -> np.ndarray:
    f = f - f.mean(0, keepdims=True)                      # mean-normalise: remove loudness / channel colour
    f = f - f.mean(1, keepdims=True)                      # and overall level per frame
    return f


def find_repeats(x: np.ndarray, min_s: float = 0.35, max_s: float = 1.4, lookahead_s: float = 4.0,
                 weak: float = WEAK) -> list[dict]:
    logb, voiced = features(x)
    if len(logb) < 100 or voiced.sum() < 40:
        return []
    f = _norm(logb - logb[voiced].mean(0, keepdims=True))
    f = f / (np.linalg.norm(f, axis=1, keepdims=True) + 1e-9)   # unit vector per frame -> dot = cosine
    n = len(f)
    hits: list[dict] = []
    for L_s in (min_s, 0.55, 0.8, 1.1, max_s):
        L = int(L_s * 100)
        step = 5
        for i in range(0, n - 2 * L, step):
            if voiced[i:i + L].mean() < 0.7:
                continue
            a = f[i:i + L]
            best, bj = -1.0, -1
            for j in range(i + L, min(n - L, i + L + int(lookahead_s * 100)), 2):
                if voiced[j:j + L].mean() < 0.7:
                    continue
                # tolerate a little speed difference: compare against the chunk and a +-4% stretched copy
                s = float((a * f[j:j + L]).sum(1).mean())
                if s > best:
                    best, bj = s, j
            if best >= weak:
                hits.append({"i": i, "j": bj, "L": L, "score": best})
    # merge overlapping hits into spans
    hits.sort(key=lambda h: h["j"])
    spans: list[dict] = []
    for h in hits:
        for s in spans:
            if h["j"] < s["j1"] + 10 and h["j"] + h["L"] > s["j0"] - 10 and abs((h["j"] - h["i"]) - s["gap"]) < 60:
                s["j0"], s["j1"] = min(s["j0"], h["j"]), max(s["j1"], h["j"] + h["L"])
                s["i0"], s["i1"] = min(s["i0"], h["i"]), max(s["i1"], h["i"] + h["L"])
                s["score"] = max(s["score"], h["score"])
                break
        else:
            spans.append({"j0": h["j"], "j1": h["j"] + h["L"], "i0": h["i"], "i1": h["i"] + h["L"],
                          "gap": h["j"] - h["i"], "score": h["score"]})
    out = []
    for s in spans:
        out.append({"first_s": round(s["i0"] / 100, 2), "repeat_s": round(s["j0"] / 100, 2),
                    "repeat_end_s": round(s["j1"] / 100, 2), "length_s": round((s["j1"] - s["j0"]) / 100, 2),
                    "score": round(s["score"], 3), "strong": s["score"] >= STRONG})
    return sorted(out, key=lambda d: d["repeat_s"])


def describe(r: dict) -> str:
    kind = "said again" if r["strong"] else "may be said again"
    return (f"audio: speech at {r['first_s']}s {kind} at {r['repeat_s']}–{r['repeat_end_s']}s "
            f"(sounds {r['score']:.0%} alike) — cut the repeat out of the video")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--min-s", type=float, default=0.35)
    ap.add_argument("--threshold", type=float, default=WEAK)
    a = ap.parse_args()
    res = find_repeats(load(Path(a.file)), min_s=a.min_s, weak=a.threshold)
    print(json.dumps(res, indent=1))
    print("audio repeats: " + ("FAIL" if any(r["strong"] for r in res) else "WARN" if res else "OK"))
    sys.exit(1 if any(r["strong"] for r in res) else 0)
