from typing import Any, Dict, Optional
import os
import argparse
import sys
import traceback
import httpx
from fastmcp import FastMCP

# =========================
#  Marketing Miner MCP (2025)
#  - STDIO first
#  - Token z ENV i z CLI (--api-token)
#  - Bezpečná diagnostika (loguje jen délku tokenu)
# =========================

mcp = FastMCP("marketing-miner")

API_BASE = "https://profilers-api.marketingminer.com"
SUGGESTIONS_TYPES = ["questions", "new", "trending"]
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]


def resolve_token() -> str:
    """Vrátí API token z ENV nebo z CLI (--api-token)."""
    env_token = os.getenv("MARKETING_MINER_API_TOKEN", "")
    if env_token:
        return env_token
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-token", default="")
    parser.add_argument("--stdio", action="store_true")  # jen flag, nic víc
    args, _ = parser.parse_known_args()
    return args.api_token or ""


API_TOKEN = resolve_token()


async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Volání Marketing Miner Profilers API s ošetřením chyb."""
    if not API_TOKEN:
        return {
            "status": "error",
            "message": "Chyba: API token pro Marketing Miner není nastaven. Prosím, nastavte ho v konfiguraci.",
        }
    async with httpx.AsyncClient() as client:
        try:
            params = dict(params or {})
            params["api_token"] = API_TOKEN
            r = await client.get(url, params=params, timeout=30.0)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            return {"status": "error", "message": f"Chyba při volání Marketing Miner API: {str(e)}"}


@mcp.tool()
async def get_keyword_suggestions(
    lang: str,
    keyword: str,
    suggestions_type: Optional[str] = None,
    with_keyword_data: Optional[bool] = False,
) -> str:
    """Získá návrhy klíčových slov z Marketing Miner API."""
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

    data = await make_mm_request(url, params)
    if data.get("status") == "error":
        return data.get("message", "Nastala neznámá chyba")

    if data.get("status") == "success":
        kws = data.get("data", {}).get("keywords", [])
        if not kws:
            return "Nebyla nalezena žádná data pro tento dotaz."
        rows = []
        for kd in kws:
            if not isinstance(kd, dict):
                continue
            info = [f"Klíčové slovo: {kd.get('keyword', 'N/A')}"]
            if "search_volume" in kd:
                info.append(f"Hledanost: {kd.get('search_volume', 'N/A')}")
            rows.append(" | ".join(info))
        return "\n".join(rows)

    return "Neočekávaný formát odpovědi z API"


@mcp.tool()
async def get_search_volume_data(lang: str, keyword: str) -> str:
    """Získá data o hledanosti klíčového slova z Marketing Miner API."""
    if lang not in LANGUAGES:
        return f"Nepodporovaný jazyk: {lang}."
    url = f"{API_BASE}/keywords/search-volume-data"
    params = {"lang": lang, "keyword": keyword}
    data = await make_mm_request(url, params)
    if data.get("status") == "error":
        return data.get("message", "Nastala neznámá chyba")

    if data.get("status") == "success":
        arr = data.get("data", [])
        if not arr:
            return "Nebyla nalezena žádná data pro toto klíčové slovo."
        kd = arr[0] if isinstance(arr, list) else {}
        out = [
            f"Klíčové slovo: {kd.get('keyword', 'N/A')}",
            f"Hledanost: {kd.get('search_volume', 'N/A')}",
        ]
        if isinstance(kd, dict) and kd.get("cpc"):
            cpc = kd.get("cpc", {}) or {}
            out.append(f"CPC: {cpc.get('value', 'N/A')} {cpc.get('currency_code', '')}")
        return "\n".join(out)

    return "Neočekávaný formát odpovědi z API"


@mcp.tool()
async def debug_status() -> str:
    """Bezpečná diagnostika – vrátí délku tokenu + základní parametry (bez vyzrazení tajemství)."""
    host = os.getenv("HOST", "N/A")
    port = os.getenv("PORT", "N/A")
    path = os.getenv("MCP_HTTP_PATH", "N/A")
    masked = f"{len(API_TOKEN)} chars" if API_TOKEN else "EMPTY"
    return f"DEBUG | host={host} port={port} path={path} | token={masked}"


if __name__ == "__main__":
    # Preferuj STDIO, HTTP až když STDIO selže (nebo když běžíš lokálně bez Smithery)
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")

    masked = f"{len(API_TOKEN)} chars" if API_TOKEN else "EMPTY"
    print(f"[MCP] Boot path={path} host={host} port={port} | token={masked}", flush=True)

    for transport in ("stdio", "http", "ssehttp", "shttp", "sse"):
        try:
            print(f"[MCP] Trying transport={transport}", flush=True)
            if "http" in transport:
                # FastMCP HTTP endpoint je na /mcp (MCP specifikace počítá s jediným endpointem)
                mcp.run(transport=transport, host=host, port=port, path=path)
            else:
                mcp.run(transport=transport)
            sys.exit(0)
        except Exception as e:
            print(f"[MCP] Transport {transport} failed: {e!r}", flush=True)
            traceback.print_exc()

    print("[MCP] ERROR: no working transport found", flush=True)
    sys.exit(1)
