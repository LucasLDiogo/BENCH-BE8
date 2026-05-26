"""
Coletor FRED + EIA — séries macro globais.
- FRED St. Louis Fed: https://api.stlouisfed.org/fred (chave gratuita em fred.stlouisfed.org/docs/api/api_key.html)
- EIA Energy Info: https://api.eia.gov (chave gratuita em www.eia.gov/opendata/register.php)

Configurar chaves via variável de ambiente:
  FRED_API_KEY=xxxxxx
  EIA_API_KEY=xxxxxx
Sem chave, o script registra status PARCIAL e mantém o painel funcional.

Séries FRED relevantes:
  - DCOILBRENTEU  Brent (USD/bbl)
  - DCOILWTICO    WTI (USD/bbl)
  - DHHNGSP       Henry Hub gas (USD/MMBtu)
  - PSOILUSDM     Soybean oil price (Mundo)
  - DEXBZUS       USD/BRL (referência)
Séries EIA relevantes:
  - PET.WCRSTUS1.W   Estoques crude EUA (mil bbl)
  - PET.WDISTUS1.W   Estoques diesel/destilado EUA (mil bbl)
"""
from __future__ import annotations
import os, datetime as dt
from utils import (http_get_json, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, log, now_iso)

FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"
EIA_BASE  = "https://api.eia.gov/v2/seriesid"

FRED_SERIES = [
    {"id": "DCOILBRENTEU", "nome": "Brent (FRED)",       "unidade": "US$/bbl"},
    {"id": "DCOILWTICO",   "nome": "WTI (FRED)",         "unidade": "US$/bbl"},
    {"id": "DHHNGSP",      "nome": "Henry Hub Gas",      "unidade": "US$/MMBtu"},
    {"id": "PSOILUSDM",    "nome": "Soybean oil (mundo)","unidade": "US$/ton"},
]
EIA_SERIES = [
    {"id": "PET.WCRSTUS1.W", "nome": "Estoques crude EUA",   "unidade": "mil bbl"},
    {"id": "PET.WDISTUS1.W", "nome": "Estoques diesel EUA",  "unidade": "mil bbl"},
]

def fred_fetch(series_id: str, key: str, dias: int = 365) -> list[dict]:
    end = dt.date.today()
    start = end - dt.timedelta(days=dias)
    url = (f"{FRED_BASE}?series_id={series_id}&api_key={key}"
           f"&file_type=json&observation_start={start}&observation_end={end}")
    j = http_get_json(url, timeout=30)
    obs = j.get("observations", [])
    out = []
    for o in obs:
        try:
            v = float(o["value"]) if o["value"] not in (".", "") else None
            if v is not None:
                out.append({"data": o["date"], "valor": v})
        except Exception:
            continue
    return out

def eia_fetch(series_id: str, key: str) -> list[dict]:
    url = f"{EIA_BASE}/{series_id}?api_key={key}"
    j = http_get_json(url, timeout=30)
    data = (j.get("response") or {}).get("data") or []
    out = []
    for d in data:
        try:
            v = float(d.get("value")) if d.get("value") is not None else None
            per = d.get("period")
            if v is not None and per:
                out.append({"data": per, "valor": v})
        except Exception:
            continue
    out.sort(key=lambda x: x["data"])
    return out

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "FRED (St. Louis Fed) + EIA (Energy Info)",
        "endpoint_fred": FRED_BASE,
        "endpoint_eia":  EIA_BASE,
        "status": "OK",
        "fred": [],
        "eia": [],
    }
    fred_key = os.environ.get("FRED_API_KEY", "").strip()
    eia_key  = os.environ.get("EIA_API_KEY", "").strip()

    if not fred_key:
        log.warning("FRED_API_KEY ausente · pulando FRED")
    if not eia_key:
        log.warning("EIA_API_KEY ausente · pulando EIA")

    falhas = 0
    sucessos = 0

    # FRED
    if fred_key:
        for s in FRED_SERIES:
            try:
                serie = fred_fetch(s["id"], fred_key)
                if serie:
                    last = serie[-1]
                    out["fred"].append({**s, "ultimo": last["valor"], "data": last["data"],
                                        "serie": serie[-90:], "status": "OK"})
                    sucessos += 1
                else:
                    out["fred"].append({**s, "status": "vazio"})
                    falhas += 1
            except Exception as e:
                log.warning(f"FRED {s['id']}: {e}")
                out["fred"].append({**s, "status": "ERRO", "erro": str(e)[:200]})
                falhas += 1

    # EIA
    if eia_key:
        for s in EIA_SERIES:
            try:
                serie = eia_fetch(s["id"], eia_key)
                if serie:
                    last = serie[-1]
                    out["eia"].append({**s, "ultimo": last["valor"], "data": last["data"],
                                       "serie": serie[-52:], "status": "OK"})
                    sucessos += 1
                else:
                    out["eia"].append({**s, "status": "vazio"})
                    falhas += 1
            except Exception as e:
                log.warning(f"EIA {s['id']}: {e}")
                out["eia"].append({**s, "status": "ERRO", "erro": str(e)[:200]})
                falhas += 1

    if not fred_key and not eia_key:
        out["status"] = "PARCIAL"
        out["modo"] = "chaves_ausentes"
        out["nota"] = (
            "Chaves FRED_API_KEY e EIA_API_KEY não configuradas (opcionais e gratuitas). "
            "1) FRED: criar em https://fred.stlouisfed.org/docs/api/api_key.html (2 min) "
            "2) EIA: criar em https://www.eia.gov/opendata/register.php (1 min) "
            "3) Adicionar como secrets no GitHub Actions ou no arquivo .env local."
        )
        out["fred"] = [{**s, "status": "AGUARDANDO_CHAVE"} for s in FRED_SERIES]
        out["eia"]  = [{**s, "status": "AGUARDANDO_CHAVE"} for s in EIA_SERIES]
        save_json(DATA_DIR / "fred_eia.json", out)
        mark_source_partial("fred_eia", "Aguardando configuração de chaves (opcional)",
                            rows=0, endpoint="fred.stlouisfed.org + api.eia.gov")
        return

    if sucessos == 0:
        out["status"] = "ERRO"
        mark_source_error("fred_eia", "Todas as séries falharam", endpoint=FRED_BASE)
    elif falhas:
        out["status"] = "PARCIAL"
        mark_source_partial("fred_eia", note=f"{falhas} falhas · {sucessos} OK",
                            rows=sucessos, endpoint=FRED_BASE)
    else:
        mark_source_ok("fred_eia", rows=sucessos, note=f"{sucessos} séries OK",
                       endpoint=FRED_BASE)
    save_json(DATA_DIR / "fred_eia.json", out)

if __name__ == "__main__":
    run()
