"""
BENCH-BE8 · utils.py
---------------------------------------------------------------------
Helpers compartilhados por todos os coletores Python.
- HTTP com timeout, retry exponencial, User-Agent realista
- Salvar JSON com schema padronizado
- Logger consistente com prefixo
"""
from __future__ import annotations

import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import requests

# Pasta raiz do projeto = um nível acima de scripts/
ROOT     = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
LOG_DIR  = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

# Logger padrão
def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] · %(name)s · %(levelname)s · %(message)s",
                            datefmt="%H:%M:%S")
    # stdout
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    # arquivo
    fh = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    return logger


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def http_get(url: str, timeout: int = 20, retries: int = 3,
             headers: Optional[dict] = None, params: Optional[dict] = None,
             verify: bool = True) -> Optional[requests.Response]:
    """GET HTTP defensivo: retry exponencial, UA realista, no-cache."""
    hdrs = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/csv, text/html, */*;q=0.8",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    }
    if headers:
        hdrs.update(headers)
    for attempt in range(1, retries + 1):
        try:
            r = requests.get(url, headers=hdrs, params=params,
                             timeout=timeout, verify=verify)
            if r.status_code == 200:
                return r
            if r.status_code in (429, 503):
                wait = 2 ** attempt
                time.sleep(wait)
                continue
            return None  # 4xx outros → não recupera
        except (requests.Timeout, requests.ConnectionError) as e:
            if attempt == retries:
                return None
            time.sleep(2 ** attempt)
    return None


def save_json(filename: str, fonte: str, status: str,
              dados: Any = None, erro: Optional[str] = None) -> Path:
    """
    Salva um JSON em /data com o SCHEMA PADRÃO:
        { fonte, status, ultima_atualizacao, dados, erro }

    status: 'ok' | 'fallback' | 'erro' | 'indisponivel' | 'pendente'
    """
    payload = {
        "fonte": fonte,
        "status": status,
        "ultima_atualizacao": datetime.now(timezone.utc).isoformat(),
        "dados": dados if dados is not None else {},
        "erro": erro,
    }
    path = DATA_DIR / filename
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_json(filename: str) -> Optional[dict]:
    """Carrega JSON de /data, retorna None se não existir / inválido."""
    path = DATA_DIR / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def pct_change(novo: float, antigo: float) -> Optional[float]:
    """Variação percentual entre dois valores. None se inválido."""
    if antigo is None or antigo == 0 or novo is None:
        return None
    try:
        return ((novo - antigo) / antigo) * 100.0
    except (TypeError, ZeroDivisionError):
        return None
