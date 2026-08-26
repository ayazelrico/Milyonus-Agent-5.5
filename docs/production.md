# Production deployment checklist

Milyonus is safe by default, but a public deployment should verify each of these
(PLAN §12). Most map directly to a config or environment setting.

1. **Never set `gateway_allow_all_users = true`.** The gateway prints a loud
   warning at startup if it is on. Keep default-deny + DM pairing.
2. **Use a container backend** (`security.sandbox_backend = "docker"`) or run the
   provided hardened image (`deploy/Dockerfile`): read-only rootfs, non-root,
   `cap_drop: ALL`, `no-new-privileges`, `pids_limit`.
3. **Constrain resources** — set container memory/CPU limits.
4. **Store secrets in `~/.milyonus/.env` with `chmod 600`.** Never in
   `config.toml`, never in the repo. `milyonus doctor` checks the permission.
5. **Enable DM pairing** and hand out codes out-of-band. Codes expire in 1 hour.
6. **Audit the command allowlist** and the RiskEngine decisions periodically.
7. **Do not point the workspace at sensitive directories.** The agent's file
   tools are confined to the workspace root you pass to `gateway start`.
8. **Do not run the gateway as root.** Use the `milyonus` system user.
9. **Watch the logs** (`~/.milyonus/logs/`, or the gateway's stdout) and the
   memory audit ledger: `milyonus audit verify` should always pass.
10. **Keep up to date** and re-run `uv run pytest -q` after upgrades.

## Verifying integrity

```bash
milyonus audit verify     # hash-chained memory ledger intact?
milyonus memory pending   # anything stuck in quarantine?
milyonus memory diff --since 7d   # what did it learn recently?
```
