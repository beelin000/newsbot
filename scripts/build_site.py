#!/usr/bin/env python3
"""Build GitHub Pages static site from newsletter HTML files.

- Scans newsletters/ (incl. YYYY-MM archives) for briefing HTML
- Writes editions.json, archive.html
- Writes index.html from the latest edition (with site chrome)
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "newsletters"
NAME_RE = re.compile(
    r"^全球要闻简报-(?P<date>\d{4}-\d{2}-\d{2})-(?P<slot>上午|晚上)(?:-(?P<hm>\d{4}))?\.html$"
)
SLOT_RANK = {"上午": 0, "晚上": 1}


def find_editions() -> list[dict]:
    items: list[dict] = []
    if not NEWS.exists():
        return items
    for path in NEWS.rglob("全球要闻简报-*.html"):
        m = NAME_RE.match(path.name)
        if not m:
            continue
        date = m.group("date")
        slot = m.group("slot")
        hm = m.group("hm") or ""
        rel = path.relative_to(ROOT).as_posix()
        title = f"全球要闻简报｜{date}｜{'早报' if slot == '上午' else '晚报'}"
        if hm:
            title += f"（{hm[:2]}:{hm[2:]}）"
        items.append(
            {
                "date": date,
                "slot": slot,
                "hm": hm,
                "title": title,
                "path": rel,
                "sort_key": (date, SLOT_RANK.get(slot, 0), hm),
            }
        )
    items.sort(key=lambda x: x["sort_key"], reverse=True)
    return items


SITE_BANNER_CSS = """
.site-chrome {
  border-bottom: 1px solid var(--border, #e2ddd3);
  background: var(--header-bg, var(--header, rgba(246,244,239,.96)));
}
.site-chrome .inner {
  width: min(100%, var(--measure, 42rem));
  margin: 0 auto;
  padding: 0.55rem var(--page-pad, 1rem);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  font-size: 0.9rem;
}
.site-chrome a {
  color: var(--accent, #0b4f6c);
  text-decoration: none;
  font-weight: 650;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}
.site-chrome .brand { font-weight: 700; color: var(--text, #1a1a1a); }
.site-chrome .links { display: flex; gap: 1rem; flex-wrap: wrap; }
"""


def inject_site_chrome(html: str, *, is_home: bool) -> str:
    """Add shared measure fallback + top chrome for Pages index."""
    if "--measure:" not in html:
        # Minimal fallback if an older file lacked responsive vars
        inject = """
:root { --measure: 42rem; --page-pad: 1rem; }
@media (min-width: 768px) { :root { --measure: 52rem; --page-pad: 1.5rem; } }
@media (min-width: 1100px) { :root { --measure: 60rem; --page-pad: 2rem; } body { font-size: 18px; } }
"""
        html = html.replace("</style>", inject + "</style>", 1)

    if ".site-chrome" not in html:
        html = html.replace("</style>", SITE_BANNER_CSS + "</style>", 1)

    archive_href = "archive.html"
    latest_href = "index.html"
    home_label = "最新一期" if is_home else "最新一期"
    chrome = f"""
<div class="site-chrome" role="navigation" aria-label="站点导航">
  <div class="inner">
    <span class="brand">全球要闻简报</span>
    <div class="links">
      <a href="{latest_href}"{" aria-current=\"page\"" if is_home else ""}>{home_label}</a>
      <a href="{archive_href}">往期简报</a>
    </div>
  </div>
</div>
"""
    # Place chrome before sticky edition header when possible
    if '<div id="top"></div>' in html:
        html = html.replace('<div id="top"></div>', '<div id="top"></div>\n' + chrome, 1)
    elif "<body>" in html:
        html = html.replace("<body>", "<body>\n" + chrome, 1)
    else:
        html = chrome + html

    # Fix relative asset links inside copied index: newsletter paths stay as newsletters/...
    # Sources in details are absolute URLs — fine.
    return html


def rewrite_paths_for_index(html: str) -> str:
    """No path rewrite needed for content; chrome uses root-relative archive/index."""
    return html


def build_archive_html(editions: list[dict], generated_at: str) -> str:
    rows = []
    for i, ed in enumerate(editions):
        badge = ' <span class="badge">最新</span>' if i == 0 else ""
        rows.append(
            f'<li><a href="{ed["path"]}">{ed["title"]}</a>{badge}</li>'
        )
    items = "\n      ".join(rows) if rows else "<li>暂无简报</li>"
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="light dark">
<meta name="description" content="全球要闻简报 · 往期列表">
<title>往期简报｜全球要闻简报</title>
<style>
:root {{
  --bg: #f6f4ef;
  --bg-card: #ffffff;
  --text: #1a1a1a;
  --muted: #5c5c5c;
  --border: #e2ddd3;
  --accent: #0b4f6c;
  --header-bg: rgba(246, 244, 239, 0.92);
  --measure: 42rem;
  --page-pad: 1rem;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #121416;
    --bg-card: #1c1f24;
    --text: #f0f0f0;
    --muted: #a8a8a8;
    --border: #2e333a;
    --accent: #7eb8d4;
    --header-bg: rgba(18, 20, 22, 0.94);
  }}
}}
@media (min-width: 768px) {{
  :root {{ --measure: 52rem; --page-pad: 1.5rem; }}
}}
@media (min-width: 1100px) {{
  :root {{ --measure: 60rem; --page-pad: 2rem; }}
  body {{ font-size: 18px; }}
}}
* {{ box-sizing: border-box; }}
html {{ -webkit-text-size-adjust: 100%; }}
body {{
  margin: 0;
  font-family: ui-sans-serif, system-ui, "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
  font-size: 17px;
  line-height: 1.75;
  color: var(--text);
  background: var(--bg);
  padding:
    env(safe-area-inset-top, 0px)
    env(safe-area-inset-right, 0px)
    calc(2rem + env(safe-area-inset-bottom, 0px))
    env(safe-area-inset-left, 0px);
  text-wrap: pretty;
}}
.wrap {{ width: min(100%, var(--measure)); margin: 0 auto; padding: 1rem var(--page-pad); }}
h1 {{ margin: 0 0 0.35rem; font-size: 1.4rem; }}
.meta {{ color: var(--muted); font-size: 0.9rem; margin: 0 0 1.25rem; }}
.nav {{ display: flex; gap: 1rem; margin-bottom: 1.25rem; }}
.nav a {{
  color: var(--accent);
  font-weight: 650;
  text-decoration: none;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
}}
ul {{
  list-style: none;
  margin: 0;
  padding: 0;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
}}
li {{
  border-bottom: 1px solid var(--border);
  padding: 0;
}}
li:last-child {{ border-bottom: none; }}
li a {{
  display: flex;
  align-items: center;
  min-height: 52px;
  padding: 0.75rem 1rem;
  color: var(--text);
  text-decoration: none;
}}
li a:focus-visible {{ outline: 2px solid var(--accent); outline-offset: -2px; }}
.badge {{
  margin-left: 0.6rem;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 4px;
  padding: 0.05rem 0.4rem;
}}
</style>
</head>
<body>
<main class="wrap">
  <nav class="nav" aria-label="站点导航">
    <a href="index.html">最新一期</a>
    <a href="archive.html" aria-current="page">往期简报</a>
  </nav>
  <h1>往期简报</h1>
  <p class="meta">共 {len(editions)} 期 · 生成于 {generated_at}（UTC）</p>
  <ul>
      {items}
  </ul>
</main>
</body>
</html>
"""


def main() -> None:
    editions = find_editions()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    payload = {
        "generatedAt": generated_at,
        "latest": None,
        "editions": [
            {k: v for k, v in ed.items() if k != "sort_key"} for ed in editions
        ],
    }
    if editions:
        latest = editions[0]
        payload["latest"] = {k: v for k, v in latest.items() if k != "sort_key"}
        src = ROOT / latest["path"]
        html = src.read_text(encoding="utf-8")
        html = rewrite_paths_for_index(html)
        html = inject_site_chrome(html, is_home=True)
        # Retarget title slightly for home
        html = re.sub(
            r"<title>.*?</title>",
            "<title>全球要闻简报｜最新一期</title>",
            html,
            count=1,
            flags=re.S,
        )
        (ROOT / "index.html").write_text(html, encoding="utf-8")
        print(f"index.html ← {latest['path']}")
    else:
        (ROOT / "index.html").write_text(
            "<!DOCTYPE html><html lang='zh-CN'><meta charset='utf-8'>"
            "<title>全球要闻简报</title><body><p>暂无简报</p>"
            "<p><a href='archive.html'>往期简报</a></p></body></html>\n",
            encoding="utf-8",
        )
        print("index.html ← empty placeholder")

    (ROOT / "editions.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "archive.html").write_text(
        build_archive_html(editions, generated_at), encoding="utf-8"
    )
    print(f"archive.html + editions.json ({len(editions)} editions)")


if __name__ == "__main__":
    main()
