#!/usr/bin/env python3
"""Rewrite api-base / data-source in frontend HTML for Cloudflare Pages (CI only)."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Pages that fetch the D1 Worker; must each contain one api-base and one data-source meta.
PATCH_TARGETS = ("index.html", "victims.html")


def patch_file(path: Path, url: str) -> bool:
    if not path.is_file():
        return False
    html = path.read_text(encoding="utf-8")
    if 'name="api-base"' not in html or 'name="data-source"' not in html:
        return False
    html, n1 = re.subn(
        r'(<meta\s+name="api-base"\s+content=")[^"]*(")',
        rf"\g<1>{url}\2",
        html,
        count=1,
    )
    html, n2 = re.subn(
        r'(<meta\s+name="data-source"\s+content=")[^"]*(")',
        r"\g<1>worker\2",
        html,
        count=1,
    )
    if n1 != 1 or n2 != 1:
        print(
            f"patch_pages_meta: {path.name}: expected 1 api-base and 1 data-source meta, got {n1} {n2}",
            file=sys.stderr,
        )
        sys.exit(1)
    path.write_text(html, encoding="utf-8")
    print(f"patched {path}: api-base={url}, data-source=worker")
    return True


def main() -> None:
    url = (
        os.environ.get("D1_WORKER_URL")
        or os.environ.get("WORKER_URL")
        or os.environ.get("PAGES_API_BASE")
        or ""
    ).strip().rstrip("/")
    if not url:
        print(
            "Set D1_WORKER_URL (data-extraction-worker deploy), WORKER_URL, or PAGES_API_BASE.",
            file=sys.stderr,
        )
        sys.exit(1)
    patched = 0
    for name in PATCH_TARGETS:
        if patch_file(ROOT / name, url):
            patched += 1
    if patched == 0:
        print("patch_pages_meta: no files matched PATCH_TARGETS", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
