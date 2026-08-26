# ADR-004: Open, self-modifiable core

**Status:** Accepted (2026-08-26)

## Context
The initial framing considered a "sealed core" whose files are integrity-checked
and where the core cannot be monkey-patched. The project owner revised this: the
system should be open and editable, and the agent should be able to actively
modify its own code and skills. Security is to come from **runtime layers**
(approval flows, container isolation, credential filtering, SSRF), not from
locking the core.

## Decision
The core is open (Apache-2.0) and self-modifiable. There is no integrity gate
that blocks edits to core files. Safety for self-modification is provided by the
`selfmod` harness (ADR-005): every change is snapshotted, gated by tests, and
reversible with one command.

## Consequences
- The "sealed core" and "compiled/closed distribution" options are rejected.
- Risk is managed by **reversibility and auditability**, not by prohibition.
- Extension is still encouraged through skill/tool/channel interfaces to keep
  the core small, but nothing prevents core edits.
