---
name: observability
description: Yapısal log, metrik ve tracing ile gözlemlenebilirlik
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
    category: sistem
    requires_toolsets: []
    provenance: official
---

# Observability (Loglar · Metrikler · Tracing)

Üç sütun: **loglar** (ne oldu), **metrikler** (ne kadar), **trace** (nerede/ne kadar sürdü).

## Yapısal loglama
- Düz metin değil **JSON** logla: `{"level","ts","msg","request_id","user",...}`.
- Her isteğe bir **correlation/request id** ekle; servisler arası taşı.
- Seviyeleri doğru kullan: DEBUG/INFO/WARN/ERROR. Secret'ları redakte et.
```python
import logging, json

logging.info(json.dumps({"event": "login", "user_id": 42, "ms": 83}))
```

## Metrikler (ne izlenir)
- **RED** (servisler): Rate (istek/s), Errors (hata oranı), Duration (gecikme p50/p95/p99).
- **USE** (kaynaklar): Utilization, Saturation, Errors (CPU/bellek/disk).
- Prometheus + Grafana yaygın; sayaç/histogram export et.

## Tracing
- Bir isteğin servisler arası yolculuğunu span'lerle izle (OpenTelemetry).
- Yavaş uçları bulmak için span sürelerine bak.

## Log analizi (hızlı)
```bash
grep -E "ERROR|Exception" app.log | tail -50
jq 'select(.level=="ERROR")' app.jsonl | jq -s 'length'
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head   # en çok IP
```

> Milyonus'un kendi eval katmanı bu felsefeyi izler: her koşumda token, süre,
> maliyet, tool hatası ve human intervention izlenir (`milyonus eval run`).
