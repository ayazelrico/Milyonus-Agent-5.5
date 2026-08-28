"""A minimal stdio MCP server used by test_mcp.py.

Speaks just enough of the protocol (initialize, tools/list, tools/call) to let
the real MCPClient/MCPManager connect to it. Exposes one tool, `echo`.
"""

import json
import sys


def _send(obj):
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        msg = json.loads(line)
        method = msg.get("method")
        rid = msg.get("id")
        if method == "initialize":
            _send({"jsonrpc": "2.0", "id": rid, "result": {"protocolVersion": "2024-11-05"}})
        elif method == "notifications/initialized":
            continue  # notification: no reply
        elif method == "tools/list":
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {
                        "tools": [
                            {
                                "name": "echo",
                                "description": "Echo the given text.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {"text": {"type": "string"}},
                                    "required": ["text"],
                                },
                            }
                        ]
                    },
                }
            )
        elif method == "tools/call":
            args = msg.get("params", {}).get("arguments", {})
            text = args.get("text", "")
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": rid,
                    "result": {"content": [{"type": "text", "text": f"echo: {text}"}]},
                }
            )
        else:
            _send({"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "unknown"}})


if __name__ == "__main__":
    main()
