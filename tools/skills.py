#!/usr/bin/env python3
"""Manage the skills in this repository.

    python tools/skills.py new <name> [--category qa] [--media video] [--description "..."] [--from <skill>]
    python tools/skills.py validate              # check every skill under skills/
    python tools/skills.py index                 # rebuild the skill list in README.md
    python tools/skills.py index --check         # fail if README.md is out of date (used by CI)
    python tools/skills.py package [name ...]    # build dist/<name>.skill (all skills if no name)
    python tools/skills.py list

Every skill lives in its own folder: skills/<name>/SKILL.md (+ scripts/, references/, profiles/, assets/).
Nothing here is hard-coded to a particular skill — add a folder and the index, checks and packages pick it
up. The category comes from the SKILL.md frontmatter (metadata.category); QA skills use "qa".
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("PyYAML is needed: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
TEMPLATES = ROOT / "templates"
DIST = ROOT / "dist"
README = ROOT / "README.md"
BEGIN, END = "<!-- skills:begin -->", "<!-- skills:end -->"
ALLOWED = {"name", "description", "license", "allowed-tools", "metadata", "compatibility"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CATEGORY_TITLES = {"qa": "Quality assurance (QA)", "content": "Content creation", "automation": "Automation",
                   "other": "Other"}
SKIP = {"__pycache__", ".DS_Store"}


def frontmatter(skill_md: Path) -> tuple[dict, str]:
    text = skill_md.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if not m:
        raise ValueError("SKILL.md must start with a --- frontmatter block")
    data = yaml.safe_load(m.group(1)) or {}
    if not isinstance(data, dict):
        raise ValueError("frontmatter is not a key: value mapping")
    return data, m.group(2)


def skill_dirs() -> list[Path]:
    return sorted(p for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith(".")) if SKILLS.exists() else []


def meta(fm: dict) -> dict:
    return fm.get("metadata") or {}


# ------------------------------------------------------------------------------------------------- validate
def check_skill(d: Path) -> list[str]:
    errs = []
    md = d / "SKILL.md"
    if not md.exists():
        return [f"{d.name}: no SKILL.md"]
    try:
        fm, body = frontmatter(md)
    except (ValueError, yaml.YAMLError) as e:
        return [f"{d.name}: {e}"]
    extra = set(fm) - ALLOWED
    if extra:
        errs.append(f"{d.name}: frontmatter keys {sorted(extra)} aren't allowed (use {sorted(ALLOWED)}; "
                    f"put anything else under metadata:)")
    name = fm.get("name")
    if name != d.name:
        errs.append(f"{d.name}: frontmatter name '{name}' must equal the folder name")
    if not isinstance(name, str) or not NAME_RE.match(name or "") or len(name) > 64:
        errs.append(f"{d.name}: name must be lowercase-with-hyphens, ≤ 64 characters")
    desc = fm.get("description")
    if not isinstance(desc, str) or not desc.strip():
        errs.append(f"{d.name}: description is missing")
    elif len(desc) > 1024:
        errs.append(f"{d.name}: description is {len(desc)} characters (max 1024)")
    elif "<" in desc or ">" in desc:
        errs.append(f"{d.name}: description can't contain angle brackets")
    if "TODO" in (desc or "") or "TODO" in body:
        errs.append(f"{d.name}: still has TODOs from the template")
    if not meta(fm).get("category"):
        errs.append(f"{d.name}: add metadata.category (e.g. qa) so the index can group it")
    if len(body.splitlines()) > 500:
        errs.append(f"{d.name}: SKILL.md body is over 500 lines — move detail into references/")
    # every file SKILL.md points at must exist
    for ref in sorted(set(re.findall(r"`((?:scripts|references|profiles|assets)/[\w./-]+\.\w+)`", body))):
        if not (d / ref).exists():
            errs.append(f"{d.name}: SKILL.md mentions {ref}, which doesn't exist")
    for py in d.rglob("*.py"):
        try:
            compile(py.read_text(encoding="utf-8"), str(py), "exec")
        except SyntaxError as e:
            errs.append(f"{d.name}: {py.relative_to(d)} has a syntax error: {e}")
    for js in d.rglob("*.json"):
        import json
        try:
            json.loads(js.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            errs.append(f"{d.name}: {js.relative_to(d)} is not valid JSON: {e}")
    return errs


def cmd_validate(_: argparse.Namespace) -> int:
    dirs = skill_dirs()
    errs = [e for d in dirs for e in check_skill(d)]
    for e in errs:
        print("ERROR:", e)
    print(f"{len(dirs)} skill(s) checked — " + ("FAILED" if errs else "all OK"))
    return 1 if errs else 0


# ------------------------------------------------------------------------------------------------- index
def short(desc: str, n: int = 170) -> str:
    desc = re.sub(r"^Also called [^.]*\.\s*", "", desc.strip())
    first = re.split(r"(?<=[.!?])\s", desc.strip(), maxsplit=1)[0]
    return first if len(first) <= n else first[: n - 1].rstrip() + "…"


def build_index() -> str:
    groups: dict[str, list[tuple[str, dict, dict]]] = {}
    for d in skill_dirs():
        try:
            fm, _ = frontmatter(d / "SKILL.md")
        except Exception:  # noqa: BLE001 - validate reports it
            continue
        groups.setdefault(meta(fm).get("category", "other"), []).append((d.name, fm, meta(fm)))
    if not groups:
        return "_No skills yet — run `python tools/skills.py new <name>` to add one._"
    out = []
    order = [c for c in CATEGORY_TITLES if c in groups] + sorted(c for c in groups if c not in CATEGORY_TITLES)
    for cat in order:
        out += [f"### {CATEGORY_TITLES.get(cat, cat.title())}", "",
                "| Skill | Name | What it does | Media | Projects | Version |", "|---|---|---|---|---|---|"]
        for name, fm, m in groups[cat]:
            projects = ", ".join(m.get("projects") or []) or "any"
            out.append(f"| [`{name}`](skills/{name}/SKILL.md) | {m.get('persona', '–')} | {short(fm.get('description', ''))} | "
                       f"{m.get('media', '–')} | {projects} | {m.get('version', '–')} |")
        out.append("")
    return "\n".join(out).rstrip()


def cmd_index(args: argparse.Namespace) -> int:
    text = README.read_text(encoding="utf-8")
    if BEGIN not in text or END not in text:
        sys.exit(f"README.md needs the markers {BEGIN} and {END}")
    a, b = text.index(BEGIN) + len(BEGIN), text.index(END)
    new = text[:a] + "\n" + build_index() + "\n" + text[b:]
    if args.check:
        if new != text:
            print("README.md skill list is out of date — run: python tools/skills.py index")
            return 1
        print("README.md skill list is up to date")
        return 0
    README.write_text(new, encoding="utf-8")
    print("README.md skill list updated")
    return 0


# ------------------------------------------------------------------------------------------------- new
def cmd_new(args: argparse.Namespace) -> int:
    name = args.name
    if not NAME_RE.match(name) or len(name) > 64:
        sys.exit("name must be lowercase-with-hyphens, ≤ 64 characters (e.g. thumbnail-qa)")
    dest = SKILLS / name
    if dest.exists():
        sys.exit(f"skills/{name} already exists")
    if args.copy_from:
        src = SKILLS / args.copy_from
        if not src.exists():
            sys.exit(f"skills/{args.copy_from} not found")
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(*SKIP))
        md = dest / "SKILL.md"
        md.write_text(re.sub(r"^name: .*$", f"name: {name}", md.read_text(encoding="utf-8"), count=1, flags=re.M),
                      encoding="utf-8")
        print(f"created skills/{name} as a copy of {args.copy_from} — now edit its description and checks")
        return 0
    tpl = TEMPLATES / ("qa-skill" if args.category == "qa" else "basic-skill")
    if not tpl.exists():
        tpl = TEMPLATES / "qa-skill"
    shutil.copytree(tpl, dest, ignore=shutil.ignore_patterns(*SKIP))
    title = " ".join(w.upper() if w == "qa" else w.capitalize() for w in name.split("-"))
    subs = {"{{name}}": name, "{{title}}": title, "{{category}}": args.category, "{{media}}": args.media,
            "{{description}}": args.description or "TODO: one or two sentences — what it checks and when to use it"}
    for f in dest.rglob("*"):
        if f.is_file() and f.suffix in {".md", ".py", ".json", ".txt", ".yaml"}:
            t = f.read_text(encoding="utf-8")
            for k, v in subs.items():
                t = t.replace(k, v)
            f.write_text(t, encoding="utf-8")
    print(f"created skills/{name} from templates/{tpl.name}. Next: fill in the TODOs, then\n"
          f"  python tools/skills.py validate && python tools/skills.py index")
    return 0


# ------------------------------------------------------------------------------------------------- package
def cmd_package(args: argparse.Namespace) -> int:
    names = args.names or [d.name for d in skill_dirs()]
    DIST.mkdir(exist_ok=True)
    bad = 0
    for n in names:
        d = SKILLS / n
        errs = check_skill(d) if d.exists() else [f"{n}: not found"]
        if errs:
            bad += 1
            print("\n".join("ERROR: " + e for e in errs))
            continue
        out = DIST / f"{n}.skill"
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(d.rglob("*")):
                if f.is_file() and not (set(f.relative_to(d).parts) & SKIP) and f.suffix != ".pyc":
                    z.write(f, Path(n) / f.relative_to(d))
        print(f"packaged {out.relative_to(ROOT)}")
    return 1 if bad else 0


def cmd_list(_: argparse.Namespace) -> int:
    for d in skill_dirs():
        try:
            fm, _ = frontmatter(d / "SKILL.md")
            m = meta(fm)
            print(f"{d.name:28} {m.get('category', '?'):10} {m.get('version', '–'):8} {short(fm.get('description', ''), 80)}")
        except Exception as e:  # noqa: BLE001
            print(f"{d.name:28} (broken: {e})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="create a skill from a template (or copy an existing one)")
    p.add_argument("name")
    p.add_argument("--category", default="qa")
    p.add_argument("--media", default="video", help="what it checks: video, image, audio, text, …")
    p.add_argument("--description")
    p.add_argument("--from", dest="copy_from", help="copy an existing skill instead of the template")
    p.set_defaults(fn=cmd_new)
    sub.add_parser("validate").set_defaults(fn=cmd_validate)
    p = sub.add_parser("index")
    p.add_argument("--check", action="store_true")
    p.set_defaults(fn=cmd_index)
    p = sub.add_parser("package")
    p.add_argument("names", nargs="*")
    p.set_defaults(fn=cmd_package)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
