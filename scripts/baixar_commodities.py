"""
Coletor de Commodities — Yahoo Finance (server-side).
Como roda em Python (não browser), NÃO há problema de CORS.
Produz: data/commodities.json
"""
from __future__ import annotations
import datetime as dt
from utils import (http_get_json, save_json, mark_source_ok, mark_source_error,
                   DATA_DIR, log, now_iso, pct)

# Símbolos Yahoo Finance — todos futuros do CME/NYMEX/ICE
SYMBOLS = [
    {"id": "brent",    "sym": "BZ=F", "nome": "Petróleo Brent",   "mercado": "ICE",   "unidade": "US$/bbl"},
    {"id": "wti",      "sym": "CL=F", "nome": "WTI Crude",        "mercado": "NYMEX", "unidade": "US$/bbl"},
    {"id": "soja",     "sym": "ZS=F", "nome": "Soja",             "mercado": "CBOT",  "unidade": "¢/bu"},
    {"id": "milho",    "sym": "ZC=F", "nome": "Milho",            "mercado": "CBOT",  "unidade": "¢/bu"},
    {"id": "trigo",    "sym": "ZW=F", "nome": "Trigo",            "mercado": "CBOT",  "unidade": "¢/bu"},
    {"id": "oleo_soja","sym": "ZL=F", "nome": "Óleo de Soja",     "mercado": "CBOT",  "unidade": "¢/lb"},
    {"id": "farelo",   "sym": "ZM=F", "nome": "Farelo de Soja",   "mercado": "CBOT",  "unidade": "US$/ton"},
    {"id": "gas",      "sym": "NG=F", "nome": "Gás Natural",      "mercado": "NYMEX", "unidade": "US$/MMBtu"},
]

YAHOO_BASE = "https://query1.finance.yahoo.com/v8/finance/chart"

def fetch_yahoo(symbol: str, range_: str = "90d", interval: str = "1d") -> list[dict]:
    url = f"{YAHOO_BASE}/{symbol}?range={range_}&interval={interval}"
    j = http_get_json(url, timeout=30, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    })
    result = (j.get("chart", {}).get("result") or [None])[0]
    if not result:
        return []
    ts = result.get("timestamp") or []
    closes = (result.get("indicators", {}).get("quote", [{}])[0]).get("close") or []
    out = []
    for t, c in zip(ts, closes):
        if c is None: continue
        d = dt.datetime.utcfromtimestamp(t).date().isoformat()
        out.append({"data": d, "valor": float(c)})
    # Dedupe último por dia
    seen = {p["data"]: p for p in out}
    return sorted(seen.values(), key=lambda x: x["data"])

def run() -> None:
    payload = {
        "ultima_atualizacao": now_iso(),
        "fonte": "Yahoo Finance (CME/CBOT/ICE/NYMEX)",
        "endpoint": YAHOO_BASE,
        "status": "OK",
        "commodities": [],
    }
    falhas = 0
    for c in SYMBOLS:
        try:
            serie = fetch_yahoo(c["sym"], range_="90d", interval="1d")
            if not serie:
                raise RuntimeError("série vazia")
            last = serie[-1]["valor"]
            prev = serie[-2]["valor"] if len(serie) >= 2 else None
            w = serie[-7]["valor"] if len(serie) >= 8 else None
            m = serie[-21]["valor"] if len(serie) >= 22 else None
            item = {
                **c,
                "ultimo": last,
                "anterior": prev,
                "var_d_pct": pct(last, prev),
                "var_7d_pct": pct(last, w) if w else None,
                "var_30d_pct": pct(last, m) if m else None,
                "data_referencia": serie[-1]["data"],
                "serie_90d": serie,
                "status": "OK",
            }
            payload["commodities"].append(item)
            log.info(f"Yahoo {c['id']}: {last:.2f} · {len(serie)} pontos")
        except Exception as e:
            log.error(f"Yahoo {c['id']} ({c['sym']}): {e}")
            payload["commodities"].append({**c, "status": "ERRO", "erro": str(e)[:200], "serie_90d": []})
            falhas += 1

    if falhas == len(SYMBOLS):
        payload["status"] = "ERRO"
        mark_source_error("commodities_yahoo", "Todas as séries falharam", endpoint=YAHOO_BASE)
    elif falhas > 0:
        payload["status"] = "PARCIAL"
        mark_source_ok("commodities_yahoo", rows=len(SYMBOLS)-falhas,
                       note=f"{falhas} falhas / {len(SYMBOLS)}", endpoint=YAHOO_BASE)
    else:
        mark_source_ok("commodities_yahoo", rows=len(SYMBOLS),
                       note="todas as commodities OK", endpoint=YAHOO_BASE)
    save_json(DATA_DIR / "commodities.json", payload)

if __name__ == "__main__":
    run()
