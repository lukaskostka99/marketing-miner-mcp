from typing import Any, Dict, Optional
import os
import argparse
import json
import sys
import traceback
import httpx
from fastmcp import FastMCP

# =========================
#  Marketing Miner MCP (2025)
#  - Streamable HTTP first (Smithery)
#  - Token z ENV / --api-token / session JSON
# =========================

mcp = FastMCP("marketing-miner")

API_BASE = "https://profilers-api.marketingminer.com"
SUGGESTIONS_TYPES = ["questions", "new", "trending"]
LANGUAGES = ["cs", "sk", "pl", "hu", "ro", "gb", "us"]

# Možné názvy proměnných pro token (pro jistotu)
POSSIBLE_ENV_KEYS = [
    "MARKETING_MINER_API_TOKEN",
    "MARKETING_MINER_API_KEY",
    "MARKETING_MINER_TOKEN",
    "MM_API_TOKEN",
    "MM_API_KEY",
    "API_TOKEN",
    "API_KEY",
]


def _find_token_in_obj(obj) -> str:
    """Rekurzivně najde první hodnotu ve slovníku/listu, jejíž klíč obsahuje 'token' nebo 'key' a je neprázdná."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and v and (("token" in k.lower()) or ("key" in k.lower())):
                return v
            sub = _find_token_in_obj(v)
            if sub:
                return sub
    elif isinstance(obj, list):
        for item in obj:
            sub = _find_token_in_obj(item)
            if sub:
                return sub
    return ""


def resolve_token() -> str:
    """
    Získá API token prioritně z ENV, poté z CLI (--api-token),
    a nakonec z případného session JSONu v ENV (pokud hostitel takto config přibaluje).
    """
    # 1) ENV (více názvů)
    for key in POSSIBLE_ENV_KEYS:
        val = os.getenv(key, "")
        if val:
            return val

    # 2) CLI fallback
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-token", default="")
    # toleruj neznámé argumenty (FastMCP/hostitel je může přidat)
    args, _ = parser.parse_known_args()
    if args.api_token:
        return args.api_token

    # 3) Session JSON v ENV (některé platformy takto posílají config)
    for suspect in ("SMITHERY_SESSION_CONFIG", "SMITHERY_CONFIG", "MCP_SESSION_CONFIG"):
        raw = os.getenv(suspect, "")
        if not raw:
            continue
        try:
            cfg = json.loads(raw)
            tok = _find_token_in_obj(cfg)
            if tok:
                return tok
        except Exception:
            pass

    return ""


API_TOKEN = resolve_token()


async def make_mm_request(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Volání Marketing Miner Profilers API s ošetřením chyb.
    """
    if not API_TOKEN:
        return {
            "status": "error",
            "message": "Chyba: API token pro Marketing Miner není nastaven. Prosím, nastavte ho v konfiguraci.",
        }

    async with httpx.AsyncClient() as client:
        try:
            _params = dict(params or {})
            _params["api_token"] = API_TOKEN
            resp = await client.get(url, params=_params, timeout=30.0)
            resp.raise_for_status()
            return resp.json()
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
    lang: cs/sk/pl/hu/ro/gb/us
    suggestions_type: questions/new/trending (volitelné)
    with_keyword_data: bool (volitelné)
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
    """
    Získá data o hledanosti klíčového slova z Marketing Miner API.
    lang: cs/sk/pl/hu/ro/gb/us
    """
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


if __name__ == "__main__":
    # Smithery (remote) vyžaduje streamable HTTP; stdio bývá vypnuto
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    path = os.getenv("MCP_HTTP_PATH", "/mcp")

    # Bezpečná diagnostika do logu: ukážeme jen délku tokenu
    masked = f"{len(API_TOKEN)} chars" if API_TOKEN else "EMPTY"
    print(f"[MCP] Boot path={path} host={host} port={port} | token={masked}", flush=True)

    # Preferuj HTTP na hostingu, další transporty jako fallbacky (lokální běh apod.)
    for transport in ("http", "ssehttp", "shttp", "sse", "stdio"):
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
