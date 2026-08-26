"""Minimal fake MCP server over stdio for testing the client."""

import json
import sys


def send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    msg = json.loads(line)
    method = msg.get("method")
    rid = msg.get("id")
    if method == "initialize":
        send({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2024-11-05"}})
    elif method == "notifications/initialized":
        pass
    elif method == "tools/list":
        send(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {
                    "tools": [
                        {
                            "name": "echo",
                            "description": "echoes input",
                            "inputSchema": {
                                "type": "object",
                                "properties": {"text": {"type": "string"}},
                            },
                        }
                    ]
                },
            }
        )
    elif method == "tools/call":
        args = msg["params"]["arguments"]
        send(
            {
                "jsonrpc": "2.0",
                "id": rid,
                "result": {"content": [{"type": "text", "text": f"echo: {args.get('text', '')}"}]},
            }
        )
