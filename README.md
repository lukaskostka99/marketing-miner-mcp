# Marketing Miner MCP

> Připojte Marketing Miner k Cursor, Claude, Windsurf a dalším AI asistentům.

MCP server pro analýzu klíčových slov a hledanost pomocí Marketing Miner API.

## Použití přes Smithery (Doporučeno)

Nejjednodušší způsob použití je přes Smithery hosted URL:

1. Jděte na [smithery.ai](https://smithery.ai) 
2. Vyhledejte "marketing-miner-mcp"
3. **Zadejte své API klíče** v Smithery Connect formuláři
4. Získejte remote hosted URL
5. Přidejte do svého MCP klienta

### SHTTP (pro klienty s podporou):
```json
{
  "mcpServers": {
    "marketing-miner": {
      "url": "your-smithery-url.com"
    }
  }
}
```

### Pro klienty bez SHTTP podpory:
```json
{
  "mcpServers": {
    "marketing-miner": {
      "command": "npx",
      "args": ["mcp-remote", "your-smithery-url.com"]
    }
  }
}
```

## Lokální spuštění

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export MARKETING_MINER_API_TOKEN=YOUR_TOKEN
python server.py
```

## API Token

Získejte svůj API token na [Marketing Miner API](https://www.marketingminer.com/cs/features/api)
