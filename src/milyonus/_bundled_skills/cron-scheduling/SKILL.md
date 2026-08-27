---
name: cron-scheduling
description: Scheduled tasks with cron expressions
version: 1.0.0
platforms:
- macos
- linux
metadata:
  milyonusagentskill:
    tags:
    - cron
    - scheduling
    category: system
    requires_toolsets:
    - terminal
    provenance: official
---

# Cron Scheduling
- **Edit:** `crontab -e` ; list `crontab -l`
- **Format:** `minute hour day month weekday command`
- **Examples:** hourly `0 * * * *` ; daily 09:00 `0 9 * * *` ; Mondays `0 9 * * 1`
- **Every 15 min:** `*/15 * * * *`
- Capture output: `... >> /var/log/task.log 2>&1`
- Validate the expression (minute/hour/day/month/weekday)
