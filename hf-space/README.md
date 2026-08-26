---
title: Milyonus Agent 5.5
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 4.44.0
app_file: app.py
pinned: true
license: apache-2.0
short_description: Poison-proof agent memory — try to poison it, watch it blocked.
---

# 🛡️ Milyonus — Verified Memory (live poison test)

A free, key-less demo of the [Milyonus Agent](https://github.com/ayazelrico/Milyonus-Agent-5.5)
verified-memory pipeline. Paste a memory candidate, choose its source, and watch
the structure accept or reject it — and explain why.

Runs the deterministic rule-based verifier (no LLM, no cost). On the built-in
PoisonBench (45 cases): **0% attack success** vs a published 66.67% for
flexible-write memory.
