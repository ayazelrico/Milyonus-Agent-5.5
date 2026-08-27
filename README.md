<div align="center">

<img src="assets/brand/milyonus-wordmark.png" width="660" alt="Milyonus"/>

### ✦ Agent 5.5 — *Remembers. Verifies. Evolves.*

An open-source, self-improving autonomous agent with a **verified-memory core** —
it closes the biggest gap in self-evolving agents: *who wrote this memory, and was it checked?*

[![CI](https://github.com/ayazelrico/Milyonus-Agent-5.5/actions/workflows/ci.yml/badge.svg)](https://github.com/ayazelrico/Milyonus-Agent-5.5/actions)
[![License](https://img.shields.io/badge/license-Apache--2.0-1E4FD8.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%2B-35C6F4.svg)](pyproject.toml)
[![Version](https://img.shields.io/badge/version-5.5.0-071233.svg)](CHANGELOG.md)
[![Tests](https://img.shields.io/badge/tests-157%20passing-22C55E.svg)](tests)
[![PoisonBench](https://img.shields.io/badge/PoisonBench%20ASR-0%25-22C55E.svg)](docs/benchmarks.md)

</div>

---

## Table of contents

- [Why Milyonus](#why-milyonus)
- [Quick start](#quick-start)
- [Talk to it from anywhere](#talk-to-it-from-anywhere)
- [Verified memory — the core idea](#-verified-memory--the-core-idea)
- [Skills — procedural memory](#-skills--procedural-memory)
- [Security model](#-security-model)
- [Self-modification](#-self-modification)
- [Architecture](#architecture)
- [Benchmarks](#benchmarks)
- [CLI reference](#cli-reference)
- [Deployment](#deployment)
- [Development](#development)
- [Roadmap](#roadmap)
- [License &amp; trademark](#license--trademark)

---

## Why Milyonus

Most agents start from zero every session. The ones that *do* remember tend to
believe whatever gets written to memory — which makes them easy to **poison**.
Milyonus keeps the learning loop (persistent memory + self-authored skills) but
makes every memory **earn its place**.

| | Typical self-evolving agent | **Milyonus** |
|---|---|---|
| Memory write | Agent writes directly | **Ingest → Quarantine → Verify → Promote** |
| Provenance | Not tracked | Every line: who · from where · which turn · what evidence |
| Poison cleanup | Manual | `memory revoke --source <uri>` cascades in **seconds** |
| Rejected ideas | Forgotten (rephrase slips through) | **Negative memory** + rephrase detection |
| Memory in prompt | Injected as text | Rendered in a **data fence** — "not instructions" |
| Autonomy | "Act first" (risk multiplier) | **Risk-tiered**: reversible → auto, irreversible → always confirm |
| Self-modification | — | Open core, gated by **git snapshot + test + rollback** |

> Measured on the built-in **PoisonBench** (45 cases): **ASR 0% · RSR 0% · 100% legitimate promotion** — see [docs/benchmarks.md](docs/benchmarks.md).

---

## Quick start

```bash
# 1. install uv  (https://astral.sh/uv)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. install Milyonus
uv tool install milyonus-agent        # or: git clone && uv sync

# 3. configure and run
milyonus setup                        # pick a provider
milyonus doctor                       # verify the environment
milyonus                              # start an interactive session
```

Put your key in `~/.milyonus/.env` (mode `600` — `milyonus doctor` checks this):

```bash
echo 'ANTHROPIC_API_KEY=sk-ant-...' > ~/.milyonus/.env && chmod 600 ~/.milyonus/.env
```

Multi-provider: **Anthropic** (default, most poisoning-resistant), **OpenAI**,
**OpenRouter**, and **local** (Ollama / vLLM).

---

## Talk to it from anywhere

The same agent core runs behind **six surfaces**, all default-deny with in-chat approval:

<div align="center">

| Surface | Transport | Setup |
|---|---|---|
| 🖥️ **CLI / TUI** | terminal | `milyonus` |
| ✈️ **Telegram** | Bot API (long-poll) | `milyonus gateway start --channel telegram` |
| 💬 **WhatsApp** | Cloud API (webhook) | `milyonus gateway start --channel whatsapp` |
| 🟣 **Slack** | Events API (webhook) | `milyonus gateway start --channel slack` |
| 🎮 **Discord** | Gateway (WebSocket) | `milyonus gateway start --channel discord` |
| 📝 **Editor (ACP)** | stdio / JSON-RPC | `milyonus acp` (Zed, …) |

</div>

Pairing keeps it private:

```bash
milyonus gateway pair telegram        # → a one-time code
milyonus gateway start                # user sends /pair <code> in chat
```

---

## ✦ Verified memory — the core idea

Milyonus has **no direct-write path** to durable memory. Every candidate flows
through a pipeline before it is trusted:

```
 memory candidate
      │
      ▼
 ┌──────────┐   ┌─────────────┐   ┌──────────────────────┐   ┌──────────┐
 │  Ingest  │──▶│  Quarantine │──▶│  Verify              │──▶│ Promote  │
 │          │   │ + provenance│   │ scanner + verifier   │   │ (ledger) │
 └──────────┘   └─────────────┘   │ model + tier rules   │   └──────────┘
                                  └──────────┬───────────┘
                                             │ reject
                                             ▼
                                     negative memory
                                   (rephrase detection)
```

**Trust tiers** decide how a claim is promoted:

| Tier | Source | Rule |
|---|---|---|
| **T0** | operator config | permanent, agent can't change |
| **T1** | paired user, direct | promote instantly if it passes the scanner |
| **T2** | agent first-hand observation | verifier approval |
| **T3** | third-party (web, email, group) | 2 independent confirmations + verifier; else expires |
| **T4** | subagent / unknown | never auto-promotes — user approval only |

Every line is **provenance-stamped** and recorded on a **hash-chained ledger**.
Ask it anything:

```bash
milyonus memory why <id>       # full provenance chain + evidence hash
milyonus memory revoke --source https://bad.example   # cascade in seconds
milyonus memory diff --since 7d
milyonus audit verify          # ledger integrity intact?
```

Memory reaches the prompt inside a `<milyonus:memory>` **data fence** with an
explicit rule that it is *past observation, not instruction* — imperatives inside
memory are never executed.

---

## ✦ Skills — procedural memory

The agent loads on-demand instruction docs (agentskills.io-compatible) and
**writes its own** from experience. Unlike other agents, a generated skill is
**verified, not trusted on write**: it must pass a reproducibility gate + security
scanner before it goes live.

**36 official skills ship bundled** — ready on first install:

```
git · github-cli · docker · docker-compose · kubernetes · pytest · uv · ripgrep
jq · sqlite · postgres · pandas · csv · ffmpeg · imagemagick · tar · ssh · cron
systemd · curl · bash · regex · markdown · env-secrets · web-scraping · pdf
github-actions · terraform · aws-cli · fastapi · playwright · security-audit
rag-retrieval · prompt-engineering · debugging · observability
```

```bash
milyonus skills list           # browse
milyonus skills view git-workflow
milyonus skills why <name>     # provenance: official | self-learned | hub
```

---

## ✦ Security model

Defense-in-depth, on by default:

1. **Risk-tiered approval** — reversible/local runs automatically; irreversible or
   outward-reaching actions **always** confirm, and no "always allow" can cover that class.
2. **DM pairing** — 8-char crypto codes, 1h TTL, rate limit, lockout, `chmod 600`.
3. **Sandbox** — `local · docker · ssh · modal · daytona`; hardened container image.
4. **Credential filtering** — secrets stripped from subprocess env, redacted from output.
5. **Injection scanning** — memory candidates *and* context files (`AGENTS.md`,
   `.cursorrules`, …) scanned before they can reach the prompt.
6. **SSRF** — always-on, fail-closed; blocks private/loopback/link-local/cloud-metadata.
7. **Pre-exec scanning + audit** — fork bombs, `rm -rf /`, `curl | bash` blocked;
   every action hash-chained in the ledger.

> `SafetyRegression` suite: **0 findings**.

---

## ✦ Self-modification

The core is open and the agent **can edit its own code** — nothing blocks it.
Safety comes from **reversibility**, not prohibition:

```
snapshot (git)  →  agent edits  →  pytest gate  →  ✅ keep  /  ❌ auto-rollback
```

```bash
milyonus selfmod log
milyonus selfmod rollback [--to <tag>]
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  SURFACES   CLI/TUI · Telegram · WhatsApp · Slack · Discord · ACP │
├──────────────────────────────────────────────────────────────┤
│  CORE       AgentLoop · PromptBuilder · Budget · ProviderRouter │
│             (anthropic | openai | local)                       │
├──────────────────────────────────────────────────────────────┤
│  CAPABILITY ToolRegistry · Skills · MCP client · Delegation    │
├──────────────────────────────────────────────────────────────┤
│  MEMORY ★   Ingest→Quarantine→Verify→Promote · Ledger          │
│             SessionStore(FTS5) · NegativeMemory · Revocation   │
├──────────────────────────────────────────────────────────────┤
│  SECURITY   RiskEngine · Approval · Sandbox · SSRF · Redaction │
│             InjectionScanner · PreExecScanner · AuditLog       │
├──────────────────────────────────────────────────────────────┤
│  INFRA      SQLite/WAL · strict ConfigSchema · Telemetry(opt)  │
└──────────────────────────────────────────────────────────────┘
```

---

## Benchmarks

Reproducible, in-repo. Run them yourself:

```bash
uv run python -m evals.poisonbench.run          # memory-poisoning resistance
uv run python -m evals.safety.run               # approval-bypass regression
```

| Suite | Metric | Milyonus | Reference |
|---|---|---|---|
| **PoisonBench** | Attack Success Rate | **0.0%** | Hermes 66.67% |
| **PoisonBench** | Retention/Success Rate | **0.0%** | Hermes 64.70% |
| **PoisonBench** | Legitimate promotion | **100%** | — |
| **SafetyRegression** | Approval bypasses | **0** | — |

Details and methodology: [docs/benchmarks.md](docs/benchmarks.md) ·
[docs/comparison.md](docs/comparison.md).

---

## CLI reference

```
milyonus                     interactive session
milyonus setup               first-run wizard
milyonus doctor              environment diagnostics
milyonus memory   list | pending | why | diff | revoke | search | consolidate
milyonus skills   list | view | why
milyonus audit    verify | log
milyonus gateway  start | pair
milyonus selfmod  log | rollback
milyonus cron     add | list | remove   # scheduled tasks (NL/cron/interval)
milyonus proactive start | suggest    # run the scheduler; suggest automations
milyonus eval     run | tasks    # task-level evaluation + cost/observability
milyonus acp                 run as an editor agent (ACP)
```

---

## Deployment

```bash
# hardened container (non-root, read-only rootfs via compose, cap-drop)
docker run --rm -it -v milyonus-data:/data milyonus/agent:5.5.0 doctor

# production gateway on a VPS
docker compose -f deploy/compose.yaml up -d
```

Guides: [docs/docker.md](docs/docker.md) · [docs/production.md](docs/production.md)
· [docs/publishing.md](docs/publishing.md).

---

## Development

```bash
uv sync --extra dev --extra discord
uv run pytest -q            # 150 tests, green without an API key
make check                 # lint + format-check + test
```

Extend Milyonus through the **skill**, **tool**, or **channel adapter** interfaces
— the verified-memory core stays small and auditable. See
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md).

---

## Roadmap

- [x] Verified-memory core · trust tiers · ledger · revocation
- [x] Agent-authored skills + 26 bundled
- [x] 6 surfaces (CLI, Telegram, WhatsApp, Slack, Discord, ACP)
- [x] Self-modification harness · subagent delegation · MCP
- [x] Hardened Docker · automated PyPI + Docker Hub release
- [x] Task-level evaluation & observability (success, tools, tokens, cost)
- [x] Proactivity: scheduler (NL→cron), safety policy, automation suggestions
- [x] Integrations: email (IMAP/SMTP), browser (Playwright), vision (image input)
- [ ] Vector/embedding layer for memory similarity (opt-in)
- [ ] Honcho-style cross-session user modelling
- [ ] Larger PoisonBench corpus + third-party audit

---

## License &amp; trademark

Apache-2.0 — see [LICENSE](LICENSE). **"Milyonus"** and the star mark are
trademarks; the code license does not grant rights to the name or marks. See
[TRADEMARK.md](TRADEMARK.md). Forks should adopt a distinct name and replace the
assets in `assets/brand/`.

<div align="center">
<br>
<img src="assets/brand/milyonus-mark.png" width="80" alt="Milyonus"/>
<br>
<em>Remembers. Verifies. Evolves.</em>

<em>Ayaz Elrico | Milyonus INC </em>
<em>ayaz@milyonus.com </em>
 
</div>







