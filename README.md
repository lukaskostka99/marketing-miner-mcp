# Marketing Miner MCP

An MCP server that exposes **Marketing Miner** keyword endpoints to AI assistants (Claude Desktop, Cursor, LibreChat, etc.) via the Model Context Protocol.

> **Security**: The API token is **not** hard-coded. Provide it via the `MARKETING_MINER_API_TOKEN` environment variable (or through Smithery's per-connection secret `apiToken`).

## Features
- Query keyword **suggestions**: `questions | new | trending`
- Get **related keywords** and **monthly search volumes**
- Designed with [FastMCP](https://pypi.org/project/mcp/) for a clean Python tool interface

## Quickstart (local)
```bash
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export MARKETING_MINER_API_TOKEN=YOUR_TOKEN   # PowerShell: $env:MARKETING_MINER_API_TOKEN='YOUR_TOKEN'
python server.py
```

Then add the server to your MCP client (e.g., Claude Desktop) as a **stdio** server running the above command.

## Deploy with Smithery (HTTP / Hosted)
1. Push this repository to GitHub.
2. Go to **https://smithery.ai/new**, authenticate with GitHub, and choose your repo.
3. Smithery detects `Dockerfile` and `smithery.yaml`. In the server settings, set the **base directory** to the repo root (or subfolder if you move files later).
4. In the **Session Config** UI, provide your `apiToken` (stored securely by Smithery). This is injected as `MARKETING_MINER_API_TOKEN` for each connection.
5. Deploy. You’ll get a hosted URL and a server page on Smithery you can share or connect from clients (LibreChat, Cursor, Retool, etc.).

## Config Reference
- `smithery.yaml` defines the start mode (**stdio**) and the per-connection schema.
- `Dockerfile` builds a Python 3.11 image with the necessary dependencies.
- `requirements.txt` lists Python dependencies.
- `server.py` contains the MCP tools and logic.

## Migrating to HTTP (optional / future-proofing)
Smithery is guiding servers toward **Streamable HTTP**. This repo currently runs in **stdio** mode for compatibility.
When you’re ready to migrate, you can:
- Replace the `startCommand.type` with `http`
- Expose a small HTTP wrapper (e.g., FastAPI/Uvicorn) that uses the MCP server's HTTP transport
- Provide a `urlFunction` in `smithery.yaml` that returns the server's URL

## License
MIT


### Transport

This server uses **FastMCP v2** with **Streamable HTTP** (path `/mcp`). On Smithery, only HTTP is supported.

