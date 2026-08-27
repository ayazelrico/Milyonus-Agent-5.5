# Integrations

Beyond files, shell, and web, Milyonus ships tools for email, a real browser, and
vision. Each follows the same safety model: reversible/local runs automatically,
outward/irreversible confirms, and untrusted content flows through the
verified-memory pipeline if the agent tries to remember it.

## Email (IMAP/SMTP)

Read and send email on the standard library — no extra dependency.

```bash
# ~/.milyonus/.env  (chmod 600)
EMAIL_ADDRESS=you@example.com
EMAIL_PASSWORD=an-app-password
IMAP_HOST=imap.example.com
SMTP_HOST=smtp.example.com
# IMAP_PORT=993  SMTP_PORT=587  (defaults)
```

Tools: `email_list` (caution), `email_read` (caution — untrusted content),
`email_send` (**danger** — outward + irreversible, always confirms).

## Browser automation (Playwright)

`web_fetch` gets raw HTTP; `browser_fetch` renders JavaScript in a real headless
browser and returns the visible text. SSRF-guarded, read-only.

```bash
pip install milyonus-agent[browser]
playwright install chromium
```

Tool: `browser_fetch(url, wait_for?)` (caution).

## Vision (image input)

`describe_image(path, question?)` analyzes a local image (png/jpg/gif/webp) with a
multimodal model. The image is sent as a neutral image block, so it works with
Anthropic and OpenAI vision models. Path-confined to the working root, read-only
(safe).

> Requires a vision-capable model (the default Claude models qualify).
