# Marketing Miner MCP

Model Context Protocol (MCP) server for Marketing Miner keyword endpoints.

## Connect (per-user API key)
- Use the **Connect** form on Smithery (generated from `configSchema`) and enter your `Marketing Miner API Token`.
- Smithery passes it only to your session as `MARKETING_MINER_API_TOKEN`.

## Local run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETING_MINER_API_TOKEN=YOUR_TOKEN
export HOST=0.0.0.0 PORT=8000 MCP_HTTP_PATH=/mcp
python server.py
```
