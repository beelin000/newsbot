#!/usr/bin/env python3
"""Email one or more newsbot briefing Markdown files via SMTP.

Configuration (env / GitHub Actions secrets+vars — never commit credentials):

  Required:
    BRIEFING_EMAIL_TO   Comma-separated recipient addresses
    SMTP_HOST           e.g. smtp.gmail.com
    SMTP_USER
    SMTP_PASSWORD       App password / SMTP password

  Optional:
    SMTP_PORT           default 587
    SMTP_FROM           default SMTP_USER
    SMTP_STARTTLS       default "1" (set "0" for SSL on 465)
    BRIEFING_PAGES_BASE e.g. https://beelin000.github.io/newsbot
    EMAIL_DRY_RUN       if "1", print payload and do not send

Usage:
  python3 scripts/email_briefing.py newsletters/global-brief-YYYY-MM-DD-morning.md
  python3 scripts/email_briefing.py --from-git-range BEFORE_SHA AFTER_SHA
  python3 scripts/email_briefing.py --latest

Note: CI auto-land emails only --latest once per run (not every path in a catch-up list).
"""

from __future__ import annotations

import argparse
import html as html_lib
import os
import re
import smtplib
import ssl
import subprocess
import sys
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BRIEF_RE = re.compile(
    r"^global-brief-(?P<date>\d{4}-\d{2}-\d{2})-(?P<slot>morning|evening)(?:-(?P<hm>\d{4}))?\.md$"
)
SLOT_LABEL = {"morning": "早报", "evening": "晚报"}


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    if v is None or not str(v).strip():
        return default
    return str(v).strip()


def parse_briefing(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    m = BRIEF_RE.match(md_path.name)
    date = m.group("date") if m else ""
    slot = m.group("slot") if m else ""
    hm = (m.group("hm") if m else "") or ""
    label = SLOT_LABEL.get(slot, slot or "简报")

    title_m = re.match(r"^#\s+(.+)$", text, re.M)
    title = title_m.group(1).strip() if title_m else f"全球要闻简报｜{date}｜{label}"
    if hm and "（" not in title:
        title = f"{title}（{hm[:2]}:{hm[2:]}）"

    meta_m = re.search(r"^\*\*生成时间：\*\*.+$", text, re.M)
    meta = meta_m.group(0) if meta_m else ""

    bullets: list[str] = []
    sec = re.search(r"##\s*今日要点\s*\n+(.*?)(?:\n---|\n##\s)", text, re.S)
    if sec:
        for b in re.findall(r"^-\s+(.+)$", sec.group(1), re.M):
            b = re.sub(r"\*\*", "", b).strip()
            bullets.append(b)

    return {
        "path": md_path,
        "html_path": md_path.with_suffix(".html"),
        "title": title,
        "date": date,
        "slot": slot,
        "label": label,
        "hm": hm,
        "meta": meta,
        "bullets": bullets,
        "markdown": text,
    }


def pages_url(brief: dict) -> str | None:
    base = env("BRIEFING_PAGES_BASE")
    if not base:
        return None
    base = base.rstrip("/")
    html_name = brief["html_path"].name
    rel = brief["html_path"].relative_to(ROOT).as_posix()
    # Prefer repo-relative path under Pages root.
    return f"{base}/{rel}" if html_name else None


def build_text_body(brief: dict) -> str:
    lines = [brief["title"], ""]
    if brief["meta"]:
        lines.append(re.sub(r"\*\*", "", brief["meta"]))
        lines.append("")
    lines.append("今日要点")
    lines.append("--------")
    if brief["bullets"]:
        for b in brief["bullets"]:
            lines.append(f"• {b}")
    else:
        lines.append("（无要点摘要）")
    url = pages_url(brief)
    if url:
        lines.extend(["", f"在线阅读：{url}"])
    lines.extend(
        [
            "",
            "——",
            "完整正文见附件 Markdown，或打开同目录 HTML。",
            f"源文件：{brief['path'].relative_to(ROOT).as_posix()}",
        ]
    )
    return "\n".join(lines)


def build_html_body(brief: dict) -> str:
    bullets_html = "".join(
        f"<li>{html_lib.escape(b)}</li>" for b in brief["bullets"]
    ) or "<li>（无要点摘要）</li>"
    meta = html_lib.escape(re.sub(r"\*\*", "", brief["meta"])) if brief["meta"] else ""
    url = pages_url(brief)
    link = (
        f'<p style="margin:16px 0 0"><a href="{html_lib.escape(url)}">在线阅读本期简报</a></p>'
        if url
        else ""
    )
    src = html_lib.escape(brief["path"].relative_to(ROOT).as_posix())
    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{html_lib.escape(brief["title"])}</title></head>
<body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Noto Sans SC',sans-serif;line-height:1.6;color:#1a1a1a;max-width:40rem;margin:0 auto;padding:1.25rem">
  <p style="color:#666;font-size:0.9rem;margin:0 0 0.35rem">全球要闻简报 · {html_lib.escape(brief["label"])}</p>
  <h1 style="font-size:1.35rem;margin:0 0 0.75rem">{html_lib.escape(brief["title"])}</h1>
  {"<p style='color:#666;font-size:0.9rem'>" + meta + "</p>" if meta else ""}
  <h2 style="font-size:1.05rem;margin:1.25rem 0 0.5rem">今日要点</h2>
  <ul style="padding-left:1.2rem;margin:0">{bullets_html}</ul>
  {link}
  <p style="color:#888;font-size:0.85rem;margin-top:1.5rem;border-top:1px solid #ddd;padding-top:0.75rem">
    完整正文见附件 Markdown。源文件：{src}
  </p>
</body></html>
"""


def send_one(brief: dict) -> None:
    to_raw = env("BRIEFING_EMAIL_TO")
    host = env("SMTP_HOST")
    user = env("SMTP_USER")
    password = env("SMTP_PASSWORD")
    if not to_raw or not host or not user or not password:
        missing = [
            n
            for n, v in [
                ("BRIEFING_EMAIL_TO", to_raw),
                ("SMTP_HOST", host),
                ("SMTP_USER", user),
                ("SMTP_PASSWORD", password),
            ]
            if not v
        ]
        raise SystemExit(
            "Missing required env: "
            + ", ".join(missing)
            + ". Set GitHub Actions secrets/vars (see README)."
        )

    port = int(env("SMTP_PORT", "587") or "587")
    mail_from = env("SMTP_FROM", user) or user
    starttls = (env("SMTP_STARTTLS", "1") or "1") != "0"
    recipients = [a.strip() for a in to_raw.split(",") if a.strip()]
    if not recipients:
        raise SystemExit("BRIEFING_EMAIL_TO has no valid addresses")

    msg = EmailMessage()
    msg["Subject"] = brief["title"]
    msg["From"] = mail_from
    msg["To"] = ", ".join(recipients)
    msg.set_content(build_text_body(brief))
    msg.add_alternative(build_html_body(brief), subtype="html")

    md_bytes = brief["markdown"].encode("utf-8")
    msg.add_attachment(
        md_bytes,
        maintype="text",
        subtype="markdown",
        filename=brief["path"].name,
    )
    if brief["html_path"].exists():
        msg.add_attachment(
            brief["html_path"].read_bytes(),
            maintype="text",
            subtype="html",
            filename=brief["html_path"].name,
        )

    if (env("EMAIL_DRY_RUN", "0") or "0") == "1":
        print(f"[dry-run] would send to {recipients}: {brief['title']}")
        print(build_text_body(brief)[:800])
        return

    context = ssl.create_default_context()
    if starttls:
        with smtplib.SMTP(host, port, timeout=60) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP_SSL(host, port, context=context, timeout=60) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
    print(f"sent: {brief['title']} -> {', '.join(recipients)}")


def briefings_from_git_range(before: str, after: str) -> list[Path]:
    """List newly added briefing .md files between two commits."""
    if not before or before == "0000000000000000000000000000000000000000":
        cmd = ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", "--diff-filter=A", after]
    else:
        cmd = [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=A",
            f"{before}...{after}",
        ]
    out = subprocess.check_output(cmd, cwd=ROOT, text=True)
    paths: list[Path] = []
    for line in out.splitlines():
        line = line.strip()
        if not line.startswith("newsletters/") or not line.endswith(".md"):
            continue
        name = Path(line).name
        if BRIEF_RE.match(name):
            paths.append(ROOT / line)
    return paths


def latest_briefing() -> Path | None:
    """Pick the newest briefing .md by filename date/slot/hm sort key."""
    news = ROOT / "newsletters"
    if not news.exists():
        return None
    scored: list[tuple[tuple, Path]] = []
    for path in news.rglob("global-brief-*.md"):
        m = BRIEF_RE.match(path.name)
        if not m:
            continue
        slot_rank = 0 if m.group("slot") == "morning" else 1
        hm = m.group("hm") or ""
        scored.append(((m.group("date"), slot_rank, hm), path))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("paths", nargs="*", type=Path, help="Briefing .md paths")
    ap.add_argument(
        "--from-git-range",
        nargs=2,
        metavar=("BEFORE", "AFTER"),
        help="Send newly added briefing .md files in the git range",
    )
    ap.add_argument(
        "--latest",
        action="store_true",
        help="Send the newest briefing on disk (useful for manual workflow tests)",
    )
    args = ap.parse_args(argv)

    files: list[Path] = []
    if args.latest:
        latest = latest_briefing()
        if latest is None:
            print("No briefing Markdown files found under newsletters/.", file=sys.stderr)
            return 1
        print(f"latest: {latest.relative_to(ROOT).as_posix()}")
        files.append(latest)
    if args.from_git_range:
        files.extend(briefings_from_git_range(args.from_git_range[0], args.from_git_range[1]))
    files.extend(p if p.is_absolute() else ROOT / p for p in args.paths)

    # Deduplicate while preserving order
    seen: set[Path] = set()
    unique: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)
        unique.append(p)

    if not unique:
        print("No new briefing Markdown files to email.")
        return 0

    for p in unique:
        if not p.exists():
            print(f"skip missing: {p}", file=sys.stderr)
            continue
        if not BRIEF_RE.match(p.name):
            print(f"skip non-briefing name: {p.name}", file=sys.stderr)
            continue
        send_one(parse_briefing(p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
