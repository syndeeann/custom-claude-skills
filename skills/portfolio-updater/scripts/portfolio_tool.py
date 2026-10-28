#!/usr/bin/env python3
"""Keep a static portfolio site's AI Studio in step with delivered work.

    portfolio_tool.py [--site DIR] [--profile NAME|PATH] <command> ...

    classify     --project P [--title T] [--text T]            which studio does this belong in?
    add          --run-dir DIR | --title T ...                  add one delivered video or app
    sync-skills  --skills-repo DIR                              rebuild data/skills.json from the skills repo
    new-studio   --id ID --name N --tagline T [--kind video|app] [--keywords a,b]
    build-pages                                                 (re)generate every studio page from the template
    check                                                       verify the data, the pages and the hooks
    publish      --message M [--dry-run]                        commit and push to the live branch(es)

The site is a static page set that renders data/*.json in the browser (assets/studio.js). Nothing here knows
about a particular project: project rules live in profiles/<site>.json and the site's own data/*.json.
The NEW badge is not stored. The browser works it out from "published", so it switches itself off after
new_badge_days with no redeploy.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
TEMPLATE = SKILL / "assets" / "studio-page.html"
DEFAULT_FONTS = "family=Sora:wght@400;600;700;800&family=Geist:wght@400;500;600&family=Geist+Mono:wght@400;500"
DATA_FILES = ("studios", "projects", "videos", "skills", "workflow")
YT_RE = re.compile(r"youtu(?:\.be/|be\.com/(?:shorts/|watch\?v=|embed/))([\w-]{11})")
ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ------------------------------------------------------------------------------------------------- helpers
def die(msg: str, code: int = 2) -> "None":
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        die(f"{path} is not valid JSON: {e}")


def write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


class Site:
    def __init__(self, root: Path, profile: dict):
        self.root, self.profile = root, profile

    def data(self, name: str) -> Path:
        return self.root / "data" / f"{name}.json"

    def load(self, name: str, default):
        return read_json(self.data(name), default)

    def studios(self) -> list[dict]:
        return self.load("studios", {"studios": []}).get("studios", [])

    def new_days(self) -> int:
        return int(self.load("studios", {}).get("newBadgeDays") or self.profile.get("new_badge_days") or 7)


def load_profile(arg: str | None) -> dict:
    if not arg:
        return {}
    p = Path(arg)
    if not p.exists():
        p = SKILL / "profiles" / (arg if arg.endswith(".json") else f"{arg}.json")
    if not p.exists():
        die(f"profile '{arg}' not found (looked for {p})")
    return read_json(p, {})


def slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "item"


def sentence(text: str) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    if not t:
        return ""
    t = t[0].upper() + t[1:]
    return t if t[-1] in ".!?" else t + "."


def mmss(seconds: float | None) -> str:
    if not seconds:
        return ""
    s = round(seconds)
    return f"{s // 60}:{s % 60:02d}"


def js(value) -> str:
    """A JavaScript string/number literal for injection into a hand-written page."""
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


# ------------------------------------------------------------------------------------------------- classify
def classify(site: Site, project: str | None, text: str) -> tuple[str | None, str]:
    """Return (studio_id, why). The project's studio wins; otherwise keywords decide; otherwise None."""
    studios = site.studios()
    ids = {s["id"] for s in studios}
    proj = (site.profile.get("projects") or {}).get(project or "") or (site.load("projects", {}).get("projects") or {}).get(project or "")
    if proj and proj.get("studio") in ids:
        return proj["studio"], f"project '{project}' is assigned to this studio"
    best, best_score, hits = None, 0, []
    low = text.lower()
    for s in studios:
        score, found = 0, []
        for kw in s.get("keywords", []):
            if re.search(rf"(?<![a-z0-9]){re.escape(kw.lower())}(?![a-z0-9])", low):
                score += 2 if " " in kw else 1
                found.append(kw)
        if score > best_score:
            best, best_score, hits = s["id"], score, found
    if best:
        return best, "matched keywords: " + ", ".join(hits)
    return None, "no keyword matched"


def cmd_classify(site: Site, a: argparse.Namespace) -> int:
    studio, why = classify(site, a.project, f"{a.title or ''} {a.text or ''}")
    print(json.dumps({"studio": studio, "why": why}, ensure_ascii=False))
    return 0 if studio else 1


# ------------------------------------------------------------------------------------------------- add
def read_run_dir(run: Path, delivered_status: str) -> dict:
    brief = read_json(run / "brief.json", {})
    if not brief:
        die(f"{run} has no brief.json: is this a run folder?")
    log = (run / "run-log.md").read_text(encoding="utf-8") if (run / "run-log.md").exists() else ""
    posted = re.search(rf"^- (\d{{4}}-\d{{2}}-\d{{2}})[^\n]*status '{re.escape(delivered_status)}'", log, re.M)
    yt = YT_RE.search(log)
    dur = re.search(r"Assembled:\s*([\d.]+)\s*s", log)
    folder_day = re.match(r"^(\d{4}-\d{2}-\d{2})-", run.name)
    return {
        "brief": brief,
        "delivered": bool(posted),
        "published": posted.group(1) if posted else (folder_day.group(1) if folder_day else None),
        "youtube": yt.group(1) if yt else None,
        "duration_s": round(float(dur.group(1))) if dur else (int(brief["length_seconds"]) if str(brief.get("length_seconds", "")).isdigit() else None),
        "topic_id": brief.get("topic_id") or run.name,
    }


def cmd_add(site: Site, a: argparse.Namespace) -> int:
    info = {"brief": {}, "delivered": True, "published": None, "youtube": None, "duration_s": None, "topic_id": None}
    if a.run_dir:
        info = read_run_dir(Path(a.run_dir), site.profile.get("delivered_status", "posted"))
        if not info["delivered"] and not a.allow_undelivered:
            die(f"{a.run_dir} is not delivered (no '{site.profile.get('delivered_status', 'posted')}' status in run-log.md). "
                f"Nothing was added. Use --allow-undelivered only if the owner says it is live.", 3)
    brief = info["brief"]
    project = a.project or (brief.get("project") if brief else None)
    if not project and brief:  # the profile says which brief fields identify a project
        for slug_, cfg_ in (site.profile.get("projects") or {}).items():
            m_ = cfg_.get("brief_match") or {}
            if m_ and all(str(brief.get(k, "")) == v for k, v in m_.items()):
                project = slug_
                break
    if not project:
        die("--project is required (the project slug, e.g. kwento-kilabot)")
    pcfg = (site.profile.get("projects") or {}).get(project, {})

    topic = brief.get("topic", "")
    title, desc, num = a.title, a.description, None
    rx = pcfg.get("title_regex")
    if rx and topic:
        m = re.match(rx, topic)
        if m:
            gd = m.groupdict()
            title = title or gd.get("title")
            desc = desc or sentence(gd.get("desc", ""))
            num = gd.get("n")
    title = title or topic or (info["topic_id"] or "").replace("-", " ").title()
    if not title:
        die("could not work out a title; pass --title")
    desc = desc or sentence(topic)

    youtube = a.youtube or info["youtube"]
    if youtube and (m := YT_RE.search(youtube)):
        youtube = m.group(1)
    if youtube and not re.fullmatch(r"[\w-]{11}", youtube):
        die(f"'{youtube}' is not a YouTube id or URL")
    published = a.published or info["published"] or date.today().isoformat()
    if not DATE_RE.match(published):
        die("--published must be YYYY-MM-DD")
    kind = a.type
    studio_id = a.studio
    why = "set with --studio"
    if not studio_id:
        studio_id, why = classify(site, project, f"{title} {desc} {topic} {brief.get('folklore', '')}")
    if not studio_id:
        die("could not classify this item. Re-run with --studio <id>. Studios: " + ", ".join(s["id"] for s in site.studios()), 4)
    studio = next((s for s in site.studios() if s["id"] == studio_id), None)
    if not studio:
        die(f"unknown studio '{studio_id}'")
    kind = kind or studio.get("kind", "video")

    item = {
        "id": a.id or f"{project}-{info['topic_id'] or slug(title)}",
        "studio": studio_id, "project": project, "type": kind,
        "title": title, "description": desc, "published": published,
        "language": a.language or pcfg.get("language") or brief.get("language"),
        "duration_s": a.duration or info["duration_s"],
        "youtube": youtube, "facebook": a.facebook, "tiktok": a.tiktok, "instagram": a.instagram,
        "link": a.link, "repo": a.repo, "poster": a.poster, "src": a.src,
        "platforms": [p.strip() for p in a.platforms.split(",")] if a.platforms else None,
        "skills": [s.strip() for s in a.skills.split(",")] if a.skills else None,
    }
    item = {k: v for k, v in item.items() if v not in (None, "", [])}
    if kind == "video" and not any(item.get(k) for k in ("youtube", "src", "facebook", "tiktok", "instagram", "link")):
        print("WARNING: no playable link yet; the card shows without a play button until you add one.", file=sys.stderr)

    path = site.data("videos")
    db = read_json(path, {"items": []})
    items = db.setdefault("items", [])
    existing = next((i for i in items if i.get("id") == item["id"]), None)
    if existing:
        if not a.republish:
            item["published"] = existing.get("published", item["published"])  # keep the first publish date: the badge must not restart
        existing.clear()
        existing.update(item)
        verb = "updated"
    else:
        items.append(item)
        verb = "added"
    items.sort(key=lambda i: (i.get("published", ""), i.get("id", "")), reverse=True)
    write_json(path, db)

    legacy = (site.profile.get("legacy_pages") or {}).get(studio_id)
    if legacy and kind == "video":
        inject_legacy(site, legacy, item, brief, a.folk, num)
    print(f"{verb} {item['id']} -> {studio['name']} ({why}); published {item['published']}")
    return 0


def inject_legacy(site: Site, cfg: dict, item: dict, brief: dict, folk: str | None, num: str | None) -> None:
    """Hand-built studio pages keep their own list of videos between two marker comments. Keep it in step."""
    page = site.root / cfg["page"]
    if not page.exists():
        print(f"WARNING: legacy page {cfg['page']} not found; skipped", file=sys.stderr)
        return
    text = page.read_text(encoding="utf-8")
    b, e = cfg["begin"], cfg["end"]
    if b not in text or e not in text:
        print(f"WARNING: {cfg['page']} has no {b} ... {e} markers; add them around the video list once", file=sys.stderr)
        return
    head, rest = text.split(b, 1)
    body, tail = rest.split(e, 1)
    lines = [ln for ln in body.splitlines() if ln.strip()]
    yt = item.get("youtube", "")
    at = next((i for i, ln in enumerate(lines) if yt and (f"'{yt}'" in ln or f'"{yt}"' in ln)), None)
    folklore = folk or re.split(r"\s[(—-]", brief.get("folklore", ""))[0].strip() or item.get("project", "")
    fields = {
        "n": num or str(len([ln for ln in lines if "id:" in ln]) + 1),
        "youtube_id_js": js(item.get("youtube", "")), "title_js": js(item["title"]), "folk_js": js(folklore),
        "dur_js": js(mmss(item.get("duration_s"))), "desc_js": js(item.get("description", "")),
        "published_js": js(item["published"]),
    }
    line = cfg["line"]
    for k, v in fields.items():
        line = line.replace("{" + k + "}", v)
    if at is not None:
        keep = re.search(r"\burl:\s*(?:'[^']*'|\"[^\"]*\"),?", lines[at])  # a hand-set watch link survives the update
        if keep and "url:" not in line:
            line = line.replace(f"id: {js(yt)},", f"id: {js(yt)}, {keep.group(0).rstrip(',')},", 1)
        lines[at] = line  # already listed: update it where it stands
    else:
        lines = [line] + lines if cfg.get("newest_first", True) else lines + [line]
    page.write_text(head + b + "\n" + "\n".join(lines) + "\n  " + e + tail, encoding="utf-8")


# ------------------------------------------------------------------------------------------------- skills
def read_frontmatter(md: Path) -> tuple[dict, str]:
    try:
        import yaml
    except ImportError:
        die("PyYAML is needed: pip install pyyaml")
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", md.read_text(encoding="utf-8"), re.S)
    if not m:
        die(f"{md} has no frontmatter")
    return yaml.safe_load(m.group(1)) or {}, m.group(2)


def cmd_sync_skills(site: Site, a: argparse.Namespace) -> int:
    repo = Path(a.skills_repo)
    base = a.repo_url or site.profile.get("skills_repo") or ""
    out = []
    for d in sorted((repo / "skills").iterdir()):
        md = d / "SKILL.md"
        if not md.exists():
            continue
        fm, _ = read_frontmatter(md)
        m = fm.get("metadata") or {}
        desc = re.sub(r"\s+", " ", str(fm.get("description", ""))).strip()
        first = re.split(r"(?<=[.!?])\s", desc)[0] if desc else ""
        out.append({
            "id": d.name,
            "name": m.get("title") or d.name.replace("-", " ").title(),
            "role": m.get("role") or str(m.get("category", "")).title(),
            "summary": m.get("summary") or first,
            "responsibilities": list(m.get("responsibilities") or []),
            "projects": list(m.get("projects") or []),
            "category": m.get("category", ""),
            "version": str(m.get("version", "")),
            "order": int(m.get("order", 100)),
            "url": f"{base}/tree/main/skills/{d.name}" if base else "",
        })
    out.sort(key=lambda s: (s["order"], s["id"]))
    write_json(site.data("skills"), {"repo": base, "generated": date.today().isoformat(), "skills": out})
    print(f"wrote data/skills.json with {len(out)} skill(s): " + ", ".join(s["id"] for s in out))
    missing = [s["id"] for s in out if not s["responsibilities"] or not s["projects"]]
    if missing:
        print("WARNING: no responsibilities/projects in metadata for: " + ", ".join(missing), file=sys.stderr)
    return 0


# ------------------------------------------------------------------------------------------------- studios + pages
def render_page(site: Site, studio: dict) -> str:
    t = TEMPLATE.read_text(encoding="utf-8")
    depth = len([p for p in studio["path"].strip("/").split("/") if p])
    base = "/".join([".."] * depth) or "."
    analytics = '<script src="%s/assets/analytics.js"></script>' % base if (site.root / "assets" / "analytics.js").exists() else ""
    rep = {
        "NAME": html.escape(studio["name"]), "TAGLINE": html.escape(studio.get("tagline", "")),
        "DESCRIPTION": html.escape(studio.get("description") or studio.get("tagline", "")),
        "ID": html.escape(studio["id"]), "BASE": base, "ANALYTICS": analytics,
        "SITE_URL": html.escape(site.profile.get("site_url", "")), "SKILLS_REPO": html.escape(site.profile.get("skills_repo", "")),
        "NOUN": "apps" if studio.get("kind") == "app" else "videos",
        "THEME": html.escape(studio.get("theme") or "default"),
        "FONTS": html.escape(studio.get("fonts") or DEFAULT_FONTS, quote=False),
        "BADGE_HTML": '<span class="hero-badge">%s</span>' % html.escape(studio["badge"]) if studio.get("badge") else "",
        "TICKER_HTML": ('<div class="ticker" aria-hidden="true"><span>%s</span></div>' % html.escape((studio["ticker"] + "  ") * 12)) if studio.get("ticker") else "",
    }
    for k, v in rep.items():
        t = t.replace("{{" + k + "}}", v)
    return t


def cmd_build_pages(site: Site, _: argparse.Namespace) -> int:
    n = 0
    for s in site.studios():
        if s["id"] in (site.profile.get("legacy_pages") or {}) or not s["path"].endswith("/"):
            print(f"skip {s['id']}: hand-built page at {s['path']}")
            continue
        out = site.root / s["path"] / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(render_page(site, s), encoding="utf-8")
        n += 1
        print(f"wrote {s['path']}index.html")
    print(f"{n} studio page(s) generated")
    return 0


def cmd_new_studio(site: Site, a: argparse.Namespace) -> int:
    if not ID_RE.match(a.id):
        die("--id must be lowercase-with-hyphens")
    db = read_json(site.data("studios"), {"newBadgeDays": site.new_days(), "studios": []})
    if any(s["id"] == a.id for s in db["studios"]):
        die(f"studio '{a.id}' already exists")
    studio = {
        "id": a.id, "name": a.name, "tagline": a.tagline, "description": a.description or a.tagline,
        "path": f"{a.id}/", "kind": a.kind, "pipeline": a.pipeline or a.id, "icon": a.icon or a.id,
        "keywords": [k.strip().lower() for k in (a.keywords or "").split(",") if k.strip()],
    }
    for key in ("theme", "accent", "fonts", "badge", "ticker"):
        if getattr(a, key, None):
            studio[key] = getattr(a, key)
    db["studios"].append(studio)
    write_json(site.data("studios"), db)
    print(f"added studio '{a.id}'. Next: add its pipeline to data/workflow.json, run build-pages, then link it from index.html if needed.")
    return cmd_build_pages(site, a)


# ------------------------------------------------------------------------------------------------- check
def cmd_check(site: Site, _: argparse.Namespace) -> int:
    errs, warns = [], []
    d = {n: read_json(site.data(n), None) for n in DATA_FILES}
    for n in DATA_FILES:
        if d[n] is None:
            errs.append(f"data/{n}.json is missing")
    if errs:
        return report(errs, warns)
    studios = {s["id"]: s for s in d["studios"]["studios"]}
    skills = {s["id"] for s in d["skills"]["skills"]}
    pipes = d["workflow"]["pipelines"]
    days = site.new_days()
    for s in studios.values():
        for need in ("id", "name", "tagline", "path", "kind", "pipeline"):
            if not s.get(need):
                errs.append(f"studio {s.get('id')}: missing '{need}'")
        page = site.root / s["path"]
        if s["path"].endswith("/"):
            page = page / "index.html"
        if not page.exists():
            errs.append(f"studio {s['id']}: page {s['path']} does not exist (run build-pages)")
        if s.get("pipeline") not in pipes:
            errs.append(f"studio {s['id']}: pipeline '{s.get('pipeline')}' is not in workflow.json")
    for pid, p in pipes.items():
        for st in p.get("steps", []):
            for sk in st.get("skills", []):
                if sk not in skills:
                    errs.append(f"workflow {pid}: step '{st.get('title')}' uses skill '{sk}', which is not in skills.json (run sync-skills)")
    seen, fresh = set(), 0
    for i in d["videos"]["items"]:
        iid = i.get("id", "?")
        if iid in seen:
            errs.append(f"duplicate item id {iid}")
        seen.add(iid)
        if i.get("studio") not in studios:
            errs.append(f"{iid}: unknown studio '{i.get('studio')}'")
        if i.get("project") not in d["projects"]["projects"]:
            warns.append(f"{iid}: project '{i.get('project')}' is not in projects.json (shown by its slug)")
        if not DATE_RE.match(i.get("published", "")):
            errs.append(f"{iid}: published must be YYYY-MM-DD")
        elif 0 <= (date.today() - datetime.strptime(i["published"], "%Y-%m-%d").date()).days <= days:
            fresh += 1
        if i.get("youtube") and not re.fullmatch(r"[\w-]{11}", i["youtube"]):
            errs.append(f"{iid}: youtube must be the 11-character id")
        if not i.get("title"):
            errs.append(f"{iid}: missing title")
    for sid, cfg in (site.profile.get("legacy_pages") or {}).items():
        pg = site.root / cfg["page"]
        if pg.exists():
            txt = pg.read_text(encoding="utf-8")
            if cfg["begin"] not in txt or cfg["end"] not in txt:
                errs.append(f"{cfg['page']}: markers {cfg['begin']} / {cfg['end']} missing")
            for i in d["videos"]["items"]:
                if i.get("studio") == sid and i.get("youtube") and i["youtube"] not in txt:
                    warns.append(f"{cfg['page']} does not list {i['id']} yet")
    idx = site.root / "index.html"
    if idx.exists():
        t = idx.read_text(encoding="utf-8")
        for hook in ("data-studio-grid", "data-skills", "assets/studio.js", "assets/studio.css"):
            if hook not in t:
                errs.append(f"index.html is missing '{hook}'")
        if "github.com/" not in t:
            warns.append("index.html has no GitHub link")
    else:
        errs.append("index.html is missing")
    print(f"{len(d['videos']['items'])} item(s), {fresh} inside the {days}-day NEW window, {len(studios)} studio(s), {len(skills)} skill(s)")
    return report(errs, warns)


def report(errs: list[str], warns: list[str]) -> int:
    for w in warns:
        print("WARN :", w)
    for e in errs:
        print("ERROR:", e)
    print("FAILED" if errs else "OK")
    return 1 if errs else 0


# ------------------------------------------------------------------------------------------------- publish
def git(site: Site, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(site.root), *args], capture_output=True, text=True, check=check)


def cmd_publish(site: Site, a: argparse.Namespace) -> int:
    if cmd_check(site, a) != 0:
        die("check failed; fix it before publishing", 1)
    branches = site.profile.get("live_branches") or ["main"]
    git(site, "add", "-A")
    if not git(site, "status", "--porcelain").stdout.strip():
        print("nothing to publish")
        return 0
    if a.dry_run:
        print(git(site, "status", "--short").stdout, "\n(dry run) would push to:", ", ".join(branches))
        return 0
    git(site, "commit", "-m", a.message)
    for b in branches:
        r = git(site, "push", "origin", f"HEAD:{b}", check=False)
        if r.returncode:
            die(f"push to {b} failed: {r.stderr.strip()}", 1)
        print(f"pushed to {b}")
    if site.profile.get("site_url"):
        print("live at", site.profile["site_url"], "(GitHub Pages can take a minute or two)")
    return 0


# ------------------------------------------------------------------------------------------------- cli
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--site", default=".", help="the portfolio repo (default: current folder)")
    ap.add_argument("--profile", help="profile name in profiles/ or a path to a profile JSON")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("classify")
    c.add_argument("--project"); c.add_argument("--title"); c.add_argument("--text")
    c.set_defaults(fn=cmd_classify)

    c = sub.add_parser("add")
    c.add_argument("--run-dir"); c.add_argument("--project"); c.add_argument("--studio"); c.add_argument("--id")
    c.add_argument("--type", choices=["video", "app"]); c.add_argument("--title"); c.add_argument("--description")
    c.add_argument("--published"); c.add_argument("--language"); c.add_argument("--duration", type=int)
    c.add_argument("--youtube"); c.add_argument("--facebook"); c.add_argument("--tiktok"); c.add_argument("--instagram")
    c.add_argument("--link", help="live app or watch page"); c.add_argument("--repo", help="source code"); c.add_argument("--poster"); c.add_argument("--src")
    c.add_argument("--platforms", help="apps: comma list, e.g. Web,Android"); c.add_argument("--skills", help="comma list of skill ids used, if different from the studio's workflow")
    c.add_argument("--folk", help="short label for a hand-built page, e.g. the folklore creature")
    c.add_argument("--allow-undelivered", action="store_true"); c.add_argument("--republish", action="store_true", help="restart the NEW window")
    c.set_defaults(fn=cmd_add)

    c = sub.add_parser("sync-skills")
    c.add_argument("--skills-repo", required=True); c.add_argument("--repo-url")
    c.set_defaults(fn=cmd_sync_skills)

    c = sub.add_parser("new-studio")
    c.add_argument("--id", required=True); c.add_argument("--name", required=True); c.add_argument("--tagline", required=True)
    c.add_argument("--description"); c.add_argument("--kind", choices=["video", "app"], default="video")
    c.add_argument("--pipeline"); c.add_argument("--icon"); c.add_argument("--keywords")
    c.add_argument("--theme", help="a theme in assets/themes.css (ads, kids, apps, or your own)"); c.add_argument("--accent", help="tile accent as R, G, B")
    c.add_argument("--fonts", help="Google Fonts query, e.g. family=Anton&family=Manrope:wght@400;700"); c.add_argument("--badge"); c.add_argument("--ticker")
    c.set_defaults(fn=cmd_new_studio)

    sub.add_parser("build-pages").set_defaults(fn=cmd_build_pages)
    sub.add_parser("check").set_defaults(fn=cmd_check)

    c = sub.add_parser("publish")
    c.add_argument("--message", required=True); c.add_argument("--dry-run", action="store_true")
    c.set_defaults(fn=cmd_publish)

    a = ap.parse_args()
    site = Site(Path(a.site).resolve(), load_profile(a.profile))
    return a.fn(site, a)


if __name__ == "__main__":
    sys.exit(main())
