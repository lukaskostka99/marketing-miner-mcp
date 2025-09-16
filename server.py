from typing import Any, List, Optional, Dict, Union
import httpx
import os
from mcp.server.fastmcp import FastMCP

# Inicializace FastMCP serveru
mcp = FastMCP("marketing-miner")

# Konstanty
API_BASE = "https://profilers-api.marketingminer.com"
API_TOKEN = os.getenv("MARKETING_MINER_API_TOKEN", "")

# Typy suggestions
SUGGESTIONS_TYPES = ["questions", "new", "trending"]

# Dostupné jazyky
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Provede požadavek na Marketing Miner API s patřičným ošetřením chyb"""
    async with httpx.AsyncClient() as client:
        try:
            # Přidáme API token do parametrů
            params["api_token"] = API_TOKEN
            
            response = await client.get(url, params=params, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"status": "error", "message": f"Chyba při volání Marketing Miner API: {str(e)}"}

@mcp.tool()
async def get_keyword_suggestions(
    lang: str, 
    keyword: str,
    suggestions_type: Optional[str] = None,
    with_keyword_data: Optional[bool] = False
) -> str:
    """
    Získá návrhy klíčových slov z Marketing Miner API.
    
    Args:
        lang: Kód jazyka (cs, sk, pl, hu, ro, gb, us)
        keyword: Klíčové slovo pro vyhledávání návrhů
        suggestions_type: Volitelný typ návrhů (questions, new, trending)
        with_keyword_data: Zda zahrnout rozšířená data o klíčových slovech
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    if suggestions_type and suggestions_type not in SUGGESTIONS_TYPES:
        return f"Nepodporovaný typ návrhů: {suggestions_type}. Podporované typy jsou: {', '.join(SUGGESTIONS_TYPES)}"
    
    url = f"{API_BASE}/keywords/suggestions"
    
    params = {
        "lang": lang,
        "keyword": keyword
    }
    
    if suggestions_type:
        params["suggestions_type"] = suggestions_type
    
    if with_keyword_data is not None:
        params["with_keyword_data"] = str(with_keyword_data).lower()
    
    response_data = await make_mm_request(url, params)
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    # Zpracování úspěšné odpovědi
    if response_data.get("status") == "success":
        # Upravený kód - správně přistupujeme k datové struktuře
        data = response_data.get("data", {}).get("keywords", [])
        
        if not data:
            return "Nebyla nalezena žádná data pro tento dotaz."
        
        result = []
        for keyword_data in data:
            # Ověřujeme, že keyword_data je slovník
            if not isinstance(keyword_data, dict):
                continue
                
            keyword_info = [f"Klíčové slovo: {keyword_data.get('keyword', 'N/A')}"]
            
            if "search_volume" in keyword_data:
                keyword_info.append(f"Hledanost: {keyword_data.get('search_volume', 'N/A')}")
            
            if "cpc" in keyword_data and keyword_data.get("cpc"):
                cpc = keyword_data.get("cpc", {})
                keyword_info.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
            
            if "difficulty" in keyword_data and with_keyword_data:
                keyword_info.append(f"Obtížnost: {keyword_data.get('difficulty', 'N/A')}")
            
            if "serp_features" in keyword_data and with_keyword_data and keyword_data.get("serp_features"):
                features = ", ".join(keyword_data.get("serp_features", []))
                keyword_info.append(f"SERP features: {features}")
            
            result.append(" | ".join(keyword_info))
        
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"

@mcp.tool()
async def get_search_volume_data(
    lang: str, 
    keyword: str
) -> str:
    """
    Získá data o hledanosti klíčového slova z Marketing Miner API.
    
    Args:
        lang: Kód jazyka (cs, sk, pl, hu, ro, gb, us)
        keyword: Klíčové slovo pro vyhledání dat o hledanosti
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}. Podporované jazyky jsou: {', '.join(LANGUAGES)}"
    
    url = f"{API_BASE}/keywords/search-volume-data"
    
    params = {
        "lang": lang,
        "keyword": keyword
    }
    
    response_data = await make_mm_request(url, params)
    
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")
    
    # Zpracování úspěšné odpovědi
    if response_data.get("status") == "success":
        data = response_data.get("data", [])
        
        if not data or len(data) == 0:
            return "Nebyla nalezena žádná data pro toto klíčové slovo."
        
        # Vezmeme první výsledek (při GET requestu by měl být jen jeden)
        keyword_data = data[0]
        
        result = [
            f"Klíčové slovo: {keyword_data.get('keyword', 'N/A')}",
            f"Hledanost: {keyword_data.get('search_volume', 'N/A')}"
        ]
        
        if "cpc" in keyword_data and keyword_data.get("cpc"):
            cpc = keyword_data.get("cpc", {})
            result.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
        
        if "yoy_change" in keyword_data:
            yoy = keyword_data.get("yoy_change")
            if yoy is not None:
                result.append(f"Meziroční změna: {yoy * 100:.2f}%")
        
        if "peak_month" in keyword_data and keyword_data.get("peak_month"):
            result.append(f"Nejsilnější měsíc: {keyword_data.get('peak_month')}")
        
        if "monthly_sv" in keyword_data and keyword_data.get("monthly_sv"):
            monthly_data = keyword_data.get("monthly_sv", {})
            monthly_result = ["Měsíční hledanost:"]
            
            for month, volume in monthly_data.items():
                monthly_result.append(f"  - Měsíc {month}: {volume}")
            
            result.extend(monthly_result)
        
        return "\n".join(result)
    
    return "Neočekávaný formát odpovědi z API"

if __name__ == "__main__":
    # Spuštění serveru: ve Smithery MUSÍ běžet Streamable HTTP
    transport = os.getenv("MCP_TRANSPORT", "http").lower()
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    if transport == "http":
        mcp.run(transport="http", host=host, port=port, path=path)
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    else:
        mcp.run(transport="stdio")
