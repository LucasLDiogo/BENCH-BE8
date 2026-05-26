"""
BENCH-BE8 · baixar_comex.py
---------------------------------------------------------------------
ComexStat MDIC · exportação/importação por NCM.
API REST oficial, CORS aberto.

Endpoint: api-comexstat.mdic.gov.br
"""
from __future__ import annotations

from datetime import date

from utils import get_logger, http_get, save_json

log = get_logger("baixar_comex")

API = "https://api-comexstat.mdic.gov.br/general"

NCMS = {
    "soja":      "12019000",  # soja grão
    "farelo":    "23040090",  # farelo de soja
    "oleo":      "15071000",  # óleo de soja bruto
    "biodiesel": "38260000",  # biodiesel
    "diesel":    "27101921",  # diesel
    "metanol":   "29051100",  # metanol
}


def query_ncm(ncm: str, ano: int) -> dict | None:
    payload = {
        "filters":   [{"filter": "NCM", "values": [ncm]}],
        "monthDetail": False,
        "yearDetail":  False,
        "details":   ["country"],
        "flow":      "export",
        "period":    {"from": f"{ano}-01", "to": f"{ano}-12"},
        "metrics":   ["metricFOB", "metricKG"],
    }
    r = http_get(API, headers={"Content-Type": "application/json"}, timeout=30)
    if not r:
        return None
    try:
        d = r.json()
        # Fallback simples: somar tudo
        rows = d.get("data", {}).get("list", [])
        total_kg  = sum(float(x.get("metricKG", 0))  for x in rows)
        total_fob = sum(float(x.get("metricFOB", 0)) for x in rows)
        return {"volume_kg": total_kg, "volume_fob_usd": total_fob,
                "paises_top": rows[:5]}
    except (ValueError, KeyError):
        return None


def main():
    log.info("iniciando · ComexStat")
    ano = date.today().year
    out, erros = {}, []
    for slug, ncm in NCMS.items():
        d = query_ncm(ncm, ano)
        if d:
            out[slug] = d
            log.info("✓ %s · %.0f kg", slug, d.get("volume_kg", 0))
        else:
            erros.append(slug)
            log.warning("× %s falhou", slug)

    if len(erros) == len(NCMS):
        save_json("comex.json", "ComexStat MDIC", "erro",
                  erro=f"todos os {len(erros)} NCMs falharam")
        return 1
    out["ref_ano"] = ano
    status = "ok" if not erros else "fallback"
    save_json("comex.json", "ComexStat MDIC", status, dados=out,
              erro=f"falha em: {erros}" if erros else None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
