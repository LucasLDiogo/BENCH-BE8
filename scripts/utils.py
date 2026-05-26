"""
Utilitários compartilhados pelos coletores Be8 Market Intelligence.
- HTTP com retry, timeout, User-Agent
- Salvamento atômico de JSON (não corrompe se script for interrompido)
- Logger unificado
- Registro de status de cada fonte (alimenta a página de Governança)
"""
from __future__ import annotations
import json, os, sys, time, logging, tempfile, shutil, datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from urllib.parse import quote
import ssl

# === Paths ===
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DOWNLOADS_DIR = ROOT / "downloads"
LOGS_DIR = ROOT / "logs"

for d in (DATA_DIR, DOWNLOADS_DIR, LOGS_DIR):
    d.mkdir(parents=True, exist_ok=True)

# === Logger ===
LOG_FILE = LOGS_DIR / "atualizacao.log"

def get_logger(name: str = "be8") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s · %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger

log = get_logger()

# === HTTP ===
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Be8-MarketIntel/1.0; +https://lucasldiogo.github.io/BENCH-BE8)",
    "Accept": "application/json, text/csv, text/html, */*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
}

def http_get(url: str, timeout: int = 30, retries: int = 3,
             headers: dict | None = None, verify_ssl: bool = True) -> bytes:
    """GET com retry exponencial. Retorna bytes ou levanta exceção."""
    ctx = None
    if not verify_ssl:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(url, headers={**DEFAULT_HEADERS, **(headers or {})})
            with urlopen(req, timeout=timeout, context=ctx) as r:
                return r.read()
        except (URLError, HTTPError, TimeoutError) as e:
            last_err = e
            wait = 2 ** attempt
            log.warning(f"HTTP retry {attempt+1}/{retries} em {wait}s · {url[:80]}… · {e}")
            time.sleep(wait)
    raise RuntimeError(f"HTTP falhou após {retries} tentativas: {last_err}")

def http_get_json(url: str, **kw) -> dict:
    raw = http_get(url, **kw)
    return json.loads(raw.decode("utf-8"))

def http_post_json(url: str, payload: dict, timeout: int = 30,
                   retries: int = 3, headers: dict | None = None) -> dict:
    """POST JSON com retry."""
    data = json.dumps(payload).encode("utf-8")
    h = {"Content-Type": "application/json", **DEFAULT_HEADERS, **(headers or {})}
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(url, data=data, headers=h, method="POST")
            with urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except (URLError, HTTPError, TimeoutError) as e:
            last_err = e
            wait = 2 ** attempt
            log.warning(f"POST retry {attempt+1}/{retries} em {wait}s · {e}")
            time.sleep(wait)
    raise RuntimeError(f"POST falhou após {retries} tentativas: {last_err}")

# === Salvamento atômico ===
def save_json(path: Path | str, payload: dict | list, indent: int = 2) -> None:
    """Salva JSON de forma atômica (escreve em tmp, renomeia)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp_", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=indent, default=str)
        shutil.move(tmp, path)
    except Exception:
        if os.path.exists(tmp): os.unlink(tmp)
        raise

def load_json(path: Path | str, default=None):
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Falha lendo {path}: {e}")
        return default

# === Status de fonte (alimenta página Governança) ===
STATUS_PATH = DATA_DIR / "status_fontes.json"

def update_source_status(source_id: str, **fields) -> None:
    """Atualiza/insere o status de uma fonte no arquivo central."""
    status = load_json(STATUS_PATH, default={"fontes": {}, "ultima_atualizacao_global": None})
    if "fontes" not in status:
        status["fontes"] = {}
    entry = status["fontes"].get(source_id, {})
    entry.update(fields)
    entry["ultima_verificacao"] = dt.datetime.now().isoformat(timespec="seconds")
    status["fontes"][source_id] = entry
    status["ultima_atualizacao_global"] = dt.datetime.now().isoformat(timespec="seconds")
    save_json(STATUS_PATH, status)

def mark_source_ok(source_id: str, rows: int = 0, note: str = "", endpoint: str = "") -> None:
    update_source_status(source_id,
                         status="OK",
                         ultima_atualizacao_ok=dt.datetime.now().isoformat(timespec="seconds"),
                         linhas=rows,
                         nota=note,
                         endpoint=endpoint)

def mark_source_error(source_id: str, error: str, endpoint: str = "") -> None:
    update_source_status(source_id,
                         status="ERRO",
                         ultimo_erro=str(error)[:300],
                         endpoint=endpoint)

def mark_source_partial(source_id: str, note: str, rows: int = 0, endpoint: str = "") -> None:
    update_source_status(source_id,
                         status="PARCIAL",
                         nota=note,
                         linhas=rows,
                         endpoint=endpoint)

# === Helpers ===
def today() -> str:
    return dt.date.today().isoformat()

def now_iso() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")

def pct(v_now: float, v_prev: float) -> float | None:
    try:
        if v_prev == 0 or v_prev is None or v_now is None:
            return None
        return (v_now - v_prev) / v_prev * 100.0
    except Exception:
        return None
