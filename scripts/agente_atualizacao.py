"""
Agente principal Be8 Market Intelligence.
Orquestra a execução de todos os coletores com ISOLAMENTO DE FALHAS:
uma fonte falhando NÃO interrompe as demais.

Roda às 07:00 e 13:00 (configurar via Task Scheduler ou GitHub Actions).
"""
from __future__ import annotations
import sys, time, traceback, datetime as dt
from importlib import import_module
from utils import log, save_json, DATA_DIR, now_iso, load_json, STATUS_PATH

# Ordem de execução. Cada item: (módulo, nome_amigável)
COLETORES = [
    ("baixar_cambio",             "BCB · Câmbio PTAX"),
    ("baixar_commodities",        "Yahoo Finance · Commodities"),
    ("baixar_anp_combustiveis",   "ANP · Preços combustíveis"),
    ("baixar_anp_b100",           "ANP · Biodiesel B100"),
    ("baixar_anp_vendas",         "ANP · Vendas por UF/distribuidora"),
    ("baixar_conab",              "CONAB · Safras"),
    ("baixar_ibge_sidra",         "IBGE SIDRA · LSPA"),
    ("baixar_comex",              "ComexStat · Comércio exterior"),
    ("baixar_fred_eia",           "FRED + EIA · Macro/Energia"),
    ("baixar_usda",               "USDA WASDE · Benchmark global"),
    ("gerar_noticias",            "Notícias setoriais (RSS)"),
    ("gerar_be8_profile",         "Be8 · Perfil institucional"),
]

def run_one(module_name: str, label: str) -> dict:
    start = time.time()
    try:
        mod = import_module(module_name)
        mod.run()
        dur = round(time.time() - start, 1)
        log.info(f"✓ {label} OK em {dur}s")
        return {"modulo": module_name, "label": label, "status": "OK", "duracao_s": dur}
    except Exception as e:
        dur = round(time.time() - start, 1)
        tb = traceback.format_exc()
        log.error(f"✗ {label} FALHOU em {dur}s · {e}")
        log.debug(tb)
        return {"modulo": module_name, "label": label, "status": "ERRO",
                "erro": str(e)[:300], "duracao_s": dur}

def run_all() -> dict:
    log.info("=" * 70)
    log.info(f"INICIANDO ATUALIZAÇÃO · {dt.datetime.now().isoformat(timespec='seconds')}")
    log.info("=" * 70)
    inicio = time.time()
    resultados = []
    for mod, label in COLETORES:
        resultados.append(run_one(mod, label))
    duracao = round(time.time() - inicio, 1)
    ok = sum(1 for r in resultados if r["status"] == "OK")
    err = sum(1 for r in resultados if r["status"] == "ERRO")
    log.info("=" * 70)
    log.info(f"FIM · {ok} OK · {err} ERROS · {duracao}s")
    log.info("=" * 70)

    # Resumo consolidado em status_fontes.json (campo extra: ultima_execucao)
    status_atual = load_json(STATUS_PATH, default={"fontes": {}})
    status_atual["ultima_execucao"] = {
        "timestamp": now_iso(),
        "duracao_segundos": duracao,
        "coletores_ok": ok,
        "coletores_erro": err,
        "detalhes": resultados,
    }
    save_json(STATUS_PATH, status_atual)
    return status_atual["ultima_execucao"]

if __name__ == "__main__":
    summary = run_all()
    # Exit code 0 mesmo com falhas parciais (não quebra Actions)
    # Exit 1 só se TUDO falhou
    if summary["coletores_ok"] == 0:
        sys.exit(1)
    sys.exit(0)
