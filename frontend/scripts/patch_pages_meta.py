#!/usr/bin/env python3
"""Rewrite api-base / data-source in frontend/index.html for Cloudflare Pages (CI only)."""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "index.html"


def main() -> None:
    # D1 map API: TypeScript data-extraction-worker (preferred). Fallback: Python BFF or secret.
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
    html = INDEX.read_text(encoding="utf-8")
    html, n1 = re.subn(
        r'(<meta\s+name="api-base"\s+content=")[^"]*(")',
        rf'\g<1>{url}\2',
        html,
        count=1,
    )
    html, n2 = re.subn(
        r'(<meta\s+name="data-source"\s+content=")[^"]*(")',
        r'\g<1>worker\2',
        html,
        count=1,
    )
    if n1 != 1 or n2 != 1:
        print(f"patch_pages_meta: expected 1 api-base and 1 data-source meta, got {n1} {n2}", file=sys.stderr)
        sys.exit(1)
    INDEX.write_text(html, encoding="utf-8")
    print(f"patched {INDEX}: api-base={url}, data-source=worker")


if __name__ == "__main__":
    main()
