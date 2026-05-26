"""
BENCH-BE8 · agente_atualizacao.py
---------------------------------------------------------------------
Orquestrador principal. Roda TODOS os coletores em sequência,
captura erros individualmente (nenhum coletor derruba o restante),
e gera o manifesto governance.json no final.

Uso:
    python scripts/agente_atualizacao.py

Saída:
    /data/*.json (todos atualizados)
    /logs/agente_atualizacao.log
"""
from __future__ import annotations

import importlib
import sys
import time
from pathlib import Path

# Garante que scripts/ está no path para imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from utils import get_logger

log = get_logger("agente_atualizacao")

# Ordem de execução: rápidos primeiro, depois pesados
PIPELINE = [
    "baixar_cambio",
    "baixar_commodities",
    "baixar_anp_combustiveis",
    "baixar_anp_b100",
    "baixar_anp_vendas",
    "baixar_conab",
    "baixar_comex",
    "baixar_usda",
    "baixar_noticias",
    "gerar_be8_profile",
    "gerar_governance",   # SEMPRE último — consolida o estado
]


def run_module(mod_name: str) -> tuple[str, bool, float]:
    t0 = time.time()
    try:
        mod = importlib.import_module(mod_name)
        rc = mod.main()
        ok = (rc == 0)
        return mod_name, ok, time.time() - t0
    except Exception as e:
        log.exception("falha em %s: %s", mod_name, e)
        return mod_name, False, time.time() - t0


def main():
    log.info("=" * 60)
    log.info("BENCH-BE8 · agente de atualização · iniciando ciclo")
    log.info("=" * 60)

    resultados = []
    for mod_name in PIPELINE:
        log.info("→ %s", mod_name)
        nome, ok, dur = run_module(mod_name)
        resultados.append((nome, ok, dur))
        marker = "✓" if ok else "✗"
        log.info("%s %s · %.1fs", marker, nome, dur)

    log.info("=" * 60)
    ok_count = sum(1 for _, ok, _ in resultados if ok)
    total = len(resultados)
    log.info("ciclo encerrado · %d/%d OK", ok_count, total)
    log.info("=" * 60)
    return 0 if ok_count == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
