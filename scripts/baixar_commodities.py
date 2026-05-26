"""
BENCH-BE8 · baixar_commodities.py
---------------------------------------------------------------------
Coletor Yahoo Finance · commodities (futuros CME/NYMEX/ICE).
Substitui o pedido original do Investing.com (que tem anti-bot
Cloudflare) — mesmas commodities, fonte estável.

Tickers Yahoo:
  BZ=F  → Brent
  CL=F  → WTI
  ZS=F  → Soja CBOT
  ZC=F  → Milho CBOT
  ZW=F  → Trigo CBOT
  ZL=F  → Óleo de soja CBOT
  ZM=F  → Farelo de soja CBOT
  NG=F  → Gás natural
"""
from __future__ import annotations

from datetime import datetime

from utils import get_logger, http_get, save_json, pct_change

log = get_logger("baixar_commodities")

ATIVOS = {
    "brent":     {"ticker": "BZ=F", "nome": "Brent",         "mercado": "ICE",   "unidade": "USD/bbl"},
    "wti":       {"ticker": "CL=F", "nome": "WTI",           "mercado": "NYMEX", "unidade": "USD/bbl"},
    "soja":      {"ticker": "ZS=F", "nome": "Soja",          "mercado": "CBOT",  "unidade": "cent/bu"},
    "milho":     {"ticker": "ZC=F", "nome": "Milho",         "mercado": "CBOT",  "unidade": "cent/bu"},
    "trigo":     {"ticker": "ZW=F", "nome": "Trigo",         "mercado": "CBOT",  "unidade": "cent/bu"},
    "oleo_soja": {"ticker": "ZL=F", "nome": "Óleo de Soja",  "mercado": "CBOT",  "unidade": "cent/lb"},
    "farelo":    {"ticker": "ZM=F", "nome": "Farelo de Soja","mercado": "CBOT",  "unidade": "USD/ton"},
    "gas":       {"ticker": "NG=F", "nome": "Gás Natural",   "mercado": "NYMEX", "unidade": "USD/MMBtu"},
}

YAHOO = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"


def baixar_ticker(ticker: str) -> dict | None:
    """Busca série de 90 dias do Yahoo. Retorna None se falhar."""
    params = {"range": "3mo", "interval": "1d", "includePrePost": "false"}
    r = http_get(YAHOO.format(ticker=ticker), params=params, timeout=20)
    if not r:
        return None
    try:
        data = r.json()
        chart = data.get("chart", {}).get("result", [])
        if not chart:
            return None
        c = chart[0]
        ts = c["timestamp"]
        closes = c["indicators"]["quote"][0]["close"]
        # Filtrar None
        serie = [
            {
                "data":  datetime.fromtimestamp(t).strftime("%Y-%m-%d"),
                "valor": float(v),
            }
            for t, v in zip(ts, closes) if v is not None
        ]
        return serie
    except (KeyError, IndexError, ValueError, TypeError) as e:
        log.warning("%s · parsing falhou: %s", ticker, e)
        return None


def main():
    log.info("iniciando · Yahoo Finance · %d ativos", len(ATIVOS))
    out = {}
    erros = []
    for slug, meta in ATIVOS.items():
        serie = baixar_ticker(meta["ticker"])
        if not serie or len(serie) < 2:
            log.warning("%s (%s) · sem dados", slug, meta["ticker"])
            out[slug] = {**meta}
            erros.append(slug)
            continue
        cotacao   = serie[-1]["valor"]
        anterior  = serie[-2]["valor"]
        # var 7d e 30d
        idx_7    = max(0, len(serie) - 8)
        idx_30   = max(0, len(serie) - 31)
        var_7    = pct_change(cotacao, serie[idx_7]["valor"])  if len(serie) > 7  else None
        var_30   = pct_change(cotacao, serie[idx_30]["valor"]) if len(serie) > 30 else None
        out[slug] = {
            **meta,
            "cotacao":           cotacao,
            "cotacao_anterior":  anterior,
            "variacao_pct":      pct_change(cotacao, anterior),
            "variacao_7d":       var_7,
            "variacao_30d":      var_30,
            "data_ref":          serie[-1]["data"],
            "serie_90d":         serie[-90:],
        }
        log.info("✓ %s = %.2f (%+.2f%%)", slug, cotacao, out[slug]["variacao_pct"] or 0)

    if len(erros) == len(ATIVOS):
        save_json("commodities.json", "Yahoo Finance", "erro",
                  dados=out, erro=f"Todos os {len(erros)} ativos falharam")
        return 1
    status = "ok" if not erros else "fallback"
    save_json("commodities.json", "Yahoo Finance", status, dados=out,
              erro=f"falha em: {erros}" if erros else None)
    log.info("ok · %d/%d ativos", len(ATIVOS) - len(erros), len(ATIVOS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
