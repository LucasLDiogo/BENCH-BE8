"""
Coletor IBGE SIDRA — Produção Agrícola Municipal/UF.
Usa a API REST oficial: https://apisidra.ibge.gov.br
Tabela 6588 — LSPA (Levantamento Sistemático da Produção Agrícola), última estimativa.

Variáveis SIDRA tabela 6588:
  - 35 = área plantada (hectares)
  - 112 = quantidade produzida (toneladas)
  - 215 = rendimento médio (kg/ha)
Culturas (classificação 845):
  - 2713 = soja
  - 2711 = milho
  - 2716 = trigo

Saída: data/ibge_sidra.json
"""
from __future__ import annotations
import datetime as dt
from utils import (http_get_json, save_json, mark_source_ok, mark_source_error,
                   DATA_DIR, log, now_iso)

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"

# Tabela 6588 — LSPA (último mês disponível)
# Códigos das culturas no classificador 81/845
CULTURAS = {
    "Soja":  "2713",
    "Milho": "2711",
    "Trigo": "2716",
}
# Variáveis
VAR_PROD = "112"   # toneladas
VAR_AREA = "35"    # hectares
VAR_REND = "215"   # kg/ha

# Nível N3 = UF; N1 = Brasil
UFs_N3 = "N3"

def fetch_lspa(cultura_codigo: str) -> list[dict]:
    """Busca produção, área e rendimento da última estimativa LSPA para a cultura.
    URL exemplo:
      /t/6588/n3/all/v/112,35,215/p/last%201/c81/2713
    """
    url = (f"{SIDRA_BASE}/t/6588/n3/all"
           f"/v/{VAR_PROD},{VAR_AREA},{VAR_REND}"
           f"/p/last%201/c81/{cultura_codigo}")
    try:
        data = http_get_json(url, timeout=30)
    except Exception as e:
        log.warning(f"SIDRA cultura {cultura_codigo}: {e}")
        return []
    if not data or len(data) < 2:
        return []
    # SIDRA retorna header na linha 0 e dados nas demais
    header = data[0]
    rows = data[1:]
    out = []
    for r in rows:
        try:
            uf_nome = r.get("D1N") or r.get("D2N")
            uf_cod  = r.get("D1C") or ""
            var_nome = r.get("D3N") or r.get("D4N") or ""
            valor   = r.get("V")
            periodo = r.get("D5N") or r.get("D4N") or ""
            try:
                valor_num = float(valor) if valor and valor not in ("-", "...", "..") else None
            except: valor_num = None
            out.append({
                "uf": uf_nome,
                "codigo_uf": uf_cod,
                "variavel": var_nome,
                "valor": valor_num,
                "periodo": periodo,
            })
        except Exception:
            continue
    return out

def consolidate(raw_data: dict) -> dict:
    """Reorganiza por UF × variável."""
    by_culture = {}
    for cultura, registros in raw_data.items():
        by_uf = {}
        for r in registros:
            uf = r["uf"]
            if not uf: continue
            if uf not in by_uf:
                by_uf[uf] = {"uf": uf, "producao_t": None, "area_ha": None, "rendimento_kg_ha": None,
                             "periodo": r.get("periodo")}
            var = (r.get("variavel") or "").lower()
            if "produzida" in var or "quantidade" in var:
                by_uf[uf]["producao_t"] = r["valor"]
            elif "área" in var or "area" in var:
                by_uf[uf]["area_ha"] = r["valor"]
            elif "rendimento" in var:
                by_uf[uf]["rendimento_kg_ha"] = r["valor"]
        # Remove Brasil consolidado para não duplicar
        ufs = [v for k, v in by_uf.items() if k.upper() != "BRASIL"]
        # Ranking
        ufs.sort(key=lambda x: x.get("producao_t") or 0, reverse=True)
        # Share
        total_prod = sum(u["producao_t"] or 0 for u in ufs)
        for u in ufs:
            if total_prod and u["producao_t"]:
                u["share_pct"] = round(u["producao_t"] / total_prod * 100, 2)
            else:
                u["share_pct"] = None
        by_culture[cultura] = {
            "ufs": ufs,
            "total_producao_t": total_prod if total_prod else None,
            "total_producao_mt": round(total_prod / 1_000_000, 2) if total_prod else None,
            "periodo": ufs[0]["periodo"] if ufs else None,
        }
    return by_culture

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "IBGE · SIDRA · Tabela 6588 (LSPA)",
        "endpoint": SIDRA_BASE,
        "status": "OK",
        "culturas": {},
    }
    raw_data = {}
    falhas = 0
    for cultura, cod in CULTURAS.items():
        registros = fetch_lspa(cod)
        if registros:
            raw_data[cultura] = registros
            log.info(f"SIDRA {cultura}: {len(registros)} registros")
        else:
            falhas += 1
    if not raw_data:
        out["status"] = "ERRO"
        out["erro"] = "Nenhuma cultura retornou dados"
        save_json(DATA_DIR / "ibge_sidra.json", out)
        mark_source_error("ibge_sidra", "API retornou vazio", endpoint=SIDRA_BASE)
        return

    cons = consolidate(raw_data)
    out["culturas"] = cons
    if falhas:
        out["status"] = "PARCIAL"
    save_json(DATA_DIR / "ibge_sidra.json", out)
    total_rows = sum(len(c["ufs"]) for c in cons.values())
    mark_source_ok("ibge_sidra", rows=total_rows,
                   note=f"{len(cons)} culturas · {total_rows} UFs · tab 6588",
                   endpoint=SIDRA_BASE)
    log.info(f"IBGE SIDRA OK · {len(cons)} culturas · {total_rows} UFs")

if __name__ == "__main__":
    run()
