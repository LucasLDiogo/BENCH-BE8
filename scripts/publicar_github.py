"""
Publicador GitHub — Be8 Market Intelligence.
- Verifica se há mudanças em data/ ou downloads/
- Faz git add / commit / push com mensagem padronizada
- Não cria commit vazio
- Roda após o agente de atualização
"""
from __future__ import annotations
import subprocess, sys, datetime as dt
from pathlib import Path
from utils import log, ROOT

def sh(cmd: list[str], cwd: Path = ROOT) -> tuple[int, str, str]:
    """Roda comando e retorna (returncode, stdout, stderr)."""
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()

def has_changes() -> bool:
    code, out, _ = sh(["git", "status", "--porcelain", "data/", "downloads/"])
    if code != 0:
        log.error("git status falhou · este diretório é um repositório git?")
        return False
    return bool(out)

def run() -> None:
    if not (ROOT / ".git").exists():
        log.error("Diretório não é um repositório git. Rode 'git init' primeiro.")
        sys.exit(1)

    if not has_changes():
        log.info("Sem alterações em data/ · pulando commit")
        return

    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = f"Atualização automática Market Intelligence Be8 - {ts}"

    # add seletivo
    sh(["git", "add", "data/", "logs/"])

    # commit
    code, out, err = sh(["git", "commit", "-m", msg])
    if code != 0:
        log.warning(f"git commit retornou {code}: {err or out}")
        return
    log.info(f"Commit criado: {msg}")

    # push
    code, out, err = sh(["git", "push", "origin", "main"])
    if code != 0:
        log.error(f"git push falhou ({code}): {err}")
        # Fallback: tentar master
        code2, _, err2 = sh(["git", "push", "origin", "master"])
        if code2 != 0:
            log.error(f"git push (master) também falhou: {err2}")
            sys.exit(1)
    log.info("Push OK · GitHub Pages atualizará em ~30s")

if __name__ == "__main__":
    run()
