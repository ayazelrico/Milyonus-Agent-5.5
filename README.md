<div align="center">

# ✦ Milyonus Agent

**Remembers. Verifies. Evolves.**

An open-source, self-improving autonomous agent — with a verified-memory core
that closes the biggest gap in self-evolving agents: *who wrote this memory, and
was it checked?*

[![CI](https://github.com/milyonus/milyonus-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/milyonus/milyonus-agent/actions)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](pyproject.toml)

</div>

---

## Why Milyonus

Most agents start from zero every session. The ones that *do* remember tend to
believe whatever gets written to memory — which makes them easy to poison.
Milyonus keeps the learning loop (persistent memory + self-authored skills) but
makes memory **earn its place**:

| | Typical self-evolving agent | Milyonus |
|---|---|---|
| Memory write | Agent writes directly | **Ingest → Quarantine → Verify → Promote** |
| Provenance | Not tracked | Every line: who, from where, which turn, what evidence |
| Poison cleanup | Manual | `memory revoke --source <uri>` cascades in seconds |
| Rejected ideas | Forgotten (rephrase slips through) | **Negative memory** + rephrase detection |
| Memory in prompt | Injected as text | Rendered in a **data fence** — "not instructions" |
| Autonomy | "Act first" (risk multiplier) | **Risk-tiered**: reversible → auto, irreversible → always confirm |

Measured on the built-in **PoisonBench**: **ASR 0% / RSR 0%** (see
[docs/benchmarks.md](docs/benchmarks.md)).

## Quick start

```bash
# install uv (https://astral.sh/uv) then:
uv tool install milyonus-agent      # or: git clone && uv sync

milyonus setup                      # pick a provider, add your key
milyonus doctor                     # verify the environment
milyonus                            # start an interactive session
```

Add your key to `~/.milyonus/.env` (chmod 600):

```
ANTHROPIC_API_KEY=sk-ant-...
# or OPENAI_API_KEY / OPENROUTER_API_KEY for OpenAI-compatible providers
```

## Talk to it from Telegram

```bash
echo 'TELEGRAM_BOT_TOKEN=...' >> ~/.milyonus/.env   # from @BotFather
milyonus gateway pair telegram                       # get a pairing code
milyonus gateway start                               # default-deny; /pair <code> in chat
```

WhatsApp, Discord, and Slack adapters share the same gateway core.

## What's inside

- **Verified memory** — trust tiers T0–T4, a separate verifier model, hash-chained
  audit ledger, cascade revocation. `milyonus memory why <id>` shows the full chain.
- **Skills** — the agent writes its own reusable skills, gated by a
  reproducibility check + security scanner before they go live.
- **Security** — risk-tiered approval, always-on SSRF, credential redaction,
  pre-exec command scanning, DM pairing with lockout.
- **Self-modification** — the agent can edit its own code, behind an automatic
  git snapshot + test gate + one-command rollback.
- **Multi-provider** — Anthropic (default), OpenAI, OpenRouter, local vLLM/Ollama.

## Commands

```
milyonus                     interactive session
milyonus doctor              environment diagnostics
milyonus memory  list|pending|why|diff|revoke|search
milyonus skills  list|view|why
milyonus audit   verify|log
milyonus gateway start|pair
milyonus selfmod log|rollback
```

## Deploy

```bash
docker run --rm -it -v milyonus:/data milyonus/agent   # hardened image
```

See [docs/production.md](docs/production.md) for the production checklist.

## Development

```bash
uv sync --extra dev
uv run pytest -q            # 114 tests, green without an API key
uv run python -m evals.poisonbench.run   # safety benchmark
```

## License

Apache-2.0. "Milyonus" and the star mark are trademarks — see
[TRADEMARK.md](TRADEMARK.md). Contributions welcome; see
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).
