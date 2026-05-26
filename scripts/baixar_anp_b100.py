"""
Coletor ANP — Produção de Biodiesel B100 (mensal por produtor).
A ANP publica planilhas XLS/XLSX em:
  https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-estatisticos/biocombustiveis

Estratégia: descobre links das planilhas; se openpyxl/xlrd não estiverem
disponíveis, registra a fonte como "PARCIAL · planilha baixada · parser pendente".
Mantém o painel funcional com a estrutura de produtores conhecida publicamente.
Saída: data/anp_b100.json
"""
from __future__ import annotations
import re, datetime as dt
from utils import (http_get, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, DOWNLOADS_DIR, log, now_iso)

ANP_BIO_LANDING = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-estatisticos/biocombustiveis"

# Lista de produtores B100 publicamente conhecidos (Anuário Estatístico ANP / leilões públicos).
# Esta lista NÃO inventa shares — apenas mantém a estrutura. O Power Query/ETL real
# preencherá os campos numéricos quando a planilha for parseada.
PRODUTORES_BASE = [
    {"produtor": "Be8 (BSBIOS)",       "grupo": "Be8",          "plantas": ["Passo Fundo (RS)", "Marialva (PR)"]},
    {"produtor": "ADM do Brasil",      "grupo": "ADM",          "plantas": ["Rondonópolis (MT)", "Joaçaba (SC)"]},
    {"produtor": "Bunge Alimentos",    "grupo": "Bunge",        "plantas": ["Nova Mutum (MT)"]},
    {"produtor": "Cargill",            "grupo": "Cargill",      "plantas": ["Três Lagoas (MS)"]},
    {"produtor": "Granol",             "grupo": "Granol",       "plantas": ["Anápolis (GO)", "Cachoeira do Sul (RS)"]},
    {"produtor": "Oleoplan",           "grupo": "Oleoplan",     "plantas": ["Veranópolis (RS)"]},
    {"produtor": "Camera Agroalimentos","grupo": "Camera",      "plantas": ["Ijuí (RS)"]},
    {"produtor": "Caramuru",           "grupo": "Caramuru",     "plantas": ["São Simão (GO)"]},
    {"produtor": "Olfar",              "grupo": "Olfar",        "plantas": ["Erechim (RS)"]},
    {"produtor": "Potencial Biodiesel","grupo": "Potencial",    "plantas": ["Lapa (PR)"]},
    {"produtor": "Binatural",          "grupo": "Binatural",    "plantas": ["Formosa (GO)"]},
    {"produtor": "Fiagril",            "grupo": "Fiagril",      "plantas": ["Lucas do Rio Verde (MT)"]},
]

def discover_xlsx_links() -> list[str]:
    """Procura links de planilhas mensais de produção B100 na página da ANP."""
    try:
        html = http_get(ANP_BIO_LANDING, timeout=20).decode("utf-8", errors="ignore")
        links = re.findall(r'href="([^"]+\.(?:xlsx|xls|csv))"', html, re.IGNORECASE)
        # Filtra apenas os de biodiesel/B100/produção
        keywords = ["biodiesel", "b100", "producao", "produção"]
        candidates = []
        for L in links:
            low = L.lower()
            if any(k in low for k in keywords):
                if L.startswith("/"):
                    L = "https://www.gov.br" + L
                candidates.append(L)
        return candidates
    except Exception as e:
        log.debug(f"ANP B100 discovery falhou: {e}")
        return []

def try_parse_xlsx(raw: bytes) -> list[dict] | None:
    """Tenta parsear XLSX com openpyxl (se disponível). Retorna None se lib ausente."""
    try:
        import openpyxl
        from io import BytesIO
        wb = openpyxl.load_workbook(BytesIO(raw), data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return None
        # Tenta detectar header
        header_row = None
        for i, row in enumerate(rows[:10]):
            if row and any(isinstance(c, str) and "produtor" in c.lower() for c in row if c):
                header_row = i
                break
        if header_row is None:
            return None
        header = [str(c).strip().lower() if c else "" for c in rows[header_row]]
        out = []
        for r in rows[header_row+1:]:
            if not r or not r[0]: continue
            rec = dict(zip(header, r))
            out.append(rec)
        return out
    except ImportError:
        log.warning("openpyxl não instalado · planilha salva mas não parseada")
        return None
    except Exception as e:
        log.warning(f"Falha parse XLSX: {e}")
        return None

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "ANP · Dados estatísticos · Biocombustíveis",
        "endpoint": ANP_BIO_LANDING,
        "status": "PARCIAL",
        "mes_referencia": None,
        "producao_brasil_m3": None,
        "capacidade_brasil_m3_ano": None,
        "taxa_utilizacao_pct": None,
        "mistura_atual": "B15",  # vigente desde mar/2025 conforme Lei 14.993/2024
        "mistura_proxima": "B16 (mar/2026)",
        "produtores": [],
    }

    # Estrutura de produtores SEM inventar shares
    for p in PRODUTORES_BASE:
        out["produtores"].append({
            **p,
            "uf_principal": p["plantas"][0].split("(")[-1].replace(")", "").strip() if p["plantas"] else "",
            "volume_m3_mes": None,
            "capacidade_m3_ano": None,
            "market_share_pct": None,
            "ranking": None,
            "status_dado": "aguardando parser ANP",
        })

    # Tentar baixar planilha
    links = discover_xlsx_links()
    log.info(f"ANP B100 · {len(links)} links candidatos encontrados")

    parsed_any = False
    for url in links[:3]:
        try:
            raw = http_get(url, timeout=45)
            fname = url.rsplit("/", 1)[-1]
            (DOWNLOADS_DIR / "anp" / fname).write_bytes(raw)
            log.info(f"ANP B100 · baixado {fname} ({len(raw)/1024:.0f} KB)")
            data = try_parse_xlsx(raw)
            if data:
                parsed_any = True
                # Aqui caberia o mapping linha→produtor. Por ora, marca como parcial.
                out["linhas_planilha"] = len(data)
                log.info(f"ANP B100 · {len(data)} linhas extraídas (parser estrutural)")
                break
        except Exception as e:
            log.warning(f"ANP B100 download falhou {url}: {e}")
            continue

    if parsed_any:
        out["status"] = "PARCIAL"
        out["nota"] = "Planilha baixada e parseada. Mapping linha→produtor a finalizar."
        mark_source_partial("anp_b100",
                            note="planilha capturada · mapping a finalizar",
                            rows=len(PRODUTORES_BASE), endpoint=ANP_BIO_LANDING)
    elif links:
        out["status"] = "PARCIAL"
        out["nota"] = "Planilha localizada mas parser openpyxl indisponível neste ambiente."
        mark_source_partial("anp_b100",
                            note="planilha capturada · openpyxl pendente",
                            rows=0, endpoint=ANP_BIO_LANDING)
    else:
        out["status"] = "ERRO"
        out["nota"] = "Nenhum link de planilha localizado na página ANP. Estrutura de produtores preservada."
        mark_source_error("anp_b100",
                          "Nenhum link XLSX/XLS localizado",
                          endpoint=ANP_BIO_LANDING)

    save_json(DATA_DIR / "anp_b100.json", out)

if __name__ == "__main__":
    run()
