# newsbot

Workspace for the Cursor Automation **newsbot agent**.

Twice daily (07:00 / 19:00, Asia/Shanghai) it collects major worldwide news in finance, technology, politics, and military affairs, then writes a Chinese briefing as Markdown and a mobile-first static HTML page.

## Output

Each run **only adds** new files. It never overwrites or deletes previous briefings.

During the current calendar month, files land in `newsletters/`:

- `newsletters/全球要闻简报-YYYY-MM-DD-上午.md` / `.html`
- `newsletters/全球要闻简报-YYYY-MM-DD-晚上.md` / `.html`

When a calendar month has ended, the next run archives that month into a folder named after it:

- `newsletters/2026-07/`
- `newsletters/2026-08/`

Open the `.html` in any mobile browser. Pages are self-contained (inline CSS, no PDF).
