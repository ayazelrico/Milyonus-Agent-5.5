# Security Policy

Milyonus Agent takes an assume-breach stance: the agent reads untrusted content
(web pages, emails, group chats, third-party skills) and must never let that
content silently rewrite what it believes or execute privileged actions.

## Reporting a vulnerability

Please report suspected vulnerabilities privately via GitHub Security Advisories
on the repository, or by email to the maintainers listed in `pyproject.toml`.
Do not open a public issue for a security report. We aim to acknowledge within
72 hours.

## Design guarantees (what a report can hold us to)

- **No direct memory write.** Every memory candidate goes through
  Ingest → Quarantine → Verify → Promote. A path that writes durable memory
  without verification is a security bug.
- **Memory is data, not instructions.** Stored memory is rendered inside a
  data fence and never executed as a command.
- **Irreversible/outward actions require approval** and this cannot be waived
  by a blanket "always allow".
- **SSRF protection is always on** and fail-closed.
- **Credentials are filtered** out of subprocess env and redacted from output.

See `PLAN.md` §4 and §6 for the full model.
