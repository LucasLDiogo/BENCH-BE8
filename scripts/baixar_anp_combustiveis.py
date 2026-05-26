"""
BENCH-BE8 · baixar_anp_combustiveis.py
---------------------------------------------------------------------
ANP · preços de revenda combustíveis (SLP — Sistema de Levantamento de Preços).
Publicação semanal em CSV.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime

from utils import get_logger, http_get, save_json, pct_change, load_json

log = get_logger("baixar_anp_combustiveis")

# URL pode mudar entre semanas — o agente tenta a planilha consolidada
CANDIDATAS = [
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/precos-combustiveis-revenda.csv",
    "https://www.gov.br/anp/pt-br/assuntos/precos-e-defesa-da-concorrencia/precos/precos-revenda-e-de-distribuicao-combustiveis/serie-historica-de-precos-de-combustiveis/serie-historica-precos.csv",
]


def baixar_csv() -> str | None:
    for url in CANDIDATAS:
        r = http_get(url, timeout=45)
        if r:
            # ANP usa Latin-1
            try:
                return r.content.decode("latin-1")
            except UnicodeDecodeError:
                continue
    return None


def processar(csv_text: str) -> dict:
    """Agrega preço médio por produto + top/bottom municípios para Diesel S10."""
    reader = csv.DictReader(io.StringIO(csv_text), delimiter=";")
    por_produto = {
        "diesel_s10":   [],
        "diesel_s500":  [],
        "gasolina":     [],
        "etanol":       [],
    }
    s10_municipios = []
    for row in reader:
        produto = (row.get("Produto") or row.get("PRODUTO") or "").upper()
        try:
            preco = float((row.get("Valor de Venda") or row.get("VALOR DE VENDA") or "0").replace(",", "."))
        except ValueError:
            continue
        if "S-10" in produto or "S10" in produto:
            por_produto["diesel_s10"].append(preco)
            mun = row.get("Municipio") or row.get("MUNICIPIO") or ""
            uf  = row.get("Estado - Sigla") or row.get("ESTADO") or ""
            if mun:
                s10_municipios.append({"municipio": mun, "uf": uf, "preco": preco})
        elif "S-500" in produto or "DIESEL COMUM" in produto:
            por_produto["diesel_s500"].append(preco)
        elif "GASOLINA COMUM" in produto:
            por_produto["gasolina"].append(preco)
        elif "ETANOL" in produto:
            por_produto["etanol"].append(preco)

    out = {}
    for k, lst in por_produto.items():
        if lst:
            out[k] = {"preco_medio": sum(lst) / len(lst), "n_postos": len(lst)}
        else:
            out[k] = {"preco_medio": None, "n_postos": 0}

    # Top 10 baratos e top 10 caros do S10
    s10_municipios.sort(key=lambda x: x["preco"])
    out["s10_baratas"] = s10_municipios[:10]
    out["s10_caras"]   = s10_municipios[-10:][::-1]
    out["ref_semana"]  = datetime.now().strftime("%Y-%W")

    # Variação vs ciclo anterior (cache local)
    prev = load_json("anp_combustiveis.json")
    if prev and prev.get("dados"):
        for k in ["diesel_s10", "diesel_s500", "gasolina", "etanol"]:
            cur  = out[k].get("preco_medio")
            prev_v = prev["dados"].get(k, {}).get("preco_medio")
            out[k]["variacao_pct"] = pct_change(cur, prev_v)
    return out


def main():
    log.info("iniciando · ANP combustíveis")
    csv_text = baixar_csv()
    if not csv_text:
        save_json("anp_combustiveis.json", "ANP SLP", "erro",
                  erro="CSV indisponível em todas as URLs candidatas")
        log.error("nenhuma URL ANP respondeu")
        return 1
    try:
        dados = processar(csv_text)
        save_json("anp_combustiveis.json", "ANP SLP", "ok", dados=dados)
        log.info("ok · %d postos S10 · preço médio R$ %.3f",
                 dados["diesel_s10"]["n_postos"],
                 dados["diesel_s10"]["preco_medio"] or 0)
        return 0
    except Exception as e:
        log.exception("erro processando")
        save_json("anp_combustiveis.json", "ANP SLP", "erro", erro=str(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
