from typing import Any, Dict, Optional
import httpx
import os
import sys
import traceback
from fastmcp import FastMCP

# Inicializace serveru
mcp = FastMCP("marketing-miner")

# Konstanty
API_BASE = "https://profilers-api.marketingminer.com"
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

# --- ZMĚNA: Globální API_TOKEN je odstraněn ---
# API_TOKEN = os.getenv("MARKETING_MINER_API_TOKEN", "") # TENTO ŘÁDEK BYL SMAZÁN

async def make_mm_request(api_token: str, url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provede požadavek na Marketing Miner API.
    Nyní přijímá api_token jako argument pro každé volání.
    """
    # --- ZMĚNA: Kontrola tokenu, který přišel jako argument ---
    if not api_token:
        return {"status": "error", "message": "Chyba: Marketing Miner API token nebyl zadán. Připojte se znovu a zadejte jej prosím v konfiguračním formuláři."}
    
    async with httpx.AsyncClient() as client:
        try:
            params["api_token"] = api_token
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"Chyba API ({e.response.status_code}): {e.response.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Obecná chyba při volání Marketing Miner API: {str(e)}"}

@mcp.tool()
async def get_keyword_suggestions(
    config: dict,  # --- ZMĚNA: Přidán 'config' pro přístup k tokenu relace ---
    lang: str,
    keyword: str,
    suggestions_type: Optional[str] = None,
    with_keyword_data: Optional[bool] = False
) -> str:
    """Získá návrhy klíčových slov z Marketing Miner API."""
    api_token = config.get("apiToken") # --- ZMĚNA: Získání tokenu z configu relace ---
    
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    url = f"{API_BASE}/keywords/suggestions"
    params = {"lang": lang, "keyword": keyword}
    if suggestions_type in ["questions", "new", "trending"]:
        params["suggestions_type"] = suggestions_type
    if with_keyword_data:
        params["with_keyword_data"] = "true"
    
    response_data = await make_mm_request(api_token, url, params) # --- ZMĚNA: Předání tokenu ---
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    # Zpracování úspěšné odpovědi...
    return "Zpracovaná data..." # Váš kód pro zpracování odpovědi zde

@mcp.tool()
async def get_search_volume_data(
    config: dict,  # --- ZMĚNA: Přidán 'config' pro přístup k tokenu relace ---
    lang: str,
    keyword: str
) -> str:
    """Získá data o hledanosti klíčového slova z Marketing Miner API."""
    api_token = config.get("apiToken") # --- ZMĚNA: Získání tokenu z configu relace ---

    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    url = f"{API_BASE}/keywords/search-volume-data"
    params = {"lang": lang, "keyword": keyword}
    
    response_data = await make_mm_request(api_token, url, params) # --- ZMĚNA: Předání tokenu ---
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    if response_data.get("status") == "success":
        data = response_data.get("data", [])
        if not data:
            return "Nebyla nalezena žádná data pro toto klíčové slovo."
        
        keyword_data = data[0]
        result = [
            f"Data pro '{keyword_data.get('keyword', 'N/A')}':",
            f"  Hledanost: {keyword_data.get('search_volume', 'N/A')}"
        ]
        if "cpc" in keyword_data and keyword_data.get("cpc"):
            cpc = keyword_data.get("cpc", {})
            result.append(f"  CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
        
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    print(f"[MCP] Booting server on {host}:{port}{path}", flush=True)
    mcp.run(host=host, port=port, path=path)
