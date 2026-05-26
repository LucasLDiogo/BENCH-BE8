"""
BENCH-BE8 · baixar_usda.py
---------------------------------------------------------------------
USDA FAS PSD — Production, Supply & Distribution.

Endpoint público gratuito (sem chave para queries básicas):
  apps.fas.usda.gov/PSDOnlineApi
"""
from __future__ import annotations

from utils import get_logger, http_get, save_json

log = get_logger("baixar_usda")

# A API USDA PSD oficial requer um certo formato — endpoint base sujeito a
# atualização. Mantemos URL configurável e fazemos um único probe para
# checar disponibilidade. Em produção, ampliar com queries específicas
# por commodity (soja: 2222000, biodiesel: 4242000).
PROBE_URL = "https://apps.fas.usda.gov/PSDOnlineApi/api/commodity"


def main():
    log.info("iniciando · USDA PSD")
    r = http_get(PROBE_URL, timeout=30)
    if not r:
        save_json("usda_benchmarks.json", "USDA FAS PSD", "indisponivel",
                  erro="API USDA não respondeu (pode ser mudança de endpoint).")
        log.warning("API USDA indisponível")
        return 0

    # Probe OK — esquema completo de coleta por commodity vem em sprint futura.
    # Por ora marca como FALLBACK e devolve metadado de probe.
    save_json("usda_benchmarks.json", "USDA FAS PSD", "fallback",
              dados={
                  "probe":    "ok",
                  "endpoint": PROBE_URL,
                  "note":     "Implementar queries por commodity (soja=2222000, biodiesel=4242000).",
              })
    log.info("API alcançável · parser específico pendente")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
