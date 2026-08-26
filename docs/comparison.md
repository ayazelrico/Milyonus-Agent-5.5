# Comparison with Hermes-style agents

This page states, factually, how Milyonus differs from the self-evolving agent
design it takes inspiration from. Figures attributed to other systems come from
the public literature cited in the project report; they are for orientation, not
a like-for-like benchmark run on identical inputs.

## The shared idea

Both keep a persistent learning loop: memory that survives across sessions, and
skills the agent authors from experience. That loop is what makes an agent get
more capable the longer it runs.

## Where Milyonus differs

**1. Memory is verified, not trusted on write.**
The reported weakness of Hermes-style memory is a flexible retention policy: most
writes land in durable memory with little checking, which independent studies
associate with high memory-poisoning success (a published figure of ~66.67% ASR).
Milyonus has no direct-write path. Every candidate is quarantined, checked by a
deterministic scanner *and* a separate verifier model, and promoted only under
explicit trust-tier rules. Built-in PoisonBench: 0% ASR / 0% RSR.

**2. Provenance and revocation are first-class.**
Every memory line records its source, session, turn, and an evidence hash, on a
hash-chained ledger. When a source turns out bad, `memory revoke --source <uri>`
cascades to everything derived from it in seconds — not a manual cleanup.

**3. Rejected ideas are remembered.**
A rephrased version of a previously rejected proposal is caught by negative
memory + rephrase detection — the "same idea, new words" case that self-evolving
agents have been observed to miss.

**4. Autonomy is risk-tiered.**
Instead of preferring action under uncertainty across the board, reversible and
local actions run automatically while irreversible or outward-reaching ones
always require approval — and no "always allow" grant can cover that class.

**5. Self-modification is reversible by construction.**
The core is open and the agent can edit it, but every change is snapshotted in
git and gated by the test suite, with one-command rollback.

## What is comparable

Task capability, deployment flexibility (VPS, container, serverless, local
models), and the skills ecosystem are intended to match. The differentiation is
in the safety and verification of the memory that makes the loop work.
