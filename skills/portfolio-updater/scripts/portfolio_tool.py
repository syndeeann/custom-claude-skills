#!/usr/bin/env python3
"""Keep a static portfolio site's AI Studio in step with delivered work.

    portfolio_tool.py [--site DIR] [--profile NAME|PATH] <command> ...

    classify     --project P [--title T] [--text T]            which studio does this belong in?
    add          --run-dir DIR | --title T ...                  add one delivered video or app
    sync-skills  --skills-repo DIR                              rebuild data/skills.json and data/team.json from the skills repo
    new-studio   --id ID --name N --tagline T [--kind video|app] [--keywords a,b]
    build-pages                                                 (re)generate every studio page from the template
    check                                                       verify the data, the pages and the hooks
    analytics    sync | check | confirm [--gtm --ga4 --looker]   keep analytics, Tag Manager export and Looker guide current
    publish      --message M [--dry-run]                        sync analytics, check, commit, push to the live branch(es)

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
            "persona": str(m.get("persona", "")),
        })
    out.sort(key=lambda s: (s["order"], s["id"]))
    write_json(site.data("skills"), {"repo": base, "generated": date.today().isoformat(), "skills": out})
    print(f"wrote data/skills.json with {len(out)} skill(s): " + ", ".join(s["id"] for s in out))
    missing = [s["id"] for s in out if not s["responsibilities"] or not s["projects"]]
    if missing:
        print("WARNING: no responsibilities/projects in metadata for: " + ", ".join(missing), file=sys.stderr)
    sync_team(site, out)
    return 0


AVATAR_COLORS = [("#a5f3fc", "#818cf8"), ("#fde68a", "#f472b6"), ("#bbf7d0", "#38bdf8"), ("#fecaca", "#c084fc")]


def sync_team(site: Site, skills: list) -> None:
    """Give every skill that has a metadata.persona a seat in data/team.json (the 'Team I built' section).
    Existing members are never replaced, so hand-drawn avatars and titles survive. A new member gets a simple
    initial badge as its avatar, saved to assets/team/, which the owner can swap for a drawn one."""
    path = site.data("team")
    doc = read_json(path, {"note": "Teammate personas for the Claude skills in skills.json, matched by skill id.", "members": {}})
    members = doc.setdefault("members", {})
    added, renamed = [], []
    for i, s in enumerate(skills):
        name = s.get("persona")
        if not name:
            continue
        cur = members.get(s["id"])
        if cur:
            if cur.get("name") != name:
                cur["name"] = name
                renamed.append(f"{s['id']} -> {name}")
            continue
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        rel = f"assets/team/{slug}.svg"
        svg = site.root / rel
        if not svg.exists():
            a, b = AVATAR_COLORS[i % len(AVATAR_COLORS)]
            label = html.escape(f"{name}, {s['name']}")
            svg.parent.mkdir(parents=True, exist_ok=True)
            svg.write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" role="img" aria-label="{label}">'
                f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/>'
                f'<stop offset="1" stop-color="{b}"/></linearGradient></defs><circle cx="60" cy="60" r="60" fill="url(#g)"/>'
                f'<text x="60" y="76" text-anchor="middle" font-family="Sora, Arial, sans-serif" font-size="52" '
                f'font-weight="800" fill="#0c1024">{html.escape(name[0].upper())}</text></svg>\n', encoding="utf-8")
        members[s["id"]] = {"name": name, "title": s["name"], "avatar": rel}
        added.append(name)
    write_json(path, doc)
    if added:
        print("data/team.json: added " + ", ".join(added) + " (initial-badge avatar; swap in a drawn one in assets/team/ if wanted)")
    if renamed:
        print("data/team.json: renamed " + ", ".join(renamed))
    if not added and not renamed:
        print("data/team.json already matches the skills' personas")


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
        "WORKFLOW": workflow_name(studio),
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
    for c in analytics(site, write=True)[0]:
        print("changed:", c)
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
    a_changes, a_pending, a_errors = analytics(site, write=False)
    errs += a_errors
    errs += [f"analytics out of date: {c} (run: analytics sync)" for c in a_changes]
    warns += [f"manual step pending: {p_}" for p_ in a_pending]
    return report(errs, warns)


def report(errs: list[str], warns: list[str]) -> int:
    for w in warns:
        print("WARN :", w)
    for e in errs:
        print("ERROR:", e)
    print("FAILED" if errs else "OK")
    return 1 if errs else 0


# ------------------------------------------------------------------------------------------------- analytics
# The site sends events to Google Tag Manager (data layer) -> GA4 -> Looker Studio. This section keeps everything
# that lives in the repo in step with the site: assets/analytics.js (marked blocks only), the Tag Manager container
# export in docs/, and the tracking guide docs/ANALYTICS.md (one marked block). It cannot change GA4, Tag Manager
# or Looker Studio themselves; anything the owner still has to do there is listed as "pending manual steps".
BUILTIN_PARAMS = {"link_text", "link_url", "video_title", "video_url", "video_provider", "video_percent",
                  "video_current_time", "video_duration"}
BASE_PARAMS = ["page_type", "workflow_name", "site_version"]
DOC_BEGIN, DOC_END = "<!-- portfolio-updater:begin -->", "<!-- portfolio-updater:end -->"


def block(text: str, begin: str, end: str, body: str | None = None) -> tuple[str, str | None]:
    """Return (text with the marked block replaced by body, the old body). body None = just read it."""
    i, j = text.find(begin), text.find(end)
    if i < 0 or j < 0 or j < i:
        return text, None
    old = text[i + len(begin):j]
    if body is None:
        return text, old
    return text[:i + len(begin)] + body + text[j:], old


def workflow_name(studio: dict) -> str:
    return studio.get("analytics_name") or studio["id"].replace("-", "_")


def gtm_file(site: Site) -> Path | None:
    found = sorted((site.root / "docs").glob("gtm-container-*.json")) if (site.root / "docs").exists() else []
    return found[0] if found else None


def scan_events(site: Site) -> dict[str, set]:
    """Every event the site's own code sends: name -> parameter names seen next to it."""
    events: dict[str, set] = {}
    pat = re.compile(r"\b(?:track|T)\(\s*'([a-z][a-z0-9_]*)'\s*(?:,\s*\{([^}]*)\})?")
    files = [p for p in list(site.root.rglob("*.js")) + list(site.root.rglob("*.html"))
             if ".git" not in p.parts and "docs" not in p.parts]
    for f in files:
        for m in pat.finditer(f.read_text(encoding="utf-8", errors="ignore")):
            events.setdefault(m.group(1), set()).update(re.findall(r"(\w+)\s*:", m.group(2) or ""))
    return events


def analytics_keys(js_text: str) -> list[str]:
    m = re.search(r"var KEYS = \[(.*?)\];", js_text, re.S)
    return re.findall(r"'([a-z_]+)'", m.group(1)) if m else []


def gtm_new_ids(cv: dict) -> dict:
    mx = lambda key, idk: max([int(x[idk]) for x in cv.get(key, [])] or [0])
    return {"tag": mx("tag", "tagId"), "trigger": mx("trigger", "triggerId"), "variable": mx("variable", "variableId")}


def sync_gtm(site: Site, events: dict[str, set], keys: list[str], write: bool) -> tuple[list[str], list[str]]:
    """Make sure the container export has a trigger + tag per event and a variable per parameter."""
    path = gtm_file(site)
    if not path:
        return [], ["no docs/gtm-container-*.json found, so Tag Manager cannot be checked"]
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    cv = data["containerVersion"]
    ids = gtm_new_ids(cv)
    tags = {t["name"]: t for t in cv["tag"]}
    trigs = {t["name"]: t for t in cv["trigger"]}
    vars_ = {v["name"]: v for v in cv["variable"]}
    changes: list[str] = []
    base_tag = next((t for t in cv["tag"] if t["name"].startswith("GA4 - Event - ")), None)
    base_trig = next((t for t in cv["trigger"] if t["name"].startswith("CE - ")), None)
    base_var = next((v for v in cv["variable"] if v["name"].startswith("DLV - ")), None)
    if not (base_tag and base_trig and base_var):
        return [], ["the container has no example tag, trigger or variable to copy from"]

    def need_var(param: str) -> str:
        if f"DLV - {param}" not in vars_:
            ids["variable"] += 1
            v = json.loads(json.dumps(base_var))
            v.update({"variableId": str(ids["variable"]), "name": f"DLV - {param}"})
            for prm in v["parameter"]:
                if prm["key"] == "name":
                    prm["value"] = param
            cv["variable"].append(v); vars_[v["name"]] = v
            changes.append(f"Tag Manager: added variable DLV - {param}")
        return "{{DLV - %s}}" % param

    for p_ in BASE_PARAMS + [k for k in keys]:
        need_var(p_)
    for ev, seen in sorted(events.items()):
        wanted = [k for k in keys if k in seen and k not in BASE_PARAMS]
        if f"CE - {ev}" not in trigs:
            ids["trigger"] += 1
            tg = json.loads(json.dumps(base_trig))
            tg.update({"triggerId": str(ids["trigger"]), "name": f"CE - {ev}"})
            tg["customEventFilter"][0]["parameter"][1]["value"] = ev
            cv["trigger"].append(tg); trigs[tg["name"]] = tg
            changes.append(f"Tag Manager: added trigger CE - {ev}")
        tag = tags.get(f"GA4 - Event - {ev}")
        if not tag:
            ids["tag"] += 1
            tag = json.loads(json.dumps(base_tag))
            tag.update({"tagId": str(ids["tag"]), "name": f"GA4 - Event - {ev}", "firingTriggerId": [trigs[f"CE - {ev}"]["triggerId"]]})
            for prm in tag["parameter"]:
                if prm["key"] == "eventName":
                    prm["value"] = ev
                if prm["key"] == "eventSettingsTable":
                    prm["list"] = []
            cv["tag"].append(tag); tags[tag["name"]] = tag
            changes.append(f"Tag Manager: added tag GA4 - Event - {ev}")
        table = next(prm for prm in tag["parameter"] if prm["key"] == "eventSettingsTable")
        have = {next(m["value"] for m in row["map"] if m["key"] == "parameter") for row in table["list"]}
        for param in BASE_PARAMS + wanted:
            if param not in have:
                table["list"].append({"type": "MAP", "map": [{"type": "TEMPLATE", "key": "parameter", "value": param},
                                                              {"type": "TEMPLATE", "key": "parameterValue", "value": need_var(param)}]})
                changes.append(f"Tag Manager: GA4 - Event - {ev} now sends {param}")
    if changes and write:
        ascii_ = "\\u00" in raw
        path.write_text(json.dumps(data, indent=1, ensure_ascii=ascii_) + ("\n" if raw.endswith("\n") else ""), encoding="utf-8")
    return changes, []


def gtm_tags(path: Path | None) -> dict[str, list[str]]:
    """Tag name -> the parameters it sends, from a container export."""
    if not path or not path.exists():
        return {}
    out = {}
    for t in json.loads(path.read_text(encoding="utf-8"))["containerVersion"]["tag"]:
        table = next((p_ for p_ in t.get("parameter", []) if p_["key"] == "eventSettingsTable"), None)
        out[t["name"]] = sorted(next(m["value"] for m in row["map"] if m["key"] == "parameter") for row in (table or {}).get("list", []))
    return out


def status_path(site: Site) -> Path:
    return site.root / "docs" / "analytics-status.json"


def doc_registered_dims(site: Site) -> list[str]:
    doc = site.root / "docs" / "ANALYTICS.md"
    if not doc.exists():
        return []
    m = re.search(r"## 3\. Register custom dimensions(.*?)\n## 4\.", doc.read_text(encoding="utf-8"), re.S)
    return re.findall(r"\|\s*[^|]+\|\s*`([a-z_]+)`\s*\|", m.group(1)) if m else []


def render_doc_block(site: Site, studios: list[dict], sections: dict, events: list[str], pending: list[str]) -> str:
    today = date.today().isoformat()
    rows = "\n".join(f"| {s['name']} | `{s['path']}` | `{workflow_name(s)}` | {s['kind']} |" for s in studios)
    secs = ", ".join(f"`{v}`" for v in sorted(set(sections.values())))
    pend = "\n".join(f"- [ ] {p}" for p in pending) if pending else "- None. GA4, Tag Manager and Looker Studio match the site."
    wf = ", ".join(f"`{workflow_name(s)}`" for s in studios)
    return f"""

## 8. Studios and workflows (kept up to date by the portfolio-updater skill)

Do not edit this section by hand: the skill rewrites it whenever it publishes. Last sync: {today}.

Every studio page reports its own `workflow_name`, and clicks on a studio card or link send `workflow_open` with it.

| Studio | Page | `workflow_name` | Kind |
|---|---|---|---|
{rows}

- **Events the site sends:** {", ".join(f"`{e}`" for e in events)}. Each has a trigger and a tag in the Tag Manager container export in this folder.
- **Studio page sections** report these extra `section_name` values: {secs}.
- **In the studio pages:** playing a video or app preview in the page sends `video_start` (`video_source` = `on_page_player`, `link_group` = `studio_outputs`); the workflow diagram sends `ui_interaction` with `workflow_run` (`auto` or `button`) and `workflow_step_view` (the step, e.g. `quality`).

**Looker Studio, page 4 (AI Studio).** Make the drop-down filter on **Workflow** list {wf}, then add:
- Pivot table: rows Workflow, columns Event name, metric Event count, filter Event name in (`workflow_open`, `video_start`, `workflow_run`). This shows how far each studio takes a visitor.
- Bar chart: Interaction label by Event count, filter Interaction type = `workflow_step_view`, with a Workflow control (which pipeline steps people open, per studio).
- Table: Link text, Click platform, Event count, filter Click group = `skills_used` or `claude_skills` (which skills people open, and the GitHub button).

**Pending manual steps** (only you can do these; the skill cannot reach GA4, Tag Manager or Looker Studio). Tick them off, then tell Claude "confirm analytics" so the list resets:
{pend}
"""


def analytics(site: Site, write: bool = True) -> tuple[list[str], list[str], list[str]]:
    """Return (changes, pending manual steps, errors). With write=False nothing is written: changes means drift."""
    changes, errors = [], []
    cfg = site.profile.get("analytics") or {}
    studios = site.studios()
    js_path = site.root / "assets" / "analytics.js"
    if not js_path.exists():
        return [], [], ["assets/analytics.js is missing; the site has no analytics to keep in step"] if cfg else ([], [], [])
    js_text = js_path.read_text(encoding="utf-8")

    # 1. analytics.js: the studio-page map and the extra section names
    pages = {s["path"]: workflow_name(s) for s in studios}
    body = "\n  var STUDIO_PAGES = {\n" + ",\n".join(f"    {js(k)}: {js(v)}".replace('"', "'") for k, v in pages.items()) + "\n  };\n  "
    new_js, old = block(js_text, "/* portfolio-updater:studios:begin */", "/* portfolio-updater:studios:end */", body)
    if old is None:
        errors.append("analytics.js has no portfolio-updater:studios markers")
    elif old != body:
        changes.append("analytics.js: studio page list updated")
    sections = cfg.get("sections", {})
    sbody = "\n    " + ", ".join(f"{(k if re.fullmatch(r'[a-z]+', k) else js(k).replace(chr(34), chr(39)))}: {js(v).replace(chr(34), chr(39))}" for k, v in sections.items()) + "\n    "
    new_js, old = block(new_js, "/* portfolio-updater:sections:begin */", "/* portfolio-updater:sections:end */", sbody)
    if old is None:
        errors.append("analytics.js has no portfolio-updater:sections markers")
    elif old != sbody:
        changes.append("analytics.js: section names updated")
    if write and new_js != js_text:
        js_path.write_text(new_js, encoding="utf-8")

    # 2. Tag Manager container
    events = scan_events(site)
    keys = analytics_keys(js_text)
    gtm_changes, gtm_errors = sync_gtm(site, events, keys, write)
    changes += gtm_changes
    errors += gtm_errors

    # 3. studio pages carry their workflow name
    for s in studios:
        if s["path"].endswith("/"):
            pg = site.root / s["path"] / "index.html"
            if pg.exists() and f'content="{workflow_name(s)}"' not in pg.read_text(encoding="utf-8"):
                changes.append(f"{s['path']}index.html: analytics workflow name out of date (run build-pages)")
        else:
            pg = site.root / s["path"]
            if pg.exists() and 'name="analytics-workflow"' not in pg.read_text(encoding="utf-8"):
                errors.append(f"{s['path']} has no analytics-workflow meta tag")

    # 4. what still needs a person: GTM import, GA4 dimensions, Looker filter
    cpath = gtm_file(site)
    ev_in_gtm = sorted(t["name"][len("CE - "):] for t in json.loads(cpath.read_text(encoding="utf-8"))["containerVersion"]["trigger"] if t["name"].startswith("CE - ")) if cpath else []
    st_path = status_path(site)
    status = read_json(st_path, None)
    if status is None:  # first run: what is in the repo now is taken as already set up
        status = {"gtm_tags": gtm_tags(cpath), "ga4_dimensions": sorted(set(doc_registered_dims(site)) | BUILTIN_PARAMS),
                  "looker_workflows": sorted(workflow_name(s) for s in studios if s["path"].startswith("studio/"))}
        changes.append("docs/analytics-status.json created")
    pending = []
    now_tags, known = gtm_tags(cpath), status.get("gtm_tags", {})
    diffs = [f"`{n}` (new)" if n not in known else f"`{n}` (now sends {', '.join(sorted(set(p_) - set(known[n])))})"
             for n, p_ in now_tags.items() if n not in known or set(p_) - set(known[n])]
    if diffs:
        pending.append("Tag Manager: import `docs/%s` (Admin, Import container, Merge, overwrite conflicting items), check it in Preview, then Publish. Changed: %s." % (cpath.name, "; ".join(diffs)))
    new_dim = [k for k in keys if k not in status["ga4_dimensions"] and k not in BUILTIN_PARAMS]
    if new_dim:
        pending.append("GA4: register custom dimensions (Admin, Custom definitions, scope Event) for: %s." % ", ".join(f"`{k}`" for k in new_dim))
    new_wf = [workflow_name(s) for s in studios if workflow_name(s) not in status["looker_workflows"]]
    if new_wf:
        pending.append("Looker Studio: open the report and check the Workflow drop-down lists %s; add the studio charts from section 8 of `docs/ANALYTICS.md` to page 4." % ", ".join(f"`{w}`" for w in new_wf))
    status_out = status

    # 5. the guide
    doc = site.root / "docs" / "ANALYTICS.md"
    if doc.exists():
        text = doc.read_text(encoding="utf-8")
        body_md = render_doc_block(site, studios, sections, sorted(events), pending)
        if DOC_BEGIN in text:
            new_text, old = block(text, DOC_BEGIN, DOC_END, body_md)
            old_cmp = re.sub(r"Last sync: [\d-]+", "", old or "")
            if re.sub(r"Last sync: [\d-]+", "", body_md) != old_cmp:
                changes.append("docs/ANALYTICS.md: studios section updated")
            else:
                new_text = text  # nothing but the date changed: leave the file alone
        else:
            new_text = text.rstrip("\n") + "\n\n" + DOC_BEGIN + body_md + DOC_END + "\n"
            changes.append("docs/ANALYTICS.md: studios section added")
        if write and new_text != text:
            doc.write_text(new_text, encoding="utf-8")
    if write and (not st_path.exists()):
        write_json(st_path, status_out)
    return changes, pending, errors


def cmd_analytics(site: Site, a: argparse.Namespace) -> int:
    if a.action == "confirm":
        changes, pending, _ = analytics(site, write=False)
        cpath = gtm_file(site)
        events = sorted(t["name"][5:] for t in json.loads(cpath.read_text(encoding="utf-8"))["containerVersion"]["trigger"] if t["name"].startswith("CE - ")) if cpath else []
        st = read_json(status_path(site), {"gtm_tags": {}, "ga4_dimensions": [], "looker_workflows": []})
        if a.gtm or a.all:
            st["gtm_tags"] = gtm_tags(cpath)
        if a.ga4 or a.all:
            st["ga4_dimensions"] = sorted(set(analytics_keys((site.root / "assets" / "analytics.js").read_text(encoding="utf-8"))) | BUILTIN_PARAMS | set(st["ga4_dimensions"]))
        if a.looker or a.all:
            st["looker_workflows"] = sorted(workflow_name(s) for s in site.studios())
        write_json(status_path(site), st)
        analytics(site, write=True)
        print("status saved")
        return 0
    changes, pending, errors = analytics(site, write=(a.action == "sync"))
    for c in changes:
        print(("changed: " if a.action == "sync" else "out of date: ") + c)
    for e in errors:
        print("ERROR:", e)
    if pending:
        print("PENDING MANUAL STEPS (GA4, Tag Manager, Looker Studio; I cannot reach them):")
        for p_ in pending:
            print("  -", p_)
    elif not errors:
        print("analytics: nothing pending")
    if a.action == "check":
        return 1 if (errors or changes) else 0
    return 1 if errors else 0

# ------------------------------------------------------------------------------------------------- publish
def git(site: Site, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(site.root), *args], capture_output=True, text=True, check=check)


def cmd_publish(site: Site, a: argparse.Namespace) -> int:
    for c in analytics(site, write=True)[0]:
        print("changed:", c)
    if cmd_check(site, a) != 0:
        die("check failed; fix it before publishing", 1)
    _, pending, _ = analytics(site, write=False)
    branches = site.profile.get("live_branches") or ["main"]
    git(site, "add", "-A")
    if not git(site, "status", "--porcelain").stdout.strip():
        print("nothing to publish")
        return 0
    if a.dry_run:
        print(git(site, "status", "--short").stdout, "\n(dry run) would push to:", ", ".join(branches))
        return 0
    git(site, "commit", "-m", a.message)
    here = git(site, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    tree = git(site, "rev-parse", "HEAD^{tree}").stdout.strip()
    for b in branches:
        if b == here:
            r = git(site, "push", "origin", f"HEAD:{b}", check=False)
        else:  # another live branch holding the same site: add one commit on top of its remote tip with this tree
            f = git(site, "fetch", "origin", b, check=False)
            if f.returncode:
                die(f"could not fetch {b}: {f.stderr.strip()}", 1)
            new = git(site, "commit-tree", tree, "-p", "FETCH_HEAD", "-m", a.message).stdout.strip()
            r = git(site, "push", "origin", f"{new}:refs/heads/{b}", check=False)
        if r.returncode:
            die(f"push to {b} failed: {r.stderr.strip()} (if the branch moved, fetch it and try again)", 1)
        print(f"pushed to {b}")
    if pending:
        print("PENDING MANUAL STEPS (GA4, Tag Manager, Looker Studio; the skill cannot reach them):")
        for p_ in pending:
            print("  -", p_)
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

    c = sub.add_parser("analytics", help="keep analytics.js, the Tag Manager export and the tracking guide in step with the site")
    c.add_argument("action", choices=["sync", "check", "confirm"])
    c.add_argument("--gtm", action="store_true"); c.add_argument("--ga4", action="store_true")
    c.add_argument("--looker", action="store_true"); c.add_argument("--all", action="store_true")
    c.set_defaults(fn=cmd_analytics)
    sub.add_parser("check").set_defaults(fn=cmd_check)

    c = sub.add_parser("publish")
    c.add_argument("--message", required=True); c.add_argument("--dry-run", action="store_true")
    c.set_defaults(fn=cmd_publish)

    a = ap.parse_args()
    site = Site(Path(a.site).resolve(), load_profile(a.profile))
    return a.fn(site, a)


if __name__ == "__main__":
    sys.exit(main())
