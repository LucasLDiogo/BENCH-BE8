"""
BENCH-BE8 · baixar_conab.py
---------------------------------------------------------------------
CONAB · Safra de grãos (soja, milho, trigo).

URL primária:
  portaldeinformacoes.conab.gov.br/safra-serie-historica-graos.html

Estrutura: este coletor é um STUB defensivo. Se a página renderiza
client-side (caso real), o agente marca status='pendente' sem inventar
dados. O conteúdo final é preenchido por scraper específico ou por
download manual do CSV oficial colocado em data/conab_graos_raw.csv.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from utils import get_logger, http_get, save_json, DATA_DIR, pct_change

log = get_logger("baixar_conab")

CSV_LOCAL = DATA_DIR / "conab_graos_raw.csv"
CSV_REMOTO = "https://www.conab.gov.br/info-agro/safras/serie-historica-das-safras"


def processar_csv(text: str) -> dict | None:
    """Espera CSV com colunas: produto;safra;uf;area_mil_ha;producao_mil_t."""
    rows = list(csv.DictReader(io.StringIO(text), delimiter=";"))
    if not rows:
        return None
    safras = {"soja": None, "milho": None, "trigo": None}
    ufs = {"soja": [], "milho": [], "trigo": []}

    # Pegar última safra disponível por produto
    for prod in ["soja", "milho", "trigo"]:
        relevantes = [r for r in rows if r.get("produto", "").lower() == prod and r.get("uf", "").upper() == "BR"]
        if not relevantes:
            continue
        ultima = sorted(relevantes, key=lambda r: r["safra"])[-1]
        try:
            prod_mt = float(ultima.get("producao_mil_t", 0)) / 1000.0
            anterior_safra = sorted(relevantes, key=lambda r: r["safra"])[-2] if len(relevantes) > 1 else None
            prod_ant = float(anterior_safra.get("producao_mil_t", 0)) / 1000.0 if anterior_safra else None
            safras[prod] = {
                "producao_mt": prod_mt,
                "safra": ultima["safra"],
                "variacao_pct_ano_anterior": pct_change(prod_mt, prod_ant),
            }
        except (ValueError, KeyError):
            continue

        # Rankings por UF da safra mais recente
        ufs_data = [r for r in rows if r.get("produto", "").lower() == prod
                    and r.get("safra") == ultima["safra"]
                    and r.get("uf", "").upper() != "BR"]
        ranking = []
        total_br = safras[prod]["producao_mt"] if safras[prod] else 0
        for r in ufs_data:
            try:
                p_mt = float(r["producao_mil_t"]) / 1000.0
                ranking.append({
                    "uf": r["uf"],
                    "producao_mt": p_mt,
                    "share_pct": (p_mt / total_br * 100) if total_br else 0,
                })
            except (ValueError, KeyError):
                continue
        ranking.sort(key=lambda x: x["producao_mt"], reverse=True)
        ufs[prod] = ranking

    return {"safras": safras, "ufs": ufs,
            "safra_ref": safras["soja"]["safra"] if safras["soja"] else "—"}


def main():
    log.info("iniciando · CONAB")
    # Caminho 1: CSV local pré-baixado manualmente
    if CSV_LOCAL.exists():
        text = CSV_LOCAL.read_text(encoding="utf-8", errors="ignore")
        log.info("usando CSV local: %s", CSV_LOCAL.name)
        dados = processar_csv(text)
        if dados:
            save_json("conab_graos.json", "CONAB (CSV local)", "ok", dados=dados)
            return 0

    # Caminho 2: tentar URL remota oficial
    r = http_get(CSV_REMOTO, timeout=45)
    if not r:
        save_json("conab_graos.json", "CONAB", "indisponivel",
                  erro="Página CONAB indisponível e CSV local ausente. "
                       f"Baixe manualmente o CSV em {CSV_REMOTO} e salve como "
                       f"{CSV_LOCAL.name} dentro de /data.")
        log.warning("CONAB indisponível — coloque CSV em /data/conab_graos_raw.csv")
        return 0  # não é erro fatal, é fonte intermitente

    # Página remota é HTML (não CSV) → marcar pendente
    save_json("conab_graos.json", "CONAB", "pendente",
              erro="Página CONAB requer download manual do CSV. "
                   "Salve como /data/conab_graos_raw.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
