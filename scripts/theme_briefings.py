#!/usr/bin/env python3
"""Apply Investor Research dark theme to newsletter briefing HTML pages."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NEWS = ROOT / "newsletters"

THEME_MARKER = "/* newsbot-theme: investor-dark-v1 */"

THEME_ROOT = f"""{THEME_MARKER}
:root {{
  --bg: #0e1211;
  --bg-card: #151c1a;
  --card: #151c1a;
  --text: #e6ebe8;
  --muted: #8b968f;
  --border: #24302c;
  --accent: #7eb68d;
  --accent-soft: rgba(126, 182, 141, 0.12);
  --accent-dim: #3d5c4a;
  --why: #a8c4b0;
  --chip: #141a18;
  --header-bg: rgba(14, 18, 17, 0.94);
  --shadow: none;
  --top-btn: #7eb68d;
  --top-btn-fg: #0e1211;
  --measure: 42rem;
  --page-pad: 1rem;
  --radius: 6px;
}}
@media (min-width: 768px) {{
  :root {{
    --measure: 52rem;
    --page-pad: 1.5rem;
  }}
}}
@media (min-width: 1100px) {{
  :root {{
    --measure: 60rem;
    --page-pad: 2rem;
  }}
  body {{ font-size: 18px; }}
}}
"""

COLOR_SCHEME_RE = re.compile(r'<meta name="color-scheme" content="[^"]*">')
THEME_COLOR_RE = re.compile(r'<meta name="theme-color" content="[^"]*">\s*')
STYLE_BLOCK_RE = re.compile(r"<style>(.*?)</style>", re.S)

# Strip previous theme block or legacy light/dark variable blocks at the top.
LEGACY_VARS_RE = re.compile(
    r"^(?:\s*/\* newsbot-theme: investor-dark-v1 \*/\s*)?"
    r"(?::root\s*\{.*?\}\s*)+"
    r"(?:@media\s*\(min-width:\s*768px\)\s*\{.*?\}\s*)?"
    r"(?:@media\s*\(min-width:\s*1100px\)\s*\{.*?\}\s*)?"
    r"(?:@media\s*\(prefers-color-scheme:\s*dark\)\s*\{.*?\}\s*)?",
    re.S,
)


def normalize_component_radii(css: str) -> str:
    css = css.replace("border-radius: 999px;", "border-radius: var(--radius);")
    css = css.replace("border-radius: 999px", "border-radius: var(--radius)")

    css = re.sub(
        r"(\.card\s*\{[^}]*?)border-radius:\s*\d+px;",
        r"\1border-radius: var(--radius);",
        css,
        flags=re.S,
    )
    css = re.sub(
        r"(\.note\s*\{[^}]*?)border-radius:\s*\d+px;",
        r"\1border-radius: var(--radius);",
        css,
        flags=re.S,
    )
    css = re.sub(
        r"(#top-btn\s*\{[^}]*?)border-radius:\s*50%;",
        r"\1border-radius: var(--radius);",
        css,
        flags=re.S,
    )
    css = re.sub(
        r"(\.to-top\s*\{[^}]*?)border-radius:\s*50%;",
        r"\1border-radius: var(--radius);",
        css,
        flags=re.S,
    )
    css = re.sub(
        r"(\.chips a\s*\{[^}]*?)border-radius:\s*(?:999px|var\(--radius\));",
        r"\1border-radius: var(--radius);",
        css,
        flags=re.S,
    )

    if ".chip-scroll a {" in css and ".chip-scroll a:hover" not in css:
        css = css.replace(
            ".chip-scroll a:focus-visible {",
            """.chip-scroll a:hover {
  color: var(--accent);
  border-color: var(--accent-dim);
  background: var(--accent-soft);
}
.chip-scroll a:focus-visible {""",
        )

    if ".lib-link" not in css:
        css += """
.lib-link {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  margin: 0 0 0.35rem;
  padding: 0 0.7rem;
  border: 1px solid var(--accent-dim);
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
  text-decoration: none;
  font-size: 0.82rem;
  font-weight: 650;
}
.lib-link:hover { border-color: var(--accent); }
"""
    return css


def restyle_css(css: str) -> str:
    css = css.lstrip()
    # Remove any prior theme / legacy variable preamble.
    css = LEGACY_VARS_RE.sub("", css, count=1).lstrip()
    # Safety: if a stray prefers-color-scheme dark block remains near top, drop it.
    css = re.sub(
        r"^@media\s*\(prefers-color-scheme:\s*dark\)\s*\{.*?\}\s*",
        "",
        css,
        count=1,
        flags=re.S,
    )
    css = THEME_ROOT + css
    return normalize_component_radii(css)


def ensure_library_link(html: str) -> str:
    if 'class="lib-link"' in html:
        return html
    if '<div class="inner">' in html:
        html = html.replace(
            '<div class="inner">\n',
            '<div class="inner">\n    <a class="lib-link" href="../index.html">简报库</a>\n',
            1,
        )
        return html
    if '<div class="head">' in html:
        html = html.replace(
            '<div class="head">\n',
            '<div class="head">\n    <a class="lib-link" href="../index.html">简报库</a>\n',
            1,
        )
        return html
    return html


def fix_lib_link_depth(path: Path, html: str) -> str:
    rel = path.relative_to(NEWS)
    depth = len(rel.parts) - 1
    href = "../" * (depth + 1) + "index.html"
    return re.sub(
        r'(class="lib-link" href=")[^"]+(")',
        rf"\1{href}\2",
        html,
        count=1,
    )


def restyle_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8")
    html = original

    # Fast path: already on the shared theme.
    if (
        THEME_MARKER in html
        and 'color-scheme" content="dark"' in html
        and "border-radius: 999px" not in html
        and 'class="lib-link"' in html
        and "#f6f4ef" not in html
    ):
        updated = fix_lib_link_depth(path, html)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            return True
        return False

    html = COLOR_SCHEME_RE.sub(
        '<meta name="color-scheme" content="dark">',
        html,
        count=1,
    )
    html = THEME_COLOR_RE.sub("", html)
    if 'name="color-scheme" content="dark"' in html and "theme-color" not in html:
        html = html.replace(
            '<meta name="color-scheme" content="dark">',
            '<meta name="color-scheme" content="dark">\n<meta name="theme-color" content="#0e1211">',
            1,
        )
    elif 'name="color-scheme" content="dark"' in html and "theme-color" in html:
        # normalize to a single theme-color after color-scheme
        html = THEME_COLOR_RE.sub("", html)
        html = html.replace(
            '<meta name="color-scheme" content="dark">',
            '<meta name="color-scheme" content="dark">\n<meta name="theme-color" content="#0e1211">',
            1,
        )

    m = STYLE_BLOCK_RE.search(html)
    if not m:
        return False
    new_css = restyle_css(m.group(1))
    html = html[: m.start()] + "<style>\n" + new_css + "\n</style>" + html[m.end() :]
    html = ensure_library_link(html)
    html = fix_lib_link_depth(path, html)

    if html == original:
        return False
    path.write_text(html, encoding="utf-8")
    return True


def restyle_all() -> int:
    changed = 0
    for path in sorted(NEWS.rglob("全球要闻简报-*.html")):
        if restyle_file(path):
            changed += 1
            print(f"restyled {path.relative_to(ROOT)}")
        else:
            print(f"unchanged {path.relative_to(ROOT)}")
    return changed


if __name__ == "__main__":
    n = restyle_all()
    print(f"done, changed={n}")
