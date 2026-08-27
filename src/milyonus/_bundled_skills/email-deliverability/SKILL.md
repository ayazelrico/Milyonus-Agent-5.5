---
name: email-deliverability
description: 'Land in the inbox: SPF/DKIM/DMARC, warmup, spam avoidance'
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - outreach
    - deliverability
    - dns
    - spam
    - email
    category: outreach
    requires_toolsets: []
    provenance: official
---

# Email Deliverability

The best copy fails in spam. Protect the inbox path.

## Authentication (set once, per sending domain)
- **SPF:** TXT record listing servers allowed to send for the domain.
- **DKIM:** cryptographic signature; publish the public key in DNS.
- **DMARC:** policy tying SPF+DKIM together (`p=none` to monitor, then `quarantine`/`reject`).
- Verify with a mail-tester tool before any volume.

## Protect sending reputation
- **Use a separate domain/subdomain** for cold outreach (not your primary domain).
- **Warm up** new mailboxes: ramp volume slowly over weeks; get early replies.
- Keep volume per mailbox low (e.g. tens/day, not hundreds); use multiple mailboxes
  behind sensible rotation rather than blasting one.
- **List hygiene:** verify addresses; remove bounces immediately. High bounce or
  spam-complaint rates get you blocklisted.

## Content that avoids spam filters
- Plain text or light HTML; avoid image-only emails and link shorteners.
- No spam-trigger phrasing, ALL CAPS, or excessive punctuation/links.
- No tracking pixels on first touch; one clear, real unsubscribe.
- Consistent from-name/domain; valid reply-to.

## Monitor
- Watch bounce rate, spam-complaint rate, and reply rate. If deliverability drops,
  pause, fix hygiene/warmup, and lower volume. Never buy lists.
