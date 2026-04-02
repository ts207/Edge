# Edge ChatGPT App Scaffold

This package is the first scaffold for a ChatGPT app built on the Apps SDK and the Edge operator workflow.

## Current shape

- `handlers.py` wraps existing Edge operator and reporting functions, including Codex via the documented `codex mcp-server` surface.
- `tool_catalog.py` defines the initial tool list, input models, and reviewer-facing hint classifications.
- `resources.py` exposes the widget URI and HTML resource payload.
- `server.py` builds the MCP blueprint and reserves the live FastMCP binding point.
- `cli.py` prints the backlog, blueprint, and widget payload, and is the entry point for the eventual server.

## Immediate next step

Install the Python MCP SDK and run the mounted Streamable HTTP server.

## Commands

- `edge-chatgpt-app backlog`
- `edge-chatgpt-app blueprint`
- `edge-chatgpt-app widget`
- `edge-chatgpt-app serve --host 127.0.0.1 --port 8000`

The live server expects the Python MCP runtime and its HTTP stack to be installed via `pip install "mcp[cli]"`.
