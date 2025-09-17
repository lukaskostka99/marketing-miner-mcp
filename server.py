from typing import Any, Dict, Optional
import httpx
import os
import sys
import traceback
from fastmcp import FastMCP

# --- ZJEDNODUŠENÍ ---
# Inicializace serveru
mcp = FastMCP("marketing-miner")

# Načtení API tokenu z proměnné prostředí, kterou nastaví smithery.yaml
# Pokud proměnná není nastavena, API_TOKEN bude None.
API_TOKEN = os.getenv("MARKETING_MINER_API_TOKEN")

# Diagnostický výpis při startu serveru pro snadné ladění v logu kontejneru
if API_TOKEN:
    print(f"[MCP] INFO: Načten API token MARKETING_MINER_API_TOKEN.", flush=True)
else:
    print("[MCP] WARNING: Proměnná prostředí MARKETING_MINER_API_TOKEN není nastavena!", flush=True)

# Konstanty
API_BASE = "https://profilers-api.marketingminer.com"
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Centrální funkce pro volání Marketing Miner API."""
    # Ochrana: Pokud API klíč chybí, vrátíme srozumitelnou chybu
    if not API_TOKEN:
        return {
            "status": "error",
            "message": "Chyba: Marketing Miner API token nebyl poskytnut. Zkontrolujte konfiguraci a připojení serveru."
        }
    
    async with httpx.AsyncClient() as client:
        try:
            params["api_token"] = API_TOKEN
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            return {"status": "error", "message": f"Chyba API ({e.response.status_code}): {error_text}"}
        except Exception as e:
            return {"status": "error", "message": f"Obecná chyba při volání API: {str(e)}"}

@mcp.tool()
async def get_keyword_suggestions(
    lang: str, 
    keyword: str,
    suggestions_type: Optional[str] = None,
    with_keyword_data: Optional[bool] = False
) -> str:
    """Získá návrhy klíčových slov z Marketing Mineru."""
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Dostupné jazyky jsou: {', '.join(LANGUAGES)}"

    params = {"lang": lang, "keyword": keyword}
    if suggestions_type in ["questions", "new", "trending"]:
        params["suggestions_type"] = suggestions_type
    if with_keyword_data:
        params["with_keyword_data"] = "true"

    data = await make_mm_request(f"{API_BASE}/suggestions", params)
    
    if data.get("status") == "error":
        return data.get("message", "Neznámá chyba")
    
    if "suggestions" in data:
        output = [f"Návrhy pro '{keyword}':"]
        for item in data["suggestions"]:
            line = f"- {item['keyword']}"
            if "search_volume" in item:
                line += f" (Hledanost: {item['search_volume']})"
            output.append(line)
        return "\n".join(output)
    
    return "Odpověď z API neobsahovala očekávaná data."

@mcp.tool()
async def get_keyword_data(lang: str, keyword: str) -> str:
    """Získá detailní data o klíčovém slově (hledanost, CPC atd.)."""
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Dostupné jazyky jsou: {', '.join(LANGUAGES)}"

    params = {"lang": lang, "keyword": keyword}
    data = await make_mm_request(f"{API_BASE}/keyword-data", params)

    if data.get("status") == "error":
        return data.get("message", "Neznámá chyba")

    if "keywords" in data and keyword in data["keywords"]:
        kw_data = data["keywords"][keyword]
        result = [f"Data pro klíčové slovo: '{keyword}'"]
        if "search_volume" in kw_data:
            result.append(f"Průměrná měsíční hledanost: {kw_data.get('search_volume')}")
        if "cpc" in kw_data:
            result.append(f"CPC: {kw_data.get('cpc', {}).get('value')} {kw_data.get('cpc', {}).get('currency')}")
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API."

if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    print(f"[MCP] Booting server on {host}:{port}{path}", flush=True)
    mcp.run(host=host, port=port, path=path)
