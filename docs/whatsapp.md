# WhatsApp setup

Milyonus supports WhatsApp through the **official Cloud API** (recommended).
An unofficial bridge is possible but risky and not shipped — see the note below.

## Official Cloud API (recommended)

You need a Meta developer app with WhatsApp added, a phone number id, and a
permanent access token. Then:

1. Put the credentials in `~/.milyonus/.env` (chmod 600):
   ```
   WHATSAPP_TOKEN=EAAG...              # Graph API access token
   WHATSAPP_PHONE_NUMBER_ID=1234567890
   WHATSAPP_VERIFY_TOKEN=some-random-string   # you choose this
   WHATSAPP_APP_SECRET=...             # optional but recommended (enables HMAC)
   ```
2. Start the gateway (it serves the webhook on the given port):
   ```bash
   milyonus gateway start --channel whatsapp --port 8080
   ```
3. Expose the port over HTTPS (a reverse proxy, or a tunnel like cloudflared /
   ngrok for testing) and register the public URL as your webhook in the Meta
   app, using the same `WHATSAPP_VERIFY_TOKEN`. Subscribe to the `messages` field.
4. Pair yourself: message the number, then send `/pair <code>` where the code
   comes from `milyonus gateway pair whatsapp`.

Security: if `WHATSAPP_APP_SECRET` is set, every inbound POST is HMAC-verified
(`X-Hub-Signature-256`) before it is trusted — set it in production. Inbound is
default-deny like every channel; group content is treated as lower trust.

## Unofficial bridge (experimental, risky — not shipped)

Libraries like `whatsapp-web.js` or Baileys automate a personal WhatsApp account.
They can get your number **banned** and violate WhatsApp's terms. Milyonus does
not ship this. If you accept the risk, you can run such a bridge yourself and
forward its messages to a small custom adapter implementing `ChannelAdapter`.
This path is unsupported.
