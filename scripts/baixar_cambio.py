"""
Coletor BCB PTAX — câmbio oficial Brasil.
Fonte: olinda.bcb.gov.br/PTAX (API REST OData, gratuita, sem chave).
Produz: data/cambio.json
"""
from __future__ import annotations
import datetime as dt
from utils import (http_get_json, save_json, mark_source_ok, mark_source_error,
                   DATA_DIR, log, now_iso, pct)

BASE = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"

def _fmt(d: dt.date) -> str:
    return f"{d.month:02d}-{d.day:02d}-{d.year}"

def fetch_last_quotation(moeda: str) -> dict | None:
    """Busca a cotação mais recente disponível (varre até 14 dias úteis para trás)."""
    today = dt.date.today()
    for i in range(15):
        d = today - dt.timedelta(days=i)
        if moeda == "USD":
            url = f"{BASE}/CotacaoDolarDia(dataCotacao=@dataCotacao)?@dataCotacao='{_fmt(d)}'&$format=json"
        else:
            url = f"{BASE}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)?@moeda='{moeda}'&@dataCotacao='{_fmt(d)}'&$format=json"
        try:
            j = http_get_json(url, timeout=15, retries=2)
            if j.get("value"):
                last = j["value"][-1]
                return {
                    "data_cotacao": last.get("dataHoraCotacao"),
                    "compra": last.get("cotacaoCompra"),
                    "venda": last.get("cotacaoVenda"),
                    "tipo_boletim": last.get("tipoBoletim", "Fechamento"),
                }
        except Exception as e:
            log.debug(f"BCB {moeda} {_fmt(d)}: {e}")
            continue
    return None

def fetch_period(moeda: str, dias: int = 90) -> list[dict]:
    end = dt.date.today()
    start = end - dt.timedelta(days=dias)
    if moeda == "USD":
        url = (f"{BASE}/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
               f"?@dataInicial='{_fmt(start)}'&@dataFinalCotacao='{_fmt(end)}'&$format=json")
    else:
        url = (f"{BASE}/CotacaoMoedaPeriodo(moeda=@moeda,dataInicial=@dataInicial,dataFinalCotacao=@dataFinalCotacao)"
               f"?@moeda='{moeda}'&@dataInicial='{_fmt(start)}'&@dataFinalCotacao='{_fmt(end)}'&$format=json")
    j = http_get_json(url, timeout=30)
    series = []
    for row in j.get("value", []):
        tipo = (row.get("tipoBoletim") or "").strip()
        if "Fechamento" in tipo or tipo == "":
            data = (row.get("dataHoraCotacao") or "")[:10]
            venda = row.get("cotacaoVenda")
            if data and venda is not None:
                series.append({"data": data, "valor": float(venda)})
    # Dedupe por data (mantém último)
    seen = {}
    for p in series:
        seen[p["data"]] = p
    return sorted(seen.values(), key=lambda x: x["data"])

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "Banco Central do Brasil · PTAX",
        "endpoint": BASE,
        "status": "OK",
        "moedas": {},
    }
    try:
        for moeda, label in [("USD", "Dólar Americano"), ("EUR", "Euro")]:
            try:
                last = fetch_last_quotation(moeda)
                serie = fetch_period(moeda, dias=90)
                prev = serie[-2]["valor"] if len(serie) >= 2 else None
                cur = serie[-1]["valor"] if serie else (last["venda"] if last else None)
                out["moedas"][moeda] = {
                    "codigo": moeda,
                    "nome": label,
                    "cotacao_atual": cur,
                    "cotacao_anterior": prev,
                    "variacao_pct": pct(cur, prev) if (cur and prev) else None,
                    "data_referencia": last["data_cotacao"] if last else None,
                    "serie_90d": serie,
                }
                log.info(f"BCB {moeda}: {cur} (Δ={out['moedas'][moeda]['variacao_pct']}) · {len(serie)} pontos")
            except Exception as e:
                log.error(f"Falha BCB {moeda}: {e}")
                out["moedas"][moeda] = {
                    "codigo": moeda, "nome": label,
                    "cotacao_atual": None, "serie_90d": [], "erro": str(e)[:200],
                }
        save_json(DATA_DIR / "cambio.json", out)
        total_pontos = sum(len(m.get("serie_90d", [])) for m in out["moedas"].values())
        mark_source_ok("bcb_ptax", rows=total_pontos,
                       note=f"USD + EUR · {total_pontos} fechamentos", endpoint=BASE)
    except Exception as e:
        log.exception(f"Erro fatal BCB: {e}")
        mark_source_error("bcb_ptax", str(e), endpoint=BASE)
        raise

if __name__ == "__main__":
    run()
