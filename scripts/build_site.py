#!/usr/bin/env python3
"""Build GitHub Pages static site from newsletter HTML files.

- Scans newsletters/ (incl. YYYY-MM archives) for briefing HTML
- Writes editions.json
- Writes index.html / archive.html as a dark “简报库” list UI
  (Investor Research–inspired theme)
"""

from __future__ import annotations

import html as html_lib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from theme_briefings import restyle_all

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "newsletters"
# Filenames are ASCII-only so CI path matching never hits C-locale quoting.
# Display titles/labels remain Chinese.
NAME_RE = re.compile(
    r"^global-brief-(?P<date>\d{4}-\d{2}-\d{2})-(?P<slot>morning|evening)(?:-(?P<hm>\d{4}))?\.html$"
)
SLOT_RANK = {"morning": 0, "evening": 1}
SLOT_LABEL = {"morning": "早报", "evening": "晚报"}


def find_editions() -> list[dict]:
    items: list[dict] = []
    if not NEWS.exists():
        return items
    for path in NEWS.rglob("global-brief-*.html"):
        m = NAME_RE.match(path.name)
        if not m:
            continue
        date = m.group("date")
        slot = m.group("slot")
        hm = m.group("hm") or ""
        rel = path.relative_to(ROOT).as_posix()
        label = SLOT_LABEL.get(slot, slot)
        title = f"全球要闻简报｜{date}｜{label}"
        if hm:
            title += f"（{hm[:2]}:{hm[2:]}）"
        summary = extract_summary(path.with_suffix(".md"))
        items.append(
            {
                "date": date,
                "slot": slot,
                "label": label,
                "hm": hm,
                "title": title,
                "path": rel,
                "summary": summary,
                "sort_key": (date, SLOT_RANK.get(slot, 0), hm),
            }
        )
    items.sort(key=lambda x: x["sort_key"], reverse=True)
    return items


def extract_summary(md_path: Path, max_bullets: int = 2) -> str:
    """Pull first bullets under 今日要点 from the matching Markdown file."""
    if not md_path.exists():
        return "点击阅读本期全球要闻简报全文。"
    text = md_path.read_text(encoding="utf-8")
    m = re.search(r"##\s*今日要点\s*\n+(.*?)(?:\n---|\n##\s)", text, re.S)
    if not m:
        return "点击阅读本期全球要闻简报全文。"
    bullets = re.findall(r"^-\s+(.+)$", m.group(1), re.M)
    cleaned = []
    for b in bullets[:max_bullets]:
        b = re.sub(r"\*\*|【更新】|【发展中】", "", b).strip()
        b = re.sub(r"\s+", " ", b)
        cleaned.append(b)
    if not cleaned:
        return "点击阅读本期全球要闻简报全文。"
    return "；".join(cleaned)


LIBRARY_CSS = """
:root {
  --bg: #0e1211;
  --bg-elevated: #141a18;
  --bg-input: #101614;
  --bg-card: #151c1a;
  --bg-card-hover: #1a2220;
  --text: #e6ebe8;
  --muted: #8b968f;
  --faint: #5c675f;
  --border: #24302c;
  --border-strong: #2f4039;
  --accent: #7eb68d;
  --accent-dim: #3d5c4a;
  --accent-soft: rgba(126, 182, 141, 0.12);
  --measure: 72rem;
  --page-pad: 1rem;
  --radius: 6px;
  --header-h: 3.25rem;
}
@media (min-width: 768px) {
  :root { --page-pad: 1.5rem; }
}
@media (min-width: 1100px) {
  :root { --page-pad: 2rem; }
  body { font-size: 16px; }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0;
  min-height: 100vh;
  font-family: ui-sans-serif, system-ui, "PingFang SC", "Hiragino Sans GB", "Noto Sans SC", "Source Han Sans SC", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  line-height: 1.6;
  color: var(--text);
  background: var(--bg);
  padding:
    env(safe-area-inset-top, 0px)
    env(safe-area-inset-right, 0px)
    calc(2rem + env(safe-area-inset-bottom, 0px))
    env(safe-area-inset-left, 0px);
  text-wrap: pretty;
}
a { color: var(--accent); text-decoration: none; }
a:focus-visible, button:focus-visible, input:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
.topbar {
  border-bottom: 1px solid var(--border);
  background: rgba(14, 18, 17, 0.92);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 40;
}
.topbar .inner {
  width: min(100%, var(--measure));
  margin: 0 auto;
  padding: 0.75rem var(--page-pad);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: var(--header-h);
}
.brand {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  color: var(--text);
  font-weight: 700;
  letter-spacing: 0.02em;
  font-size: 0.95rem;
}
.brand-mark {
  width: 1.35rem;
  height: 1.35rem;
  border-radius: 4px;
  background: linear-gradient(145deg, var(--accent), var(--accent-dim));
  box-shadow: 0 0 0 1px rgba(126,182,141,0.25);
}
.top-links {
  display: flex;
  gap: 1.1rem;
  flex-wrap: wrap;
  font-size: 0.85rem;
}
.top-links a { color: var(--muted); }
.top-links a:hover { color: var(--text); }
.wrap {
  width: min(100%, var(--measure));
  margin: 0 auto;
  padding: 1.1rem var(--page-pad) 2rem;
}
.tabs {
  display: flex;
  gap: 0.55rem;
  flex-wrap: wrap;
  margin: 0 0 1.25rem;
}
.tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 40px;
  padding: 0 0.95rem;
  border-radius: var(--radius);
  border: 1px solid transparent;
  color: var(--muted);
  font-size: 0.92rem;
  font-weight: 600;
}
.tab[aria-current="page"] {
  color: var(--accent);
  border-color: var(--accent-dim);
  background: var(--accent-soft);
}
.tab:hover { color: var(--text); }
.filters {
  display: grid;
  gap: 0.9rem;
  margin-bottom: 1.15rem;
}
.search {
  width: 100%;
  min-height: 44px;
  padding: 0.7rem 0.95rem;
  border-radius: var(--radius);
  border: 1px solid var(--border-strong);
  background: var(--bg-input);
  color: var(--text);
  font: inherit;
}
.search::placeholder { color: var(--faint); }
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}
.chip {
  appearance: none;
  cursor: pointer;
  min-height: 36px;
  padding: 0 0.8rem;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  color: var(--muted);
  font: inherit;
  font-size: 0.85rem;
}
.chip[aria-pressed="true"] {
  color: var(--accent);
  border-color: var(--accent-dim);
  background: var(--accent-soft);
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin: 0.35rem 0 0.85rem;
  color: var(--muted);
  font-size: 0.85rem;
}
.list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}
.card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.85rem 1rem;
  padding: 1rem 1.05rem;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--bg-card);
  transition: background 0.15s ease, border-color 0.15s ease;
}
.card:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-strong);
}
@media (min-width: 900px) {
  .card {
    grid-template-columns: 5.5rem 1fr auto;
    align-items: start;
    padding: 1.15rem 1.25rem;
  }
}
.card-side {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  min-width: 4.5rem;
}
.tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: fit-content;
  min-height: 1.55rem;
  padding: 0.1rem 0.45rem;
  border: 1px solid var(--accent-dim);
  border-radius: 4px;
  color: var(--accent);
  background: var(--accent-soft);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0.02em;
}
.side-date {
  color: var(--faint);
  font-size: 0.75rem;
  font-variant-numeric: tabular-nums;
  line-height: 1.35;
}
.card-main { min-width: 0; }
.card-title {
  margin: 0 0 0.4rem;
  font-size: 1.02rem;
  line-height: 1.45;
  font-weight: 700;
  color: var(--text);
}
.card-title a { color: inherit; }
.card-title a:hover { color: var(--accent); }
.card-summary {
  margin: 0;
  color: var(--muted);
  font-size: 0.88rem;
  line-height: 1.65;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.card-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 0.55rem;
  color: var(--faint);
  font-size: 0.78rem;
  white-space: nowrap;
}
@media (min-width: 900px) {
  .card-meta {
    align-items: flex-end;
    text-align: right;
    min-width: 9.5rem;
    padding-top: 0.15rem;
  }
}
.badge-new {
  display: inline-flex;
  align-items: center;
  padding: 0.05rem 0.4rem;
  border-radius: 4px;
  border: 1px solid var(--accent-dim);
  color: var(--accent);
  font-size: 0.72rem;
  font-weight: 700;
}
.read-link {
  color: var(--accent);
  font-weight: 650;
  font-size: 0.88rem;
  min-height: 36px;
  display: inline-flex;
  align-items: center;
}
.read-link::after { content: " ›"; }
.empty {
  padding: 2rem 1rem;
  text-align: center;
  color: var(--muted);
  border: 1px dashed var(--border);
  border-radius: var(--radius);
}
.footer {
  margin-top: 1.75rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border);
  color: var(--faint);
  font-size: 0.8rem;
}
"""


def build_library_html(
    editions: list[dict],
    generated_at: str,
    *,
    active: str = "index",
) -> str:
    latest_path = editions[0]["path"] if editions else "index.html"
    cards = []
    for i, ed in enumerate(editions):
        is_latest = i == 0
        y, m, d = ed["date"].split("-")
        date_cn = f"{y}年{int(m)}月{int(d)}日"
        summary = html_lib.escape(ed.get("summary") or "")
        title = html_lib.escape(ed["title"])
        label = html_lib.escape(ed["label"])
        path = html_lib.escape(ed["path"])
        badge = '<span class="badge-new">最新</span>' if is_latest else ""
        cards.append(
            f"""
    <li class="card" data-slot="{html_lib.escape(ed['slot'])}" data-title="{title}" data-summary="{summary}">
      <div class="card-side">
        <span class="tag">{label}</span>
        <span class="side-date">{html_lib.escape(ed['date'])}</span>
      </div>
      <div class="card-main">
        <h2 class="card-title"><a href="{path}">{title}</a></h2>
        <p class="card-summary">{summary}</p>
      </div>
      <div class="card-meta">
        <div>发布 {html_lib.escape(date_cn)}</div>
        <div>版次 {label}</div>
        {badge}
        <a class="read-link" href="{path}">阅读</a>
      </div>
    </li>"""
        )
    cards_html = "\n".join(cards) if cards else '<li class="empty">暂无简报</li>'
    index_current = ' aria-current="page"' if active == "index" else ""
    archive_current = ' aria-current="page"' if active == "archive" else ""
    page_title = "简报库｜全球要闻简报" if active == "index" else "往期简报｜全球要闻简报"

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="color-scheme" content="dark">
<meta name="theme-color" content="#0e1211">
<meta name="description" content="全球要闻简报 · 简报库">
<title>{page_title}</title>
<style>
{LIBRARY_CSS}
</style>
</head>
<body>
<header class="topbar">
  <div class="inner">
    <a class="brand" href="index.html"><span class="brand-mark" aria-hidden="true"></span>全球要闻简报</a>
    <nav class="top-links" aria-label="站点">
      <a href="{html_lib.escape(latest_path)}">最新一期</a>
      <a href="archive.html">往期</a>
    </nav>
  </div>
</header>

<main class="wrap">
  <nav class="tabs" aria-label="栏目">
    <a class="tab" href="index.html"{index_current}>简报库</a>
    <a class="tab" href="{html_lib.escape(latest_path)}">最新阅读</a>
    <a class="tab" href="archive.html"{archive_current}>全部期次</a>
  </nav>

  <section class="filters" aria-label="筛选">
    <label class="sr-only" for="q" style="position:absolute;left:-9999px">搜索</label>
    <input class="search" id="q" type="search" placeholder="搜索标题或要点…" autocomplete="off">
    <div class="chip-row" role="group" aria-label="版次筛选">
      <button type="button" class="chip" data-filter="all" aria-pressed="true">全部</button>
      <button type="button" class="chip" data-filter="evening" aria-pressed="false">晚报</button>
      <button type="button" class="chip" data-filter="morning" aria-pressed="false">早报</button>
    </div>
  </section>

  <div class="toolbar">
    <div>共 <strong id="count">{len(editions)}</strong> 篇简报</div>
    <div>生成于 {html_lib.escape(generated_at)}（UTC）</div>
  </div>

  <ul class="list" id="list">
{cards_html}
  </ul>

  <p class="footer">全球要闻简报 · 财经 / 科技 / 政治 / 军事 · 仅供信息摘要</p>
</main>

<script>
(function () {{
  var q = document.getElementById('q');
  var list = document.getElementById('list');
  var count = document.getElementById('count');
  var chips = Array.prototype.slice.call(document.querySelectorAll('.chip[data-filter]'));
  var slot = 'all';

  function apply() {{
    var query = (q.value || '').trim().toLowerCase();
    var visible = 0;
    Array.prototype.forEach.call(list.querySelectorAll('.card'), function (card) {{
      var slotOk = slot === 'all' || card.getAttribute('data-slot') === slot;
      var hay = ((card.getAttribute('data-title') || '') + ' ' + (card.getAttribute('data-summary') || '')).toLowerCase();
      var queryOk = !query || hay.indexOf(query) !== -1;
      var show = slotOk && queryOk;
      card.style.display = show ? '' : 'none';
      if (show) visible += 1;
    }});
    count.textContent = String(visible);
  }}

  chips.forEach(function (chip) {{
    chip.addEventListener('click', function () {{
      slot = chip.getAttribute('data-filter') || 'all';
      chips.forEach(function (c) {{
        c.setAttribute('aria-pressed', c === chip ? 'true' : 'false');
      }});
      apply();
    }});
  }});
  q.addEventListener('input', apply);
}})();
</script>
</body>
</html>
"""


def main() -> None:
    # Keep individual briefing pages on the shared dark library theme.
    restyle_all()

    editions = find_editions()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    serializable = []
    for ed in editions:
        serializable.append(
            {
                k: v
                for k, v in ed.items()
                if k != "sort_key"
            }
        )

    payload = {
        "generatedAt": generated_at,
        "latest": serializable[0] if serializable else None,
        "editions": serializable,
    }

    (ROOT / "editions.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "index.html").write_text(
        build_library_html(editions, generated_at, active="index"), encoding="utf-8"
    )
    (ROOT / "archive.html").write_text(
        build_library_html(editions, generated_at, active="archive"), encoding="utf-8"
    )
    print(f"index.html + archive.html + editions.json ({len(editions)} editions)")
    if editions:
        print(f"latest → {editions[0]['path']}")


if __name__ == "__main__":
    main()
