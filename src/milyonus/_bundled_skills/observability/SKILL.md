---
name: observability
description: Observability with structured logs, metrics and tracing
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - logging
    - metrics
    - tracing
    - observability
    category: system
    requires_toolsets: []
    provenance: official
---

# Observability (Logs · Metrics · Tracing)
Three pillars: **logs** (what happened), **metrics** (how much), **traces** (where/how long).
## Structured logging
- Log **JSON**, not plain text: `{"level","ts","msg","request_id","user",...}`.
- Add a **correlation/request id** to each request; carry it across services.
- Use levels correctly: DEBUG/INFO/WARN/ERROR. Redact secrets.
```python
import logging, json

logging.info(json.dumps({"event": "login", "user_id": 42, "ms": 83}))
```
## Metrics (what to watch)
- **RED** (services): Rate (req/s), Errors (error rate), Duration (latency p50/p95/p99).
- **USE** (resources): Utilization, Saturation, Errors (CPU/memory/disk).
- Prometheus + Grafana are common; export counters/histograms.
## Tracing
- Follow a request across services with spans (OpenTelemetry).
- Look at span durations to find slow hops.
## Quick log analysis
```bash
grep -E "ERROR|Exception" app.log | tail -50
jq 'select(.level=="ERROR")' app.jsonl | jq -s 'length'
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head   # top IPs
```
> Milyonus's own eval layer follows this philosophy: every run tracks tokens,
> time, cost, tool errors and human interventions (`milyonus eval run`).
