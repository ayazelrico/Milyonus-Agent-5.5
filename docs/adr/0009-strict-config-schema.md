# ADR-009: Strict config schema

**Status:** Accepted (2026-08-26)

## Context
Silent misconfiguration of a security control is worse than a crash. A typo like
`ssrf_protecton = false` must never be ignored.

## Decision
Config is a Pydantic model with `extra="forbid"`. Unknown keys raise ConfigError
at startup. Security-critical invariants are encoded as `Literal` types that
cannot be set to an unsafe value (e.g. `direct_write: Literal[False]`,
`ssrf_protection: Literal[True]`). A missing config file is valid (defaults apply).

## Consequences
- Typos fail loud at startup, with the offending file and key named.
- Certain guarantees are unexpressible-as-unsafe in config by construction.
