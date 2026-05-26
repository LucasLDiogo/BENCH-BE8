"""
Coletor ANP — Preços de Combustíveis (semanal, por revenda).
Estratégia resiliente:
  1) Tenta o portal de DADOS ABERTOS da ANP e descobre o link do CSV mais recente
  2) Faz fallback para URLs conhecidas (padrão histórico do dataset)
  3) Como último recurso, tenta o dataset paralelo no Portal Brasileiro de Dados Abertos
Parsing:
  - Encoding Windows-1252 (latin-1 também funciona como fallback)
  - Separador `;`, vírgula decimal
  - Padroniza nomes de colunas
Saída: data/anp_combustiveis.json (agregado nacional, regional, UF)
"""
from __future__ import annotations
import csv, io, re, datetime as dt
from collections import defaultdict
from pathlib import Path
from utils import (http_get, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, DOWNLOADS_DIR, log, now_iso, pct)

ANP_LANDING = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis"

# URLs históricas conhecidas dos CSVs por ano (padrão estável usado pela ANP)
# A ANP publica um CSV consolidado por semestre/ano
def _candidate_urls() -> list[str]:
    year = dt.date.today().year
    urls = []
    for y in [year, year - 1]:
        for sem in ["02", "01"]:
            urls.append(f"https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/ca-{y}-{sem}.csv")
            urls.append(f"https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/precos-semestrais-ca-{y}-{sem}.csv")
            urls.append(f"https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/shpc/dsas/ca/precos_semestrais_ca_{y}_{sem}.csv")
    return urls

def discover_csv_url() -> str | None:
    """Tenta extrair URL do CSV diretamente da página oficial."""
    try:
        html = http_get(ANP_LANDING, timeout=20).decode("utf-8", errors="ignore")
        # Procurar links .csv mais recentes
        links = re.findall(r'href="([^"]+\.csv)"', html, re.IGNORECASE)
        if links:
            # Prefere o que contém "ca-" (combustíveis automotivos) e ano atual
            year = str(dt.date.today().year)
            ranked = sorted(links, key=lambda u: (year in u, "ca" in u.lower(), len(u)), reverse=True)
            absolute = ranked[0]
            if absolute.startswith("/"):
                absolute = "https://www.gov.br" + absolute
            return absolute
    except Exception as e:
        log.debug(f"Discovery falhou: {e}")
    return None

def _try_download() -> tuple[bytes | None, str | None]:
    """Tenta múltiplas URLs até obter um CSV válido."""
    # 1) Descoberta
    url = discover_csv_url()
    if url:
        try:
            log.info(f"ANP · tentando URL descoberta: {url}")
            data = http_get(url, timeout=60)
            if data and len(data) > 5000 and b";" in data[:5000]:
                return data, url
        except Exception as e:
            log.warning(f"ANP descoberta falhou: {e}")
    # 2) Candidatos
    for u in _candidate_urls():
        try:
            log.info(f"ANP · tentando fallback: {u}")
            data = http_get(u, timeout=60)
            if data and len(data) > 5000:
                return data, u
        except Exception:
            continue
    return None, None

def _decode(raw: bytes) -> str:
    for enc in ("cp1252", "latin-1", "utf-8-sig", "utf-8"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("latin-1", errors="ignore")

def _to_float(s: str) -> float | None:
    if s is None: return None
    s = s.strip().replace(".", "").replace(",", ".")
    if s == "" or s.upper() in ("NULL", "NA", "-"):
        return None
    try: return float(s)
    except: return None

# Mapeamento dos nomes de coluna (a ANP varia entre arquivos)
COL_MAP = {
    "data da coleta":    "data_coleta",
    "data":              "data_coleta",
    "regiao - sigla":    "regiao",
    "regiao":            "regiao",
    "região - sigla":    "regiao",
    "estado - sigla":    "uf",
    "uf":                "uf",
    "estado":            "uf",
    "municipio":         "municipio",
    "município":         "municipio",
    "produto":           "produto",
    "valor de venda":    "preco_venda",
    "valor de compra":   "preco_compra",
    "preço de revenda":  "preco_venda",
    "preco de revenda":  "preco_venda",
    "unidade de medida": "unidade",
    "bandeira":          "bandeira",
    "revenda":           "revenda",
    "cnpj da revenda":   "cnpj",
}

def _normalize_header(h: str) -> str:
    h = h.strip().lower().replace("\ufeff", "")
    return COL_MAP.get(h, h.replace(" ", "_"))

def parse_csv(raw: bytes) -> list[dict]:
    text = _decode(raw)
    # Detecta separador
    sample = text[:2000]
    sep = ";" if sample.count(";") > sample.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=sep, quotechar='"')
    rows = list(reader)
    if not rows: return []
    headers_raw = rows[0]
    headers = [_normalize_header(h) for h in headers_raw]
    out = []
    for r in rows[1:]:
        if len(r) != len(headers): continue
        d = dict(zip(headers, r))
        out.append({
            "data_coleta": d.get("data_coleta", "").strip()[:10],
            "uf":          (d.get("uf") or "").strip().upper(),
            "regiao":      (d.get("regiao") or "").strip().upper(),
            "municipio":   (d.get("municipio") or "").strip(),
            "produto":     (d.get("produto") or "").strip().upper(),
            "preco_venda": _to_float(d.get("preco_venda", "")),
            "preco_compra": _to_float(d.get("preco_compra", "")),
            "unidade":     (d.get("unidade") or "R$/l").strip(),
            "bandeira":    (d.get("bandeira") or "").strip(),
        })
    return out

# Normaliza nomes de produtos (ANP varia)
PRODUCT_NORM = {
    "GASOLINA":           "GASOLINA",
    "GASOLINA COMUM":     "GASOLINA",
    "GASOLINA ADITIVADA": "GASOLINA_ADITIVADA",
    "ETANOL":             "ETANOL",
    "ETANOL HIDRATADO":   "ETANOL",
    "ÓLEO DIESEL":        "DIESEL_S500",
    "OLEO DIESEL":        "DIESEL_S500",
    "DIESEL":             "DIESEL_S500",
    "ÓLEO DIESEL S10":    "DIESEL_S10",
    "OLEO DIESEL S10":    "DIESEL_S10",
    "DIESEL S10":         "DIESEL_S10",
    "GNV":                "GNV",
    "GLP":                "GLP",
}

PRODUCT_LABEL = {
    "DIESEL_S10":         "Diesel S10",
    "DIESEL_S500":        "Diesel S500",
    "GASOLINA":           "Gasolina",
    "GASOLINA_ADITIVADA": "Gasolina Aditivada",
    "ETANOL":             "Etanol Hidratado",
    "GLP":                "GLP (13kg)",
    "GNV":                "GNV",
}

def aggregate(rows: list[dict]) -> dict:
    """Calcula médias por produto, UF, região, Brasil + ranking."""
    # Mantém apenas pesquisas das últimas 6 semanas
    if not rows:
        return {}
    rows = [r for r in rows if r["data_coleta"] and r["preco_venda"]]
    # Normalizar produto
    for r in rows:
        r["produto_norm"] = PRODUCT_NORM.get(r["produto"], r["produto"])
    # Identifica a semana mais recente (data máxima)
    dates = sorted({r["data_coleta"] for r in rows})
    if not dates: return {}
    last_date = dates[-1]
    # Pega últimas 6 datas distintas (proxy de semanas)
    keep_dates = set(dates[-12:])
    last_week_dates = set(dates[-6:])
    prev_week_dates = set(dates[-12:-6]) if len(dates) >= 12 else set()

    rows = [r for r in rows if r["data_coleta"] in keep_dates]

    # Médias por produto (Brasil)
    by_prod_now = defaultdict(list)
    by_prod_prev = defaultdict(list)
    by_prod_uf_now = defaultdict(lambda: defaultdict(list))
    by_prod_reg_now = defaultdict(lambda: defaultdict(list))

    for r in rows:
        p = r["produto_norm"]
        if p not in PRODUCT_LABEL: continue
        if r["data_coleta"] in last_week_dates:
            by_prod_now[p].append(r["preco_venda"])
            by_prod_uf_now[p][r["uf"]].append(r["preco_venda"])
            by_prod_reg_now[p][r["regiao"]].append(r["preco_venda"])
        elif r["data_coleta"] in prev_week_dates:
            by_prod_prev[p].append(r["preco_venda"])

    def mean(lst): return round(sum(lst)/len(lst), 4) if lst else None

    produtos = []
    for p, label in PRODUCT_LABEL.items():
        atual = mean(by_prod_now.get(p, []))
        anterior = mean(by_prod_prev.get(p, []))
        if atual is None: continue
        # UF detalhado
        ufs = sorted([
            {"uf": uf, "preco_medio": mean(vs), "n_postos": len(vs)}
            for uf, vs in by_prod_uf_now[p].items() if uf
        ], key=lambda x: x["preco_medio"] or 0, reverse=True)
        # Região
        regioes = sorted([
            {"regiao": reg, "preco_medio": mean(vs), "n_postos": len(vs)}
            for reg, vs in by_prod_reg_now[p].items() if reg
        ], key=lambda x: x["preco_medio"] or 0, reverse=True)
        produtos.append({
            "produto_id": p,
            "produto":    label,
            "preco_medio_brasil":    atual,
            "preco_medio_anterior":  anterior,
            "variacao_semanal_pct":  pct(atual, anterior),
            "uf_mais_caro":   ufs[0]["uf"] if ufs else None,
            "uf_mais_barato": ufs[-1]["uf"] if ufs else None,
            "preco_mais_caro":   ufs[0]["preco_medio"] if ufs else None,
            "preco_mais_barato": ufs[-1]["preco_medio"] if ufs else None,
            "por_uf":     ufs,
            "por_regiao": regioes,
        })
    return {
        "data_referencia": last_date,
        "produtos": produtos,
    }

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "ANP · Levantamento semanal de preços (dados abertos)",
        "endpoint": ANP_LANDING,
        "status": "OK",
    }
    raw, url_used = _try_download()
    if not raw:
        log.error("ANP combustíveis: nenhum CSV acessível no momento.")
        out.update({"status": "ERRO", "erro": "CSV indisponível em todas as URLs candidatas",
                    "data_referencia": None, "produtos": []})
        save_json(DATA_DIR / "anp_combustiveis.json", out)
        mark_source_error("anp_combustiveis", "CSV indisponível", endpoint=ANP_LANDING)
        return

    # Salva o raw em downloads (auditoria)
    raw_path = DOWNLOADS_DIR / "anp" / f"precos_{dt.date.today().isoformat()}.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(raw)
    log.info(f"ANP · CSV salvo em {raw_path} ({len(raw)/1024:.0f} KB)")

    try:
        rows = parse_csv(raw)
        if not rows:
            raise RuntimeError("CSV parseado mas sem linhas válidas")
        agg = aggregate(rows)
        out.update(agg)
        out["url_csv"] = url_used
        out["linhas_carregadas"] = len(rows)
        save_json(DATA_DIR / "anp_combustiveis.json", out)
        mark_source_ok("anp_combustiveis", rows=len(rows),
                       note=f"ref {agg.get('data_referencia')} · {len(agg.get('produtos',[]))} produtos",
                       endpoint=url_used)
        log.info(f"ANP combustíveis OK · {len(rows)} linhas · ref {agg.get('data_referencia')}")
    except Exception as e:
        log.exception("ANP combustíveis: parsing falhou")
        out.update({"status": "ERRO", "erro": str(e)[:300], "data_referencia": None, "produtos": []})
        save_json(DATA_DIR / "anp_combustiveis.json", out)
        mark_source_error("anp_combustiveis", str(e), endpoint=url_used or ANP_LANDING)

if __name__ == "__main__":
    run()
