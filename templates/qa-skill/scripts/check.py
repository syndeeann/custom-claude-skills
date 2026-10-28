#!/usr/bin/env python3
"""Automatic checks for {{name}}.

    python check.py <files and/or folders> [--profile NAME|FILE] [--out DIR]

Writes <out>/qa.json and <out>/qa_report.md. Exit 0 = passed, 1 = failed, 2 = no usable input.

To add a check: write a function `def check_xxx(path, profile) -> (problems, warnings)` and add it to
CHECKS. Each message should say what is wrong and, if possible, the fix.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load_profile(arg: str | None) -> dict:
    base = json.loads((HERE.parent / "profiles" / "generic.json").read_text(encoding="utf-8"))
    if not arg or arg == "generic":
        return base
    p = Path(arg) if Path(arg).exists() else HERE.parent / "profiles" / f"{arg}.json"
    if not p.exists():
        sys.exit(f"profile '{arg}' not found; available: "
                 + ", ".join(sorted(x.stem for x in (HERE.parent / "profiles").glob("*.json"))))
    return {**base, **json.loads(p.read_text(encoding="utf-8"))}


# ------------------------------------------------------------------------------------------- checks
def check_readable(path: Path, prof: dict) -> tuple[list[str], list[str]]:
    if path.stat().st_size == 0:
        return ["file is empty"], []
    return [], []


def check_size(path: Path, prof: dict) -> tuple[list[str], list[str]]:
    mb = path.stat().st_size / 1e6
    if prof.get("max_mb") and mb > prof["max_mb"]:
        return [], [f"{mb:.1f} MB — over the {prof['max_mb']} MB limit"]
    return [], []


CHECKS = [check_readable, check_size]   # TODO: add this skill's own checks


# ------------------------------------------------------------------------------------------- run
def collect(inputs: list[Path], exts: list[str]) -> list[Path]:
    files = []
    for p in inputs:
        if p.is_dir():
            files += sorted(q for q in p.iterdir() if q.is_file() and not q.name.startswith(".")
                            and (not exts or q.suffix.lower() in exts))
        elif p.is_file():
            files.append(p)
    return files


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("--profile", default="generic")
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    prof = load_profile(args.profile)
    ins = [Path(x).expanduser().resolve() for x in args.inputs]
    files = collect(ins, [e.lower() for e in prof.get("extensions") or []])
    if not files:
        print("no files to check", file=sys.stderr)
        return 2
    out = (args.out or ((ins[0] if ins[0].is_dir() else ins[0].parent) / f"qa-{datetime.now():%Y%m%d-%H%M%S}")).resolve()
    out.mkdir(parents=True, exist_ok=True)

    items, problems, warnings = [], [], []
    for i, f in enumerate(files, 1):
        P, W = [], []
        for fn in CHECKS:
            p, w = fn(f, prof)
            P += p
            W += w
        items.append({"n": i, "file": f.name, "problems": P, "warnings": W})
        problems += [f"{i} ({f.name}): {m}" for m in P]
        warnings += [f"{i} ({f.name}): {m}" for m in W]

    res = {"passed": not problems, "profile": prof.get("name"), "problems": problems, "warnings": warnings,
           "items": items, "review_checklist": prof.get("review_checklist", [])}
    (out / "qa.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [f"# QA report — {', '.join(p.name for p in ins)}", "",
          f"- Profile: **{prof.get('name')}** · {datetime.now():%Y-%m-%d %H:%M}",
          f"- Automatic checks: **{'PASSED' if res['passed'] else 'FAILED'}**",
          "- Review: **pending**", "", "## Problems", ""] + ([f"- {p}" for p in problems] or ["- none"]) + \
         ["", "## Warnings", ""] + ([f"- {w}" for w in warnings] or ["- none"]) + \
         ["", "## Review checklist", ""] + [f"- [ ] {x}" for x in res["review_checklist"]]
    (out / "qa_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("passed", "problems", "warnings")} | {"out": str(out)},
                     indent=2, ensure_ascii=False))
    return 0 if res["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
