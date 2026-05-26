"""
BENCH-BE8 · baixar_anp_b100.py
---------------------------------------------------------------------
ANP · produção de biodiesel B100.
XLS mensal em gov.br/anp (caminho muda às vezes).

Estratégia: tenta URLs candidatas, e se não conseguir,
marca status='pendente' (sem inventar dado).
"""
from __future__ import annotations

from utils import get_logger, http_get, save_json, load_json

log = get_logger("baixar_anp_b100")

CANDIDATAS = [
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/producao-mensal-biodiesel.xlsx",
    "https://www.gov.br/anp/pt-br/assuntos/producao-e-fornecimento-de-biocombustiveis/biodiesel/producao-anual-de-biodiesel/producao-anual-de-biodiesel.xlsx",
]


def main():
    log.info("iniciando · ANP B100")
    # Tentativa de baixar binário (sem parsing — apenas validar disponibilidade)
    for url in CANDIDATAS:
        r = http_get(url, timeout=30)
        if r and r.content and len(r.content) > 5000:
            # arquivo existe — mas parsing XLS requer openpyxl
            # esta versão marca FALLBACK (arquivo disponível mas parser pendente)
            save_json("anp_b100.json", "ANP B100 (XLS)", "fallback",
                      dados={
                          "status_arquivo": "disponivel",
                          "url_origem":     url,
                          "tamanho_kb":     len(r.content) // 1024,
                      },
                      erro="Parser XLS ainda não implementado neste coletor. "
                           "Adicione lógica openpyxl em scripts/baixar_anp_b100.py "
                           "se desejar processar automaticamente.")
            log.info("arquivo encontrado (%d KB) · parser pendente", len(r.content) // 1024)
            return 0

    # Nenhuma URL respondeu
    save_json("anp_b100.json", "ANP B100", "indisponivel",
              erro="Nenhuma URL candidata da ANP retornou XLS. "
                   "Pode ter mudado o caminho — atualize CANDIDATAS no script.")
    log.warning("nenhuma URL candidata respondeu")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
