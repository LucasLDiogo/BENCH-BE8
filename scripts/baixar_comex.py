"""
Coletor ComexStat — API REST oficial MDIC.
Endpoint: https://api-comexstat.mdic.gov.br/general
NCMs monitorados para Be8:
  - 27101921  diesel
  - 38260000  biodiesel
  - 15071000  óleo soja bruto
  - 15079011  óleo soja refinado
  - 23040010  farelo soja
  - 29051100  metanol
  - 12010090  soja em grão
Período: ano corrente + ano anterior (YTD)
Saída: data/comex.json
"""
from __future__ import annotations
import datetime as dt
from utils import (http_post_json, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, log, now_iso)

API = "https://api-comexstat.mdic.gov.br/general"

NCMS = [
    {"ncm": "27101921", "descricao": "Óleo diesel",                 "fluxo": "import", "categoria": "combustivel"},
    {"ncm": "38260000", "descricao": "Biodiesel B100 e misturas",   "fluxo": "export", "categoria": "biodiesel"},
    {"ncm": "38260000", "descricao": "Biodiesel B100 e misturas",   "fluxo": "import", "categoria": "biodiesel"},
    {"ncm": "15071000", "descricao": "Óleo de soja bruto",          "fluxo": "export", "categoria": "oleo_soja"},
    {"ncm": "15079011", "descricao": "Óleo de soja refinado",       "fluxo": "export", "categoria": "oleo_soja"},
    {"ncm": "23040010", "descricao": "Farelo de soja",              "fluxo": "export", "categoria": "farelo"},
    {"ncm": "29051100", "descricao": "Metanol",                     "fluxo": "import", "categoria": "metanol"},
    {"ncm": "12010090", "descricao": "Soja em grão",                "fluxo": "export", "categoria": "soja_grao"},
]

def query_ytd(ncm: str, fluxo: str) -> dict | None:
    """Soma valores YTD do ano corrente + ano anterior para comparativo."""
    year = dt.date.today().year
    body = {
        "flow": fluxo,
        "monthDetail": True,
        "period": {"from": f"{year-1}-01", "to": f"{year}-12"},
        "filters": [{"filter": "ncm", "values": [ncm]}],
        "details": ["ncm"],
        "metrics": ["metricFOB", "metricKG"],
    }
    try:
        j = http_post_json(API, body, timeout=45)
        lst = (j.get("data") or {}).get("list") or []
        return {"lista": lst}
    except Exception as e:
        log.warning(f"ComexStat {fluxo} NCM {ncm}: {e}")
        return None

def aggregate(lista: list[dict]) -> dict:
    """Soma FOB e KG do ano corrente vs ano anterior."""
    year = dt.date.today().year
    fob_now = kg_now = fob_prev = kg_prev = 0.0
    for r in lista:
        # API retorna `year` e `monthNumber`
        ry = int(r.get("year", 0))
        fob = float(r.get("metricFOB", 0) or 0)
        kg  = float(r.get("metricKG", 0) or 0)
        if ry == year:
            fob_now += fob; kg_now += kg
        elif ry == year - 1:
            fob_prev += fob; kg_prev += kg
    # Preço médio implícito US$/ton
    preco_now = (fob_now / (kg_now / 1000)) if kg_now else None
    preco_prev = (fob_prev / (kg_prev / 1000)) if kg_prev else None
    return {
        "ano_corrente": {
            "fob_usd": round(fob_now, 2),
            "kg":      round(kg_now, 2),
            "toneladas": round(kg_now / 1000, 2),
            "preco_medio_usd_ton": round(preco_now, 2) if preco_now else None,
        },
        "ano_anterior": {
            "fob_usd": round(fob_prev, 2),
            "kg":      round(kg_prev, 2),
            "toneladas": round(kg_prev / 1000, 2),
            "preco_medio_usd_ton": round(preco_prev, 2) if preco_prev else None,
        },
        "var_fob_pct": (round((fob_now - fob_prev) / fob_prev * 100, 2)
                       if fob_prev else None),
        "var_volume_pct": (round((kg_now - kg_prev) / kg_prev * 100, 2)
                          if kg_prev else None),
    }

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "MDIC · ComexStat (API oficial)",
        "endpoint": API,
        "status": "OK",
        "ano_corrente": dt.date.today().year,
        "fluxos": [],
    }
    falhas = 0
    for cfg in NCMS:
        r = query_ytd(cfg["ncm"], cfg["fluxo"])
        if r and r.get("lista") is not None:
            agg = aggregate(r["lista"])
            out["fluxos"].append({**cfg, **agg, "linhas": len(r["lista"])})
            log.info(f"Comex {cfg['fluxo']} NCM {cfg['ncm']} · YTD FOB US$ {agg['ano_corrente']['fob_usd']:.0f}")
        else:
            out["fluxos"].append({**cfg, "erro": "sem retorno"})
            falhas += 1
    if falhas == len(NCMS):
        out["status"] = "ERRO"
        mark_source_error("comex", "Todas as queries falharam", endpoint=API)
    elif falhas:
        out["status"] = "PARCIAL"
        mark_source_partial("comex", note=f"{falhas} falhas / {len(NCMS)}",
                            rows=len(NCMS)-falhas, endpoint=API)
    else:
        mark_source_ok("comex", rows=len(NCMS),
                       note=f"{len(NCMS)} NCMs · YTD {out['ano_corrente']}", endpoint=API)
    save_json(DATA_DIR / "comex.json", out)

if __name__ == "__main__":
    run()
