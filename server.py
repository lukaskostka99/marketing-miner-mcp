from typing import Any, List, Optional, Dict, Union
import httpx
import os
import sys
from fastmcp import FastMCP

# Inicializace FastMCP serveru
mcp = FastMCP("marketing-miner")

# --- ÚPRAVA: Načtení API tokenu s vylepšenou diagnostikou ---
# Načteme proměnnou prostředí. Pokud není nastavena, bude hodnota None.
API_TOKEN = os.getenv("MARKETING_MINER_API_TOKEN")

# Diagnostický výpis do logu kontejneru pro snadnější ladění.
# Pro bezpečnost nikdy nevypisujeme samotný token, pouze jeho existenci a délku.
if API_TOKEN:
    print(f"[MCP] INFO: Načten API token MARKETING_MINER_API_TOKEN o délce {len(API_TOKEN)}.", flush=True)
else:
    print("[MCP] WARNING: Proměnná prostředí MARKETING_MINER_API_TOKEN není nastavena. Server očekává, že bude dodána z formuláře.", flush=True)
# --- KONEC ÚPRAVY ---

# Konstanty
API_BASE = "https://profilers-api.marketingminer.com"

# Typy suggestions
SUGGESTIONS_TYPES = ["questions", "new", "trending"]

# Dostupné jazyky
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Provede požadavek na Marketing Miner API s patřičným ošetřením chyb"""
    # --- ÚPRAVA: Kontrola existence API tokenu před odesláním požadavku ---
    if not API_TOKEN:
        return {"status": "error", "message": "Chyba: Marketing Miner API token nebyl zadán. Připojte se znovu a zadejte jej prosím v konfiguračním formuláři."}
    # --- KONEC ÚPRAVY ---
    
    async with httpx.AsyncClient() as client:
        try:
            # Přidáme API token do parametrů
            params["api_token"] = API_TOKEN
            
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"status": "error", "message": f"Chyba API ({e.response.status_code}): {e.response.text}"}
        except Exception as e:
            return {"status": "error", "message": f"Obecná chyba při volání Marketing Miner API: {str(e)}"}

@mcp.tool()
async def get_keyword_suggestions(
    lang: str, 
    keyword: str,
    suggestions_type: Optional[str] = None,
    with_keyword_data: Optional[bool] = False
) -> str:
    """
    Získá návrhy klíčových slov z Marketing Mineru pro daný jazyk a klíčové slovo.
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Dostupné jazyky jsou: {', '.join(LANGUAGES)}"

    params = {"lang": lang, "keyword": keyword}
    if suggestions_type and suggestions_type in SUGGESTIONS_TYPES:
        params["suggestions_type"] = suggestions_type
    
    if with_keyword_data:
        params["with_keyword_data"] = "true"

    data = await make_mm_request(f"{API_BASE}/suggestions", params)
    
    if data.get("status") == "error":
        return data.get("message", "Neznámá chyba")

    if "suggestions" in data:
        suggestions = data["suggestions"]
        output = [f"Návrhy pro '{keyword}':"]
        for item in suggestions:
            line = f"- {item['keyword']}"
            if "search_volume" in item:
                line += f" (Hledanost: {item['search_volume']})"
            output.append(line)
        return "\n".join(output)
    
    return "Odpověď z API neobsahovala očekávaná data."


@mcp.tool()
async def get_keyword_data(
    lang: str,
    keyword: str
) -> str:
    """
    Získá detailní data o klíčovém slově, jako je hledanost, CPC a meziroční změny.
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Dostupné jazyky jsou: {', '.join(LANGUAGES)}"

    params = {"lang": lang, "keyword": keyword}
    data = await make_mm_request(f"{API_BASE}/keyword-data", params)

    if data.get("status") == "error":
        return data.get("message", "Neznámá chyba")

    if "keywords" in data and keyword in data["keywords"]:
        keyword_data = data["keywords"][keyword]
        result = [f"Data pro klíčové slovo: '{keyword}'"]
        
        if "search_volume" in keyword_data:
            result.append(f"Průměrná měsíční hledanost: {keyword_data.get('search_volume')}")
        
        if "cpc" in keyword_data:
            cpc = keyword_data.get("cpc", {})
            result.append(f"CPC: {cpc.get('value')} {cpc.get('currency')}")
        
        if "yoy_change" in keyword_data:
            yoy = keyword_data.get("yoy_change")
            if yoy is not None:
                result.append(f"Meziroční změna: {yoy * 100:.2f}%")
        
        if "peak_month" in keyword_data and keyword_data.get("peak_month"):
            result.append(f"Nejsilnější měsíc: {keyword_data.get('peak_month')}")
        
        if "monthly_sv" in keyword_data and keyword_data.get("monthly_sv"):
            monthly_data = keyword_data.get("monthly_sv", {})
            monthly_result = ["Měsíční hledanost:"]
            
            for month, volume in sorted(monthly_data.items()):
                monthly_result.append(f"  - {month}: {volume}")
            
            result.extend(monthly_result)
        
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"


if __name__ == "__main__":
    import traceback
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    print(f"[MCP] Boot host={host} port={port} path={path}", flush=True)
    for transport in ("http", "ssehttp", "shttp", "sse"):
        try:
            print(f"[MCP] Trying transport={transport}", flush=True)
            mcp.run(transport=transport, host=host, port=port, path=path)
            print(f"[MCP] Transport failed={transport}", flush=True)
        except Exception as e:
            print(f"[MCP] Transport failed={transport} error='{e}'", file=sys.stderr, flush=True)
            traceback.print_exc()
