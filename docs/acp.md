# Editor integration (ACP)

Milyonus speaks the [Agent Client Protocol](https://agentclientprotocol.com)
(ACP), so ACP-capable editors (e.g. Zed) can drive it as a native agent over
stdio.

## Run

Point your editor's ACP agent configuration at:

```
command: milyonus
args: ["acp"]
```

Milyonus then serves newline-delimited JSON-RPC on stdin/stdout, handling
`initialize`, `session/new`, and `session/prompt` (streaming assistant text and
tool calls back as `session/update` notifications). Your provider key is read
from `~/.milyonus/.env` as usual.

The same verified-memory, skills, and security layers apply inside the editor —
ACP is just another surface over the one agent core.
