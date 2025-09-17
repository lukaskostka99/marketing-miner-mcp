from typing import Any, Dict, Optional
import os
import argparse
import sys
import traceback
import httpx
from fastmcp import FastMCP

# =========================
#  Marketing Miner MCP
#  - čte token z ENV i z CLI (--api-token)
#  - bezpečná diagnostika: loguje jen délku tokenu
# =========================

# Inicializace FastMCP serveru
mcp = FastMCP("marketing-miner")

# Konstanty
API_BASE = "https://profilers-api.marketingminer.com"

# Povolené hodnoty
SUGGESTIONS_TYPES = ["questions", "new", "trending"]
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]


def resolve_token() -> str:
    """
    Vrátí API token z ENV (MARKETING_MINER_API_TOKEN) nebo z CLI argumentu (--api-token).
    """
    env_token = os.getenv("MARKETING_MINER_API_TOKEN", "")
    if env_token:
        return env_token

    # CLI fallback – ignoruj neznámé argumenty (FastMCP si něco může přidávat)
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-token", default="")
    args, _ = parser.parse_known_args()
    return args.api_token or ""


API_TOKEN = resolve_token()


async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Provede požadavek na Marketing Miner API s patřičným ošetřením chyb.
    """
    if not API_TOKEN:
        return {
            "status": "error",
            "message": "Chyba: API token pro Marketing Miner není nastaven. Prosím, nastavte ho v konfiguraci.",
        }

    async with httpx.AsyncClient() as client:
        try:
            params = dict(params or {})
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
    with_keyword_data: Optional[bool] = False,
) -> str:
    """
    Získá návrhy klíčových slov z Marketing Miner API.

    Parametry:
      - lang: jazyk (cs, sk, pl, hu, ro, gb, us)
      - keyword: vstupní klíčové slovo
      - suggestions_type: optional ("questions", "new", "trending")
      - with_keyword_data: optional (bool) – zda vracet i doplňující metriky u návrhů
    """
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}."
    if suggestions_type and suggestions_type not in SUGGESTIONS_TYPES:
        return f"Nepodporovaný typ návrhů: {suggestions_type}."

    url = f"{API_BASE}/keywords/suggestions"
    params: Dict[str, Any] = {"lang": lang, "keyword": keyword}
    if suggestions_type:
        params["suggestions_type"] = suggestions_type
    if with_keyword_data is not None:
        params["with_keyword_data"] = str(with_keyword_data).lower()

    response_data = await make_mm_request(url, params)

    if response_data.get("status") == "error":
        return response_data.get("message", "Nastala neznámá chyba")

    if response_data.get("status") == "success":
        # API obvykle vrací data pod data.keywords (seznam)
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
    """
    Získá data o hledanosti klíčového slova z Marketing Miner API.

    Parametry:
      - lang: jazyk (cs, sk, pl, hu, ro, gb, us)
      - keyword: klíčové slovo
    """
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

        kd = data[0] if isinstance(data, list) and data else {}
        result = [
            f"Klíčové slovo: {kd.get('keyword', 'N/A')}",
            f"Hledanost: {kd.get('search_volume', 'N/A')}",
        ]
        if isinstance(kd, dict) and "cpc" in kd and kd.get("cpc"):
            cpc = kd.get("cpc", {}) or {}
            result.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
        return "\n".join(result)

    return "Neočekávaný formát odpovědi z API"


@mcp.tool()
async def debug_status() -> str:
    """
    Bezpečná diagnostika: vrátí info o délce tokenu a základní parametry,
    aniž by vyzradila hodnoty tajných údajů.
    """
    host = os.getenv("HOST", "0.0.0.0")
    port = os.getenv("PORT", "8000")
    path = os.getenv("MCP_HTTP_PATH", "/mcp")
    masked = f"{len(API_TOKEN)} chars" if API_TOKEN else "EMPTY"
    return f"DEBUG | host={host} port={port} path={path} | token={masked}"


# Opravená spouštěcí sekce s vícero transporty
if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")

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
