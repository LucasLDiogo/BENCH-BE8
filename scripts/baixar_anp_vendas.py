"""
BENCH-BE8 · baixar_anp_vendas.py
---------------------------------------------------------------------
ANP · vendas por distribuidora/UF (painel dados-abertos).
"""
from __future__ import annotations

from utils import get_logger, http_get, save_json

log = get_logger("baixar_anp_vendas")

CANDIDATAS = [
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/vendas-derivados-petroleo-e-biocombustiveis.csv",
]


def main():
    log.info("iniciando · ANP vendas")
    for url in CANDIDATAS:
        r = http_get(url, timeout=60)
        if r and r.content and len(r.content) > 5000:
            # CSV disponível — mas parser específico de painel ANP é volumoso
            save_json("anp_vendas.json", "ANP vendas", "fallback",
                      dados={"status_arquivo": "disponivel",
                             "url_origem": url,
                             "tamanho_kb": len(r.content) // 1024},
                      erro="Parser CSV ainda não implementado completamente. "
                           "Implementar agregação por UF/distribuidora em "
                           "scripts/baixar_anp_vendas.py.")
            log.info("arquivo encontrado (%d KB) · parser pendente",
                     len(r.content) // 1024)
            return 0

    save_json("anp_vendas.json", "ANP vendas", "indisponivel",
              erro="Nenhuma URL candidata respondeu.")
    log.warning("nenhuma URL candidata respondeu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
