from typing import Any, Dict, Optional
import httpx
import os
from fastmcp import FastMCP

# Inicializace FastMCP serveru
mcp = FastMCP("marketing-miner")

# Konstanty
API_BASE = "https://profilers-api.marketingminer.com"
# Klíč se načte JEDNOU při startu serveru z proměnné prostředí.
API_TOKEN = os.getenv("MARKETING_MINER_API_TOKEN", "")

# Typy suggestions
SUGGESTIONS_TYPES = ["questions", "new", "trending"]

# Dostupné jazyky
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Provede požadavek na Marketing Miner API s patřičným ošetřením chyb"""
    # Zkontrolujeme, zda byl token při startu serveru vůbec načten.
    if not API_TOKEN:
        return {"status": "error", "message": "Chyba: API token pro Marketing Miner není nastaven. Prosím, nastavte ho v konfiguraci a restartujte server."}
        
    async with httpx.AsyncClient() as client:
        try:
            params["api_token"] = API_TOKEN
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"Chyba při volání Marketing Miner API: {str(e)}"}

@mcp.tool()
async def get_search_volume_data(lang: str, keyword: str) -> str:
    """Získá data o hledanosti klíčového slova z Marketing Miner API."""
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    url = f"{API_BASE}/keywords/search-volume-data"
    params = {"lang": lang, "keyword": keyword}
    response_data = await make_mm_request(url, params)
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    if response_data.get("status") == "success":
        data = response_data.get("data", [])
        if not data:
            return "Nebyla nalezena žádná data pro toto klíčové slovo."
        
        kd = data[0] # keyword_data
        result = [f"Klíčové slovo: {kd.get('keyword', 'N/A')}", f"Hledanost: {kd.get('search_volume', 'N/A')}"]
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"

# ... (ostatní nástroje jako get_keyword_suggestions by se opravily stejným způsobem) ...


if __name__ == "__main__":
    import sys, traceback
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    print(f"[MCP] Boot host={host} port={port} path={path}", flush=True)
    
    for transport in ("http", "ssehttp", "shttp", "sse"):
        try:
            if "http" in transport:
                mcp.run(transport=transport, host=host, port=port, path=path)
            else:
                mcp.run(transport=transport)
            sys.exit(0)
        except Exception:
            traceback.print_exc()
    sys.exit(1)
