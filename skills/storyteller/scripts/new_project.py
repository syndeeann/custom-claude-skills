#!/usr/bin/env python3
"""Create a video project's script folder and print where the next script goes.

    python scripts/new_project.py <project> [--topic "working title"] [--root <video-projects dir>]

Creates video-projects/<project>/script/ if it is missing and prints the next numbered file names:

    video-projects/<project>/script/003-<topic-slug>.md
    video-projects/<project>/script/003-<topic-slug>.prompts.json

--root defaults to the nearest video-projects folder at or above the current directory, or ./video-projects.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def slugify(text: str, limit: int = 48) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit].strip("-") or "untitled"


def find_root() -> Path:
    here = Path.cwd().resolve()
    for p in [here, *here.parents]:
        if (p / "video-projects").is_dir():
            return p / "video-projects"
    return here / "video-projects"


def next_number(script_dir: Path) -> int:
    nums = [int(m.group(1)) for f in script_dir.iterdir() if (m := re.match(r"^(\d+)-", f.name))]
    return max(nums, default=0) + 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("project", help="project folder name, lowercase-with-hyphens (e.g. kwento-kilabot)")
    ap.add_argument("--topic", default="untitled", help="working title; becomes the file-name slug")
    ap.add_argument("--root", type=Path, help="the video-projects directory")
    args = ap.parse_args()

    if not NAME_RE.match(args.project) or len(args.project) > 64:
        sys.exit("project must be lowercase-with-hyphens, up to 64 characters (e.g. tiktok-shop-ads)")
    root = (args.root or find_root()).resolve()
    script_dir = root / args.project / "script"
    created = not script_dir.exists()
    script_dir.mkdir(parents=True, exist_ok=True)

    base = f"{next_number(script_dir):03d}-{slugify(args.topic)}"
    print(("created " if created else "found   ") + str(script_dir))
    print(f"markdown: {script_dir / (base + '.md')}")
    print(f"json:     {script_dir / (base + '.prompts.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
