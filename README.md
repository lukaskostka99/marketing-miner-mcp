# Marketing Miner MCP

Each user connects with **their own** Marketing Miner API token via the **Connect form** on Smithery (generated from `configSchema`).

## Local
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETING_MINER_API_TOKEN=YOUR_TOKEN HOST=0.0.0.0 PORT=8000 MCP_HTTP_PATH=/mcp
python server.py
```
