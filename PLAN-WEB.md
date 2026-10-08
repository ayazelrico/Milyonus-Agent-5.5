# Milyonus Agent 5.5 — Web Plan (Surface #7)

> Status: **plan only — nothing implemented.**
> Scope: turning Milyonus Agent 5.5 into a product an end user can open in a
> browser and talk to, the way they talk to ChatGPT — without giving up a single
> guarantee the agent core already makes.
> Companion to [PLAN.md](PLAN.md) (the agent core plan) and
> `~/Documents/Milyonuss/design.md` (the milyonus.com design system).
> Owner: @ayazelrico · License: Apache-2.0

---

## 0. Positioning

Milyonus already runs behind **six surfaces** (CLI/TUI, Telegram, WhatsApp,
Slack, Discord, ACP). The web app is **surface #7** — not a rewrite, not a
second agent. The same `AgentLoop`, the same `MemoryPipeline`, the same
`RiskEngine`.

The product wedge is *not* "another chat box". Every ChatGPT clone hides its
memory and its actions. Milyonus's whole thesis is that memory is **verified,
provenanced, decaying, revocable** and that dangerous actions are **gated**. So
the web UI must **show** what the others hide:

| ChatGPT-style UI | Milyonus web UI |
|---|---|
| "Memory updated" toast | **Memory inspector**: tier, provenance, trust score, decay clock, `why` chain |
| Silent tool execution | **Tool timeline** + **approval card** (allow / deny / allow-for-session) |
| Memory is forever | **Trust decay** visible; demoted items listed; one-click reaffirm (rate-limited) |
| No cleanup path | **Revoke by source** → cascade, shown as a diff |
| "Trust us" | **Audit ledger** verify button; hash-chained, exportable |

> One-line product promise for the web: *you can see everything it learned about
> you, where each line came from, and take any of it back.*

---

## 1. What already exists vs. what is missing

Grounded in the current tree — no new agent capability is required for v1.

| Need | Status | Where |
|---|---|---|
| Streaming turn engine | ✅ exists | `src/milyonus/core/loop.py` — `on_text` / `on_tool` async sinks |
| Tool execution + registry | ✅ exists | `src/milyonus/tools/registry.py` |
| Approval hook | ✅ exists | `AgentLoop.approve: (ToolCall, risk) -> bool` |
| Risk classification | ✅ exists | `src/milyonus/security/risk.py` — `auto` / `confirm` / `block`, irreversible detection |
| Session persistence + full-text search | ✅ exists | `src/milyonus/core/store.py` — SQLite WAL + FTS5 |
| Verified memory + ledger | ✅ exists | `src/milyonus/memory/*` |
| Per-user memory scoping | ⚠️ partial | `build_snapshot(user_ref=…)` scopes the *user* half only; agent notes are **global** |
| Multi-surface session fan-out | ⚠️ partial | `GatewayServer._sessions` is an **in-memory dict** — lost on restart |
| HTTP server | ⚠️ minimal | `src/milyonus/gateway/webhook.py` — one request/connection, no TLS, no auth, no SSE |
| JSON-RPC streaming surface | ✅ reference | `src/milyonus/acp/server.py` — the closest existing model for a web protocol |
| Auth / accounts / tenancy | ❌ missing | pairing (`gateway/pairing.py`) is chat-code based, not web login |
| Quotas / cost per user | ❌ missing | `Budget` is per-process, `observability/cost.py` is per-run |
| Frontend | ❌ missing | design system exists (`design.md`), app does not |

**Conclusion:** the web project is ~80% *transport, identity, and UI* work, and
~20% context/persistence work. The agent brain is done.

---

## 2. What is actually in an AI interface

The user-visible surface, enumerated so nothing gets "discovered" in week six.
Marked **v1** (beta) / **v2** (after beta).

### 2.1 Conversation

| Element | Notes | Phase |
|---|---|---|
| Streaming assistant text | token-by-token, markdown + code highlighting, incremental render | v1 |
| Stop / cancel | must cancel the in-flight turn server-side, not just the stream | v1 |
| Copy / copy-code | per message, per code block | v1 |
| Regenerate | re-runs the last user turn with the same context | v1 |
| Edit & resend | forks the thread (`sessions.parent_id` already exists) | v2 |
| Message actions | 👍/👎 feedback → eval corpus | v2 |
| Citations | research tool returns cited reports — render as footnotes | v1 |
| Error states | provider error, budget exhausted, tool error, network drop + resume | v1 |

### 2.2 Composer

Multiline input (Shift+Enter), file/image attach (vision tools already exist),
paste-image, slash commands (`/model`, `/usage`, `/clear` exist in the TUI —
mirror them), model picker, skill mention (`@skill-name`), token counter,
"thinking / tools enabled" toggles, drag-drop.

### 2.3 Navigation

Session sidebar (list, rename, pin, archive, delete), **search across all
sessions** (FTS5 is already there — `SessionStore.search`), date grouping,
"continue where you left off".

### 2.4 The Milyonus-specific panels (the differentiator)

| Panel | Content | Backed by |
|---|---|---|
| **Tool timeline** | collapsible card per call: name, args, duration, result preview, error | `on_tool` + tracer |
| **Approval card** | blocking, inline: risk reason, findings list, irreversible badge, allow / deny / allow-for-session | `RiskEngine.classify` |
| **Memory inspector** | pending · active · quarantined · rejected · revoked; trust bar; decay countdown | `MemoryStore.by_state` |
| **Why drawer** | provenance chain, evidence hash, verifier verdict, confirmations | `memory why` |
| **Revoke by source** | paste a URL/source → preview cascade → confirm | `revoke_by_source` |
| **Skills** | list, view a SKILL.md, why it fired | `skills/*` |
| **Usage** | tokens, cost, iterations, budget pressure | `observability/cost.py`, `Budget.pressure()` |
| **Audit** | ledger verify, export | `verify_ledger`, `ledger_entries` |

### 2.5 Account & settings

Sign in/out, profile, language (TR/EN/DE/ES like the landing page), theme (dark
only, per `design.md`), provider/model choice, **safe** memory knobs, MCP server
list (read-only in v1), data export, delete account.

**Hard rule:** the web settings surface exposes an *allowlist* of config fields.
Security-relevant fields (`security.*`, `memory.direct_write`,
`gateway_allow_all_users`, T0 keys) are **never** writable from the browser.

### 2.6 Cross-cutting

Empty states, skeletons, optimistic send, offline banner, reconnect with replay,
keyboard shortcuts, `prefers-reduced-motion`, ARIA live region for streamed
text, mobile layout ≥375px, PWA install, consent banner (reuse the landing one).

---

## 3. What happens in the background

### 3.1 One message, end to end

```
browser                 api (FastAPI)            runner (asyncio task)        stores
   │ POST /messages        │                            │                       │
   ├──────────────────────►│ authn + quota + tenant      │                       │
   │                       ├─ append user msg ──────────────────────────────────►│ SessionStore
   │                       ├─ spawn turn ───────────────►│                       │
   │ GET /stream (SSE)     │                            │ build context ◄────────┤ MemoryStore
   ├──────────────────────►│◄─ event log tail ──────────┤   (§4)                 │
   │◄─ text.delta …        │                            │ provider.stream        │
   │◄─ tool.call           │                            │ RiskEngine.classify    │
   │◄─ approval.required   │                            │   └ await decision ────┤ approvals
   │ POST /approvals/{id}  │                            │                        │
   ├──────────────────────►│─ resolve future ──────────►│ tools.run              │
   │◄─ tool.result         │                            │ …loop…                 │
   │◄─ usage, turn.completed                            │ append assistant msg ─►│ SessionStore
   │                       │                            │ memory proposals ─────►│ MemoryPipeline
```

### 3.2 Components

| Component | Responsibility | v1 choice |
|---|---|---|
| **API** | HTTP, auth, validation, quota, tenant resolution | FastAPI + uvicorn, shipped as optional extra `web` |
| **Runner** | owns the turn: builds context, drives `AgentLoop`, writes events | in-process asyncio task, one per active turn |
| **Event log** | every stream event persisted before it is sent | table `turn_events(turn_id, seq, type, payload)` |
| **Stream** | SSE (`text/event-stream`), resumable via `Last-Event-ID` | SSE, not WebSocket (see §6.3) |
| **Approvals** | durable, TTL'd, one-shot decision records | table `approvals` + in-process `asyncio.Future` |
| **Memory writer** | serialized writes to the hash-chained ledger | single writer task / queue (see §7.3) |
| **Jobs** | nightly consolidation, trust decay, cron tasks, proactive suggestions | existing `proactive/scheduler.py` + `cron/` run as a separate worker process |
| **Observability** | per-turn trace, tokens, cost, tool errors | existing `observability/trace.py`, exported per user |

### 3.3 Things that are easy to get wrong (call them out now)

1. **Approval blocks the turn.** `AgentLoop.approve` is an `await` inside the
   loop. On the web this means the turn *pauses indefinitely* waiting for a
   human. Needs: durable approval row, TTL (default **300s**), timeout →
   **deny**, and a UI that can be reloaded without losing the pending state.
2. **Streams must be resumable.** A phone that locks for 10s kills an
   `EventSource`. Persist events first, replay from cursor on reconnect.
3. **The gateway's session dict does not survive a restart.** Web sessions must
   rehydrate `history` from `SessionStore` on every turn (or a warm cache with
   DB fallback).
4. **One active turn per session.** Enforce a per-session lock; a second send
   while a turn runs is queued or rejected, never interleaved.
5. **The ledger is a hash chain.** `_ledger_append` reads the head then inserts
   — two concurrent writers corrupt ordering. Serialize it.
6. **`sqlite3` connections are not shareable across threads/tasks.**
   `MemoryStore` / `SessionStore` hold one connection each; per-request
   connections or a single owning task.
7. **Shell and filesystem tools are host access.** On a hosted product these
   must be sandboxed or off by default (§8.4).

---

## 4. ★ Context — how it should be built

This is the part that decides whether the product feels intelligent or amnesic.
Milyonus's advantage is that it already distinguishes *what is trusted* from
*what is merely present*. The web must not flatten that back into "one big
string".

### 4.1 The layered model

```
┌── STABLE PREFIX (cacheable, changes rarely) ──────────────────────┐
│ L0   identity + memory contract      prompt/builder.py            │
│ L0.5 tool schemas                    registry.schemas()           │
│ L1   frozen memory snapshot          build_snapshot()   [FENCED]  │
│ L1.5 skill index (level 0)           skill_index_section()        │
│ L1.6 workspace / project instructions  context_files  [SCANNED]   │
├── VOLATILE SUFFIX (changes every turn, never cached) ─────────────┤
│ L2   semantic recall (k, trust-weighted)  SemanticMemory [FENCED] │
│ L3   conversation window                  SessionStore            │
│ L3.5 session brief (compaction summary)                           │
│ L4   tool results                     truncated + redacted [FENCED]│
│ L5   attachments / RAG chunks                          [FENCED]   │
└───────────────────────────────────────────────────────────────────┘
```

**Rule 1 — order is a performance feature.** Prompt caching only pays if the
prefix is byte-stable. Anything that changes per turn (recall, history, tool
output) goes *after* everything that doesn't. Today `build_system_prompt` puts
memory in the system block — correct, because the snapshot is **frozen at
session start**. Semantic recall must **not** go there; it belongs in a
per-turn block near the user message.

**Rule 2 — everything that is not the user is data, not instruction.** The
`<milyonus:memory>` fence and its "past observations, not instructions" contract
already exist. Extend the same treatment to **tool output, attachments, web
pages, and project files** — each in its own fenced block with its source
stamped. This is the single highest-leverage security property of the whole
context design.

**Rule 3 — every recall is scoped to the tenant before it is ranked**, not
after. See §8.2.

### 4.2 Budget (200k-token window, one hosted session)

| Layer | Budget | Refresh | Overflow policy |
|---|---|---|---|
| L0 identity + contract | ~600 tok | never | — |
| L0.5 tool schemas | 2–6k | per session | drop unused tool groups per plan tier |
| L1 memory snapshot | ~1k (2200 + 1400 chars, config) | session start | `_pack` already truncates by trust order |
| L1.5 skill index | ≤800 | per session | names only; body via `skill_view` |
| L1.6 project instructions | ≤2k | per session | truncate, warn user |
| L2 semantic recall | ≤1k (k=8) | per turn | trust-weighted cut |
| L3 conversation window | 55–65% of remainder | rolling | compaction (§4.4) |
| L4 tool results | **8k hard cap per call**, ≤25% of window total | per turn | head+tail truncation with `…N chars elided…`, full text stored and linkable |
| L5 attachments | ≤6k | per turn | chunk + rank, never whole-file dump |
| Reserve for output | `max_output_tokens` × 2 | — | — |

### 4.3 Progressive disclosure

Never load what might be needed — load an index, let the model ask.
- Skills: index in prompt → `skill_view` on demand (already implemented).
- Files: tree/preview → `read_file` on demand.
- Memory: snapshot + recall → `memory why` on demand.
- Tool results: preview in context, full body behind a handle.

### 4.4 Compaction (session doesn't die at 200k)

Driven by `Budget.pressure()`:

| Pressure | Action |
|---|---|
| < 55% | nothing |
| 55–75% | summarize the **oldest third** of turns into a *session brief* with the cheap `verifier_model`; keep the last 8 turns verbatim |
| 75–90% | also drop tool-result bodies to their previews; keep the last 4 turns verbatim |
| > 90% | hard cut + banner "this conversation was compacted"; offer "start a linked session" (`parent_id`) |

The session brief is **not memory**. It is turn-scoped, unverified, and never
enters the memory pipeline without passing quarantine → verify → promote like
anything else.

### 4.5 What the web adds that the CLI never had

| New context source | Trust tier | Treatment |
|---|---|---|
| Uploaded file | `third-party` (T3) | injection-scanned, fenced, chunked |
| Pasted web content | `third-party` (T3) | fenced, never auto-promoted |
| Project/workspace instructions | `user-direct` (T1) if authored by the paired account | scanned, fenced, editable in UI |
| Another user in a shared session (v2) | `third-party` (T3) | lower trust, marked in the UI |
| Assistant's own summary (compaction) | `agent-observed` (T2) | turn-scoped only |

### 4.6 What must *never* enter context

Secrets and env values (`security/redact.py`), other tenants' memory, raw
credentials from MCP servers (already env-filtered), full binaries/base64
blobs, unbounded tool output, and any browser-supplied "system prompt" field —
the client does **not** get to set the system prompt.

---

## 5. Architecture

### 5.1 Topology (v1, single node)

```
                    app.milyonus.com (Vite SPA, static/CDN)
                              │ HTTPS  (cookie session)
                    api.milyonus.com (FastAPI + uvicorn)
                     ├── auth / tenancy / quota
                     ├── sessions + SSE event tail
                     ├── approvals
                     ├── memory & audit read APIs
                     └── runner tasks → AgentLoop (core, unchanged)
                              │
                  ~/.milyonus/<tenant>/  (SQLite WAL: state.db, memory)
                              │
                    worker process: cron + proactive + consolidation
```

### 5.2 Why FastAPI and not `gateway/webhook.py`

`webhook.py` is deliberately dependency-free for one job: receiving channel
webhooks. It parses one request per connection, has no TLS, no auth, no
streaming, no routing. The web product needs SSE, cookies, CSRF, OpenAPI, file
upload and middleware. Ship it as an **optional extra** so the core install
stays lean:

```toml
[project.optional-dependencies]
web = ["fastapi>=0.115", "uvicorn[standard]>=0.30", "python-multipart>=0.0.9", "itsdangerous>=2.2"]
```

New package: `src/milyonus/web/` (`app.py`, `auth.py`, `sessions.py`,
`stream.py`, `approvals.py`, `memory_api.py`, `runner.py`, `schemas.py`).
New CLI verb: `milyonus web --host --port` (mirrors `milyonus gateway start`).

### 5.3 Scale path (do not build in v1, do not block it either)

| Concern | v1 | v2 |
|---|---|---|
| DB | SQLite WAL per tenant | Postgres, `tenant_id` column, RLS |
| Event fan-out | DB tail | Redis pub/sub + DB replay |
| Runner | in-process task | queue (Redis/NATS) + worker pool |
| Files | local dir | S3-compatible object store |
| Sessions | cookie | cookie + refresh, device list |

Design v1 so the only thing that changes is the store adapter: no SQLite-specific
SQL outside the store classes, no in-memory state that isn't a cache.

---

## 6. API contract (freeze this before any UI work)

### 6.1 REST

```
POST   /v1/auth/magic-link         {email}            → 202
POST   /v1/auth/verify             {token}            → sets cookie
POST   /v1/auth/logout

GET    /v1/sessions                                   → [{id,title,updated_at,pinned}]
POST   /v1/sessions                {title?}           → {id}
GET    /v1/sessions/{id}                              → {…, messages[]}
PATCH  /v1/sessions/{id}           {title?,pinned?}
DELETE /v1/sessions/{id}
GET    /v1/search?q=                                  → FTS5 hits

POST   /v1/sessions/{id}/messages  {text, attachments[]} → {turn_id}
GET    /v1/sessions/{id}/stream?from=<seq>            → SSE
POST   /v1/sessions/{id}/cancel    {turn_id}

POST   /v1/approvals/{approval_id} {decision}         → decision ∈ allow|deny|allow_session

GET    /v1/memory?state=&q=&page=                     → items + trust + decay
GET    /v1/memory/{id}/why                            → provenance chain
POST   /v1/memory/{id}/reaffirm                       → 429 if rate-limited
POST   /v1/memory/revoke           {source_uri}       → {revoked:[ids]}
GET    /v1/audit/verify                               → {intact: bool, head}

GET    /v1/skills · GET /v1/skills/{name}
GET    /v1/usage?range=                               → tokens, cost, turns
GET    /v1/settings · PUT /v1/settings                → allowlisted fields only
POST   /v1/files                                      → {file_id}
GET    /v1/export                                     → full data export (JSON)
DELETE /v1/account                                    → erasure (see §10)
```

### 6.2 SSE events

```
turn.started        {turn_id, session_id}
text.delta          {turn_id, seq, text}
tool.call           {call_id, name, args_preview, risk}
tool.result         {call_id, ok, duration_ms, preview, truncated, full_ref}
approval.required   {approval_id, call_id, name, args, risk, reason,
                     findings[], irreversible, expires_at}
approval.resolved   {approval_id, decision, by}
memory.proposed     {item_id, tier, state, preview}
usage               {input_tokens, output_tokens, cost_usd, pressure}
turn.completed      {turn_id, stop_reason, message_id}
error               {code, message, retryable}
```

Every event carries a monotonic `seq` per turn and is persisted **before**
being written to the socket. Reconnect replays from `Last-Event-ID`.

### 6.3 SSE over WebSocket

SSE: one-way server→client, plain HTTP, free reconnection + replay semantics,
trivially proxyable. Approvals are rare and latency-tolerant, so they ride a
plain `POST` back. WebSocket buys bidirectionality we need for ~2 events per
turn and costs sticky sessions and a hand-rolled reconnect protocol. Revisit
only if live collaboration (v2) lands.

---

## 7. Data model additions

New tables (in the web layer; core tables untouched):

```sql
users(id, email, created_at, locale, status)
tenants(id, owner_user_id, plan, created_at)             -- v1: 1 user = 1 tenant
turns(id, session_id, user_msg_id, state, started_at, ended_at, stop_reason)
turn_events(turn_id, seq, type, payload_json, created_at)  PK(turn_id, seq)
approvals(id, turn_id, call_id, tool, args_json, risk, reason, irreversible,
          state, decision, decided_by, created_at, expires_at)
attachments(id, tenant_id, session_id, filename, mime, bytes, sha256, path)
quotas(tenant_id, period, tokens_used, cost_usd, turns, updated_at)
api_keys(id, tenant_id, hash, name, created_at, last_used_at)
```

Extensions to existing tables (additive only, matching the store's migration
style): `sessions.pinned`, `sessions.archived_at`, `sessions.tenant_id`.

### 7.3 Serialized memory writes

One process-wide `asyncio.Queue` consumed by a single memory-writer task; all
`MemoryPipeline` promotions/ledger appends go through it. Cheap, preserves the
hash chain, and becomes a Postgres advisory lock in v2 without changing callers.

---

## 8. Security model for the web surface

The agent's security model (7 layers, PLAN §6) is unchanged. These are the
**new** attack surfaces a browser introduces.

### 8.1 Authentication & session

Magic link (v1) or OAuth (v2). `httpOnly; Secure; SameSite=Lax` cookie,
rotating session id, CSRF double-submit token on every mutating request, strict
CORS allowlist (`app.milyonus.com` only), HSTS, CSP with no inline scripts.
API keys are separate, hashed at rest, scoped, revocable.

### 8.2 Tenant isolation — the blocking item

Today `build_snapshot` scopes only the **user-profile** half by `actor`; agent
notes come from `store.active()` which is **global**. On a single-user CLI that
is correct. On a multi-tenant web product it is a **cross-tenant memory leak**.

Two options:

| Option | Work | Risk |
|---|---|---|
| **A. Directory per tenant** (`MILYONUS_HOME=/data/t/<tenant>`) | small | wastes some resources; fine to thousands of tenants |
| **B. `tenant_id` column + scoped queries everywhere** | medium | one missed `WHERE` = leak |

**Recommendation: A for beta**, B behind a migration once Postgres lands. Either
way, add a test that asserts tenant A's memory can never appear in tenant B's
snapshot or recall — in `evals/safety/`, run in CI.

### 8.3 Approval integrity

An approval decision must be bound to `(tenant, session, turn, call_id)` and be
single-use. Never allow the client to send the tool call it is approving — it
approves an **id**, the server holds the payload. `allow_session` is refused for
irreversible calls, exactly as `RiskEngine._is_irreversible` already dictates in
the TUI. Timeout = deny. Every decision hits the audit log.

### 8.4 Tool exposure on a hosted product

`make_shell_tool(root)` and `make_fs_tools(root)` mean **host access**. Hosted
defaults must be:

| Tool group | Hosted default |
|---|---|
| web, research, vision, memory, skills | on |
| fs | on, jailed to a per-tenant workspace dir |
| shell | **off** unless `security.sandbox_backend != "local"` (docker/modal/daytona) |
| email, browser | off; opt-in per tenant with the tenant's own credentials |
| MCP servers | off in v1 (they spawn subprocesses); v2 with per-tenant allowlist |

### 8.5 T0 stays out of the browser

Operator tier (T0) is Ed25519-signed, two-phase, out-of-band. There is **no web
button** that stages or activates a T0 memory, ever. The web UI may *display*
T0 items and the staged queue; signing happens with the CLI. This is the one
place where "make it convenient" is the wrong answer.

### 8.6 Abuse & cost

Per-tenant rate limits (requests/min, turns/hour), hard token + cost ceiling per
period enforced **before** the provider call, per-turn `Budget` unchanged,
circuit breaker on provider errors, upload size/type limits, SSRF protection
already on and non-disableable.

### 8.7 Prompt injection in the new sources

Uploaded files and pasted content run through `security/injection.py` before
they reach context — the same scanner that already gates `AGENTS.md`-style
context files. Findings are surfaced in the UI ("this file was skipped"), not
silently swallowed.

---

## 9. Frontend

### 9.1 Stack

React 19 + TypeScript + Vite + Tailwind + Framer Motion — **identical to the
landing page** (`design.md` §1) so the design system, fonts and motion language
carry over with zero translation. The app lives behind auth, so SSR/SEO is not a
reason to reach for Next.js. State: TanStack Query (server state) + Zustand (UI
state). Markdown: `react-markdown` + `shiki`. Virtualized message list.

### 9.2 Design system reuse — with one thing to resolve

`design.md` and `PLAN.md` disagree on the brand blue:

| Source | Primary | Accent |
|---|---|---|
| `design.md` (milyonus.com) | `#2E6BFF` | `#5CC8FF` |
| `PLAN.md` §1 (agent/terminal) | `#1E4FD8` | `#35C6F4` |

**Decision needed in W0:** pick one token set for the app. Recommendation —
follow `design.md` (the customer-facing brand), and treat the PLAN.md palette as
the terminal-only variant. Everything else carries over unchanged: pure-black
ground, glass panels (`blur(56px)`, `rgba(255,255,255,0.10)`), pill buttons,
24px card radius, Inter Tight + Instrument Serif italic accents, the
`[0.22,1,0.36,1]` easing, `prefers-reduced-motion` respect.

### 9.3 Layout

```
┌─────────┬──────────────────────────────────┬──────────────┐
│ sidebar │  thread (streaming)              │ trust rail   │
│ ─────── │  ┌────────────────────────────┐  │ ──────────── │
│ new     │  │ user bubble                │  │ memories     │
│ search  │  │ assistant (markdown)       │  │ touched      │
│ …       │  │ ▸ tool: web_search  1.2s   │  │ tools run    │
│ sessions│  │ ⚠ approval required  [y/n] │  │ tokens/cost  │
│ ─────── │  └────────────────────────────┘  │ [why] links  │
│ memory  │  [ composer                    ] │              │
│ skills  │                                  │              │
└─────────┴──────────────────────────────────┴──────────────┘
```

Mobile: rail collapses into a bottom sheet; sidebar becomes a drawer; approval
cards become full-width blocking sheets (they must never be missable).

### 9.4 i18n

TR / EN / DE / ES, same four locales as the landing page, same `t()` pattern.
The agent already replies in the user's language (`prompt/builder.py`).

---

## 10. Privacy, export, erasure

Memory is personal data (KVKK/GDPR). Two requirements collide:

- **Right to erasure**: the user can delete everything.
- **Hash-chained ledger**: append-only, tamper-evident.

Resolution: the ledger stores **hashes and actions, not content**. Erasure
tombstones the memory rows (content nulled, `state='erased'`) while the chain
stays verifiable. `GET /v1/export` returns sessions + memory + provenance as
JSON. `DELETE /v1/account` cascades and is documented as irreversible. Write
this down in an ADR (`docs/adr/00XX-web-erasure-vs-ledger.md`) before beta.

---

## 11. Phases

Each phase ends with a demo and a test gate. `make check` stays green throughout.

| Phase | Deliverable | Exit criteria |
|---|---|---|
| **W0 · Decisions** | API contract frozen, token palette resolved, tenancy option A/B chosen, threat model written | contract merged as `docs/web-api.md`; ADRs for tenancy + erasure |
| **W1 · Backend skeleton** | `milyonus/web/` + `milyonus web` CLI, auth, sessions CRUD, history rehydrated from `SessionStore` | can create a session and get a non-streamed answer via curl; tests for auth + tenancy |
| **W2 · Streaming turn** | `turns` + `turn_events`, SSE endpoint, cancel, resume from `Last-Event-ID`, per-session lock | kill the connection mid-turn, reconnect, lose nothing; contract test on every event type |
| **W3 · Approvals** | durable approvals, TTL→deny, single-use, audit entries | `evals/safety` extended: no web path can execute a `confirm`/`block` tool without a valid decision |
| **W4 · Chat MVP (UI)** | sidebar, thread, composer, streaming, tool timeline, approval card, search | a non-technical user completes a task end to end on mobile and desktop |
| **W5 · Memory & trust UI** | inspector, why drawer, revoke cascade preview, reaffirm (rate-limited), audit verify | a poisoned memory planted via PoisonBench is visible, traceable and revocable **in the UI** |
| **W6 · Context engine** | recall as a per-turn block, compaction ladder, attachments, project instructions, injection scan surfacing | a 200k-overflow session continues coherently; cache-hit rate measured before/after |
| **W7 · Hardening** | tenant isolation test, sandboxed tools, quotas, rate limits, cost ceiling, CSP/CSRF, load test | red-team pass on §8; p95 first-token < 1.5s at target concurrency |
| **W8 · Beta** | deploy (compose/K8s), metrics + alerting, docs, TR/EN onboarding, waitlist → invite | 20 external users, zero cross-tenant incidents, cost per session within budget |

Parallelizable: W4 can start against a mocked API as soon as W0 freezes the
contract. W6 is the one phase worth over-investing in — it is what makes the
product feel like it knows you.

---

## 12. Non-goals for v1

Native mobile apps · realtime voice · team/shared workspaces · collaborative
editing · an agent-builder marketplace · plugin store · multi-region · SSO/SAML ·
self-serve MCP server installation · fine-tuning.

---

## 13. Risks & open questions

| # | Risk / question | Note |
|---|---|---|
| 1 | **Whose API key?** platform-paid vs BYO key per tenant | changes pricing, quota design and the provider router; decide in W0 |
| 2 | Approval fatigue — too many cards and users click "allow" blindly | tune `RiskEngine` defaults for hosted; measure allow-rate in W7 |
| 3 | Cross-tenant memory leak (§8.2) | **blocking** for any multi-tenant launch |
| 4 | Shell/browser tools on shared infrastructure | default off; sandbox backend is a prerequisite, not a nice-to-have |
| 5 | SQLite ceiling under concurrent turns | fine for beta; Postgres migration path must stay open |
| 6 | Ledger vs erasure (§10) | needs an ADR before storing a single real user's data |
| 7 | Cost per session with long contexts | compaction + prompt caching are cost features, not polish |
| 8 | Does the memory UI overwhelm normal users? | default to a "quiet" mode; the trust rail is collapsible; the depth is there when asked for |
| 9 | Web pairing vs existing chat pairing | web accounts are a new identity namespace — decide whether a web account can claim an existing Telegram `user_ref` |
| 10 | Where does the frontend live? | separate repo (`milyonus-web`) vs a `web/` dir here; recommendation: separate repo, shared design tokens package |

---

## 14. Immediate next step

W0 is three documents and zero code:

1. `docs/web-api.md` — the frozen contract from §6.
2. `docs/adr/00XX-web-tenancy.md` — option A vs B from §8.2.
3. `docs/adr/00XX-web-erasure-vs-ledger.md` — §10.

Then W1 opens with one file: `src/milyonus/web/app.py`.
