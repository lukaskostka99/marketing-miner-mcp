from typing import Any, Dict, Optional
import httpx
import os
import argparse
from fastmcp import FastMCP

mcp = FastMCP("marketing-miner")

API_BASE = "https://profilers-api.marketingminer.com"

def resolve_token() -> str:
    # 1) ENV z commandFunction
    env_token = os.getenv("MARKETING_MINER_API_TOKEN", "")
    if env_token:
        return env_token
    # 2) CLI fallback z commandFunction
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-token", default="")
    # ignoruj neznámé argumenty (FastMCP si něco přidává)
    args, _ = parser.parse_known_args()
    return args.api_token or ""

API_TOKEN = resolve_token()

SUGGESTIONS_TYPES = ["questions", "new", "trending"]
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if not API_TOKEN:
        return {"status": "error", "message": "Chyba: API token pro Marketing Miner není nastaven. Prosím, nastavte ho v konfiguraci."}
    async with httpx.AsyncClient() as client:
        try:
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
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}."
    if suggestions_type and suggestions_type not in SUGGESTIONS_TYPES:
        return f"Nepodporovaný typ návrhů: {suggestions_type}."

    url = f"{API_BASE}/keywords/suggestions"
    params = {"lang": lang, "keyword": keyword}
    if suggestions_type:
        params["suggestions_type"] = suggestions_type
    if with_keyword_data is not None:
        params["with_keyword_data"] = str(with_keyword_data).lower()

    response_data = await make_mm_request(url, params)
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")

    if response_data.get("status") == "success":
        data = response_data.get("data", {}).get("keywords", [])
        if not data:
            return "Nebyla nalezena žádná data pro tento dotaz."
        result = []
        for kd in data:
            if not isinstance(kd, dict): 
                continue
            info = [f"Klíčové slovo: {kd.get('keyword', 'N/A')}"]
            if "search_volume" in kd:
                info.append(f"Hledanost: {kd.get('search_volume', 'N/A')}")
            result.append(" | ".join(info))
        return "\n".join(result)
    return "Neočekávaný formát odpovědi z API"

@mcp.tool()
async def get_search_volume_data(lang: str, keyword: str) -> str:
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}."
    url = f"{API_BASE}/keywords/search-volume-data"
    params = {"lang": lang, "keyword": keyword}
    response_data = await make_mm_request(url, params)
    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")

    if response_data.get("status") == "success":
        data = response_data.get("data", [])
        if not data:
            return "Nebyla nalezena žádná data pro toto klíčové slovo."
        kd = data[0]
        result = [f"Klíčové slovo: {kd.get('keyword', 'N/A')}", f"Hledanost: {kd.get('search_volume', 'N/A')}"]
        if "cpc" in kd and kd.get("cpc"):
            cpc = kd.get("cpc", {})
            result.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
        return "\n".join(result)
    return "Neočekávaný formát odpovědi z API"

if __name__ == "__main__":
    import sys, traceback
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")

    # Krátký diagnostický výpis – maskujeme hodnotu:
    masked = f"{len(API_TOKEN)} chars" if API_TOKEN else "EMPTY"
    print(f"[MCP] Boot host={host} port={port} path={path} | token={masked}", flush=True)

    for transport in ("http", "ssehttp", "shttp", "sse"):
        try:
            print(f"[MCP] Trying transport={transport}", flush=True)
            if "http" in transport:
                mcp.run(transport=transport, host=host, port=port, path=path)
            else:
                mcp.run(transport=transport)
            sys.exit(0)
        except Exception as e:
            print(f"[MCP] Transport {transport} failed: {e!r}", flush=True)
            traceback.print_exc()
    print("[MCP] ERROR: no working transport found", flush=True)
    sys.exit(1)
