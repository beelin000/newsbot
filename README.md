# newsbot

Workspace for the Cursor Automation **newsbot agent**.

Twice daily (07:00 / 19:00, Asia/Shanghai) it collects major worldwide news in finance, technology, politics, and military affairs, then writes a Chinese briefing as Markdown and a mobile-first static HTML page.

## Website (GitHub Pages)

Static site root:

| Path | Purpose |
|------|---------|
| `index.html` | Briefing library (dark list UI) |
| `archive.html` | Same library UI (全部期次 tab) |
| `editions.json` | Machine-readable edition index |
| `newsletters/*.html` | Individual briefing pages |

Rebuild after adding a newsletter:

```bash
python3 scripts/build_site.py
```

The homepage and individual briefing pages share a dark Investor Research–inspired theme (charcoal/green). Nav chips and action buttons use rounded rectangles (`border-radius: 6px`), not pills.

After adding a newsletter, rebuild (also re-applies briefing theme):

```bash
python3 scripts/build_site.py
```

Or theme briefings only:

```bash
python3 scripts/theme_briefings.py
```

Enable **Settings → Pages → Source: GitHub Actions**. Push to `main` runs `.github/workflows/pages.yml` and publishes the site (typically `https://<user>.github.io/newsbot/`).

### Auto-merge briefing PRs

`.github/workflows/auto-merge-newsbot.yml` watches PRs whose head branch starts with `cursor/chinese-news-brief` or `cursor/chinese-global-news-brief`.

**Only trusted PRs are auto-merged.** All of the following must hold:

1. Head branch is in **this same repository** (forks are blocked)
2. PR author is allowlisted: `beelin000` (you) or `cursor[bot]` (Cursor agent / automation)
3. Workflow trigger actor is allowlisted: `beelin000`, `cursor[bot]`, or `github-actions[bot]`
4. Target branch is `main`

Then the workflow:

1. Marks draft PRs as ready  
2. Lands `newsletters/**` (add/update/**delete**), plus `scripts/**`, `README.md`, and `.github/workflows/**` when those change  
3. Regenerates `index.html` / `archive.html` / `editions.json` (avoids morning/evening conflicts on generated Pages files)  
4. Merges or closes the PR and deploys Pages  

Path listing uses `git diff -z` so filenames stay unquoted. Newsletter filenames must be ASCII (`global-brief-…`).

External or fork PRs matching the branch name pattern are **not** auto-merged.

Responsive reading widths (phone / tablet / desktop):

- phone: ~42rem
- tablet (≥768px): ~52rem
- desktop (≥1100px): ~60rem, 18px body text

## Output

Each run **only adds** new files. It never overwrites or deletes previous briefings.

During the current calendar month, files land in `newsletters/` with **ASCII-only** filenames (avoids CI path-quoting bugs with non-ASCII names):

- `newsletters/global-brief-YYYY-MM-DD-morning.md` / `.html`（早报）
- `newsletters/global-brief-YYYY-MM-DD-evening.md` / `.html`（晚报）
- Optional disambiguation suffix: `-HHmm` before the extension, e.g. `global-brief-2026-09-12-evening-1910.md`

Page **titles and body copy stay Chinese**; only on-disk names are English.

When a calendar month has ended, the next run archives that month into a folder named after it:

- `newsletters/2026-07/`
- `newsletters/2026-08/`

Open the `.html` in any browser. Pages are self-contained (inline CSS, no PDF). After each new edition, run `python3 scripts/build_site.py` so the homepage points at the latest brief.

## Email delivery

When new `newsletters/global-brief-*.md` files are pushed to `main`, `.github/workflows/email-briefing.yml` emails them to your inbox (HTML summary + Markdown/HTML attachments).

### 1. Add GitHub Secrets / Variables

Repo → **Settings → Secrets and variables → Actions**.

| Name | Where | Required | Example |
|------|--------|----------|---------|
| `BRIEFING_EMAIL_TO` | Secret or Variable | yes | `you@example.com` (comma-separated OK) |
| `SMTP_HOST` | Secret | yes | `smtp.gmail.com` |
| `SMTP_USER` | Secret | yes | your SMTP login |
| `SMTP_PASSWORD` | Secret | yes | app password (not account password for Gmail) |
| `SMTP_PORT` | Secret or Variable | no | `587` (default) |
| `SMTP_FROM` | Secret or Variable | no | defaults to `SMTP_USER` |
| `SMTP_STARTTLS` | Variable | no | `1` (default); use `0` + port `465` for SSL |
| `BRIEFING_PAGES_BASE` | Variable | no | `https://beelin000.github.io/newsbot` |

**Gmail:** enable 2FA, create an [App Password](https://myaccount.google.com/apppasswords), use `smtp.gmail.com` / `587` / that app password.

If secrets are missing, the workflow skips send with a notice (does not fail the deploy).

### 2. Test

Actions → **Email new briefings** → **Run workflow**, set e.g.:

`newsletters/global-brief-2026-09-17-morning.md`

Local dry-run (no send):

```bash
EMAIL_DRY_RUN=1 \
BRIEFING_EMAIL_TO=you@example.com \
SMTP_HOST=smtp.example.com SMTP_USER=u SMTP_PASSWORD=p \
python3 scripts/email_briefing.py newsletters/global-brief-2026-09-17-morning.md
```
