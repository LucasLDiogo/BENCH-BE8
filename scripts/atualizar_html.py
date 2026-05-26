"""
Atualizar HTML — Be8 Market Intelligence.

A arquitetura desta plataforma NÃO reescreve o HTML em cada atualização.
O HTML é STATIC e faz fetch() dos arquivos JSON em /data/ em runtime
(no browser do usuário). Esta abordagem:
  - Mantém o HTML versionado e reviewable
  - Garante que o usuário sempre vê o estado mais recente sem reload de página
  - Evita bugs de geração de HTML

Este script faz apenas:
  1) Valida que todos os JSONs esperados existem em data/
  2) Atualiza o build_stamp.json (lido pelo HTML para exibir "última atualização")
"""
from __future__ import annotations
import datetime as dt
from utils import save_json, load_json, DATA_DIR, log, now_iso

JSONS_ESPERADOS = [
    "cambio.json", "commodities.json",
    "anp_combustiveis.json", "anp_b100.json",
    "conab_graos.json", "ibge_sidra.json",
    "comex.json", "fred_eia.json",
    "noticias.json", "be8_profile.json",
    "status_fontes.json",
]

def run() -> None:
    presentes = []
    ausentes  = []
    for name in JSONS_ESPERADOS:
        p = DATA_DIR / name
        if p.exists():
            presentes.append(name)
        else:
            ausentes.append(name)
    stamp = {
        "build_timestamp": now_iso(),
        "build_date": dt.date.today().isoformat(),
        "jsons_presentes": presentes,
        "jsons_ausentes":  ausentes,
        "completude_pct":  round(len(presentes) / len(JSONS_ESPERADOS) * 100, 1),
    }
    save_json(DATA_DIR / "build_stamp.json", stamp)
    log.info(f"build_stamp atualizado · {len(presentes)}/{len(JSONS_ESPERADOS)} JSONs presentes")

if __name__ == "__main__":
    run()
