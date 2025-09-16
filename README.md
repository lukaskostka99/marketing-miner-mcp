# Marketing Miner MCP

Python MCP server exposing Marketing Miner keyword endpoints.

## Deploy on Smithery
- `startCommand.type: http` (Streamable HTTP)
- Per-connection secrets in **Session Config** (UI): `apiToken` → injected as `MARKETING_MINER_API_TOKEN`
- Default endpoint: `http://HOST:PORT/mcp`

## Local run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETING_MINER_API_TOKEN=YOUR_TOKEN
export HOST=0.0.0.0 PORT=8000 MCP_HTTP_PATH=/mcp
python server.py
```
