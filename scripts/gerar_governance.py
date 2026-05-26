"""
BENCH-BE8 · gerar_governance.py
---------------------------------------------------------------------
Lê o status de cada JSON em /data e gera /data/governance.json
+ /data/status_fontes.json com o consolidado.

Chamado SEMPRE no fim do agente, após todos os coletores rodarem.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from utils import get_logger, DATA_DIR

log = get_logger("gerar_governance")

# Catálogo central de fontes (uma linha por arquivo coletado)
CATALOGO = [
    {"arquivo": "cambio.json",           "fonte": "BCB PTAX",             "tipo": "API pública",  "atualizacao": "Diária 4x",   "custo": "Gratuita", "endpoint": "olinda.bcb.gov.br/odata/CotacaoMoeda"},
    {"arquivo": "commodities.json",      "fonte": "Yahoo Finance",        "tipo": "API pública",  "atualizacao": "15min delay", "custo": "Gratuita", "endpoint": "query1.finance.yahoo.com"},
    {"arquivo": "conab_graos.json",      "fonte": "CONAB safras",         "tipo": "CSV mensal",   "atualizacao": "Mensal",      "custo": "Gratuita", "endpoint": "conab.gov.br/info-agro/safras"},
    {"arquivo": "anp_combustiveis.json", "fonte": "ANP SLP combustíveis", "tipo": "CSV semanal",  "atualizacao": "Semanal",     "custo": "Gratuita", "endpoint": "gov.br/anp · SLP"},
    {"arquivo": "anp_b100.json",         "fonte": "ANP B100",             "tipo": "XLS mensal",   "atualizacao": "Mensal",      "custo": "Gratuita", "endpoint": "gov.br/anp · biodiesel"},
    {"arquivo": "anp_vendas.json",       "fonte": "ANP vendas UF",        "tipo": "CSV mensal",   "atualizacao": "Mensal",      "custo": "Gratuita", "endpoint": "gov.br/anp · vendas-derivados"},
    {"arquivo": "comex.json",            "fonte": "ComexStat MDIC",       "tipo": "API REST",     "atualizacao": "Mensal",      "custo": "Gratuita", "endpoint": "api-comexstat.mdic.gov.br"},
    {"arquivo": "noticias.json",         "fonte": "Notícias (RSS)",       "tipo": "RSS",          "atualizacao": "Contínua",    "custo": "Gratuita", "endpoint": "noticiasagricolas.com.br/rss"},
    {"arquivo": "be8_profile.json",      "fonte": "Be8 institucional",    "tipo": "Manifesto",    "atualizacao": "Quando muda", "custo": "Interna",  "endpoint": "/scripts/gerar_be8_profile.py"},
    {"arquivo": "usda_benchmarks.json",  "fonte": "USDA FAS PSD",         "tipo": "API REST",     "atualizacao": "Mensal",      "custo": "Gratuita", "endpoint": "apps.fas.usda.gov/PSDOnlineApi"},
]

# Fontes removidas/em desenvolvimento — aparecem na governança mas não no painel
FONTES_DEV = [
    {"fonte": "FRED",         "tipo": "API key",       "atualizacao": "—", "custo": "Gratuita",  "endpoint": "api.stlouisfed.org/fred", "status": "pendente", "linhas": None, "ultima_verificacao": None},
    {"fonte": "EIA",          "tipo": "API key",       "atualizacao": "—", "custo": "Gratuita",  "endpoint": "api.eia.gov",             "status": "pendente", "linhas": None, "ultima_verificacao": None},
    {"fonte": "Investing.com","tipo": "Web (anti-bot)","atualizacao": "—", "custo": "Gratuita",  "endpoint": "br.investing.com",        "status": "indisponivel", "linhas": None, "ultima_verificacao": datetime.now(timezone.utc).isoformat()},
    {"fonte": "CEPEA/ESALQ",  "tipo": "Iframe widget", "atualizacao": "Diária", "custo": "Gratuita", "endpoint": "cepea.org.br/br/widget.aspx", "status": "pendente", "linhas": None, "ultima_verificacao": None},
    {"fonte": "IBGE SIDRA",   "tipo": "API REST",      "atualizacao": "Mensal", "custo": "Gratuita", "endpoint": "apisidra.ibge.gov.br", "status": "pendente", "linhas": None, "ultima_verificacao": None},
]


def contar_linhas(dados) -> int | None:
    """Heurística para contar registros num JSON `dados`."""
    if dados is None:
        return None
    if isinstance(dados, list):
        return len(dados)
    if isinstance(dados, dict):
        # tenta achar lista significativa
        for k in ("ranking", "lista", "items", "rows", "ufs"):
            v = dados.get(k)
            if isinstance(v, list):
                return len(v)
        return len(dados)
    return None


def main():
    log.info("iniciando · governance")
    fontes = []
    ok_count = 0
    erros = []
    for entry in CATALOGO:
        path = DATA_DIR / entry["arquivo"]
        if not path.exists():
            fontes.append({**entry, "status": "indisponivel", "linhas": None,
                          "ultima_verificacao": None})
            continue
        try:
            j = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            fontes.append({**entry, "status": "erro", "linhas": None,
                          "ultima_verificacao": None})
            erros.append(entry["arquivo"])
            continue
        st = j.get("status", "pendente")
        if st == "ok":
            ok_count += 1
        if st == "erro":
            erros.append(entry["arquivo"])
        fontes.append({
            **entry,
            "status": st,
            "linhas": contar_linhas(j.get("dados")),
            "ultima_verificacao": j.get("ultima_atualizacao"),
        })

    # Adicionar fontes em desenvolvimento
    fontes.extend(FONTES_DEV)

    governance = {
        "fonte":              "Manifesto consolidado Be8",
        "status":             "ok" if not erros else "fallback",
        "ultima_atualizacao": datetime.now(timezone.utc).isoformat(),
        "fontes":             fontes,
    }
    (DATA_DIR / "governance.json").write_text(
        json.dumps(governance, ensure_ascii=False, indent=2), encoding="utf-8")

    # Resumo executivo simples
    total = len(CATALOGO)
    exec_summary = (
        f"Ciclo concluído com {ok_count}/{total} fontes ao vivo. "
        + (f"Erros em: {', '.join(erros)}. " if erros else "")
        + "Painel atualizado."
    )

    status_fontes = {
        "fonte":              "Agente de atualização Be8",
        "status":             "ok" if ok_count == total else ("fallback" if ok_count > 0 else "erro"),
        "ultima_atualizacao": datetime.now(timezone.utc).isoformat(),
        "exec_summary":       exec_summary,
        "fontes_ok":          ok_count,
        "fontes_total":       total,
        "erros":              erros,
    }
    (DATA_DIR / "status_fontes.json").write_text(
        json.dumps(status_fontes, ensure_ascii=False, indent=2), encoding="utf-8")

    log.info("ok · %d/%d ao vivo · %d erros", ok_count, total, len(erros))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
