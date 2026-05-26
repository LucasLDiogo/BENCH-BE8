"""
BENCH-BE8 · baixar_cambio.py
---------------------------------------------------------------------
Coletor BCB PTAX (Banco Central) — USD/BRL e EUR/BRL.
API oficial, sem chave, sem CORS.

Endpoint:
  olinda.bcb.gov.br/olinda/servico/PTAX/v1/odata/CotacaoMoedaPeriodo
"""
from __future__ import annotations

from datetime import date, timedelta

from utils import get_logger, http_get, save_json, pct_change

log = get_logger("baixar_cambio")

BASE = (
    "https://olinda.bcb.gov.br/olinda/servico/PTAX/v1/odata/"
    "CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,"
    "dataFinalCotacao=@dataFinalCotacao)"
)


def baixar_moeda(moeda: str, dias: int = 95) -> dict | None:
    fim    = date.today()
    inicio = fim - timedelta(days=dias)
    params = {
        "@moeda":            f"'{moeda}'",
        "@dataInicial":      f"'{inicio.strftime('%m-%d-%Y')}'",
        "@dataFinalCotacao": f"'{fim.strftime('%m-%d-%Y')}'",
        "$format":           "json",
        "$select":           "cotacaoVenda,dataHoraCotacao",
    }
    r = http_get(BASE, params=params, timeout=30)
    if not r:
        log.warning("%s · falha HTTP", moeda)
        return None
    try:
        rows = r.json().get("value", [])
    except Exception as e:
        log.warning("%s · falha JSON: %s", moeda, e)
        return None
    if not rows:
        return None

    # série temporal
    serie = [
        {"data": row["dataHoraCotacao"][:10], "valor": float(row["cotacaoVenda"])}
        for row in rows if row.get("cotacaoVenda")
    ]
    # ordena cronologicamente, dedup por data
    seen = {}
    for it in serie:
        seen[it["data"]] = it["valor"]
    serie_clean = [{"data": d, "valor": v} for d, v in sorted(seen.items())]

    if len(serie_clean) < 2:
        return None

    cotacao  = serie_clean[-1]["valor"]
    anterior = serie_clean[-2]["valor"]

    return {
        "cotacao":           cotacao,
        "cotacao_anterior":  anterior,
        "variacao_pct":      pct_change(cotacao, anterior),
        "data_ref":          serie_clean[-1]["data"],
        "serie_90d":         serie_clean[-90:],
    }


def main():
    log.info("iniciando · BCB PTAX")
    try:
        usd = baixar_moeda("USD")
        eur = baixar_moeda("EUR")
        if not usd and not eur:
            save_json("cambio.json", "BCB PTAX", "erro",
                      erro="Ambas as moedas falharam")
            log.error("USD e EUR falharam")
            return 1
        status = "ok" if (usd and eur) else "fallback"
        save_json("cambio.json", "BCB PTAX", status,
                  dados={"usd": usd, "eur": eur})
        log.info("ok · USD=%s · EUR=%s",
                 usd["cotacao"] if usd else "—",
                 eur["cotacao"] if eur else "—")
        return 0
    except Exception as e:
        log.exception("falha inesperada")
        save_json("cambio.json", "BCB PTAX", "erro", erro=str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
