# Changelog

All notable changes to Milyonus Agent are documented here.
The format follows Keep a Changelog; versions follow the Milyonus model line.

## [5.5.0] — 2026-08-26

First public release of the Milyonus Agent 5.5 line.

### Core
- Provider-agnostic agent loop (streaming, interruptible, budgeted) with
  Anthropic (default), OpenAI, OpenRouter, and local (Ollama/vLLM) backends.
- SQLite (WAL + FTS5) session store; interactive terminal UI.

### Verified memory (the differentiator)
- Ingest → Quarantine → Verify → Promote pipeline; no direct-write path.
- Trust tiers T0–T4, provenance on every line, hash-chained audit ledger,
  cascade revocation, negative memory + rephrase detection.
- Separate verifier model; sleep-time consolidation.
- PoisonBench: 0% ASR / 0% RSR on a 45-case corpus.

### Skills
- Agent-authored skills gated by a reproducibility check + security scanner.
- 26 official bundled skills (agentskills.io-compatible,
  `milyonusagentskill` namespace).

### Security
- Risk-tiered approval; always-on SSRF; credential redaction; pre-exec command
  scanning; context-file injection scanning; DM pairing with lockout.

### Channels
- Telegram, WhatsApp (Cloud API), Slack (Events API), Discord (Gateway).
- Shared gateway core with default-deny, in-chat approval, auto-reconnect.

### Extension
- Self-modification harness (git snapshot + test gate + rollback), subagent
  delegation with a context contract, minimal MCP client.

### Deploy
- Hardened Docker image, compose, installer, systemd unit.
