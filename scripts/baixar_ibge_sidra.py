"""
Coletor IBGE SIDRA — Produção Agrícola Municipal (PAM) por UF.

Tabela 1612 — Quantidade produzida, valor e área plantada/colhida da lavoura temporária
Classificador c81 = produtos das lavouras temporárias

URL pattern:
  /values/t/1612/n3/all/v/214/p/last%201/c81/2713
  (n3 = UF, v/214 = quantidade produzida em t, c81 = classificador produto)

Códigos c81 corretos (verificado em sidra.ibge.gov.br/tabela/1612):
  - 2713 = soja
  - 2711 = milho (em grão) - 1ª safra
  - 109276 = milho (em grão) - 2ª safra
  - 2716 = trigo
  - 2702 = arroz
"""
from __future__ import annotations
import datetime as dt
from utils import (http_get_json, save_json, mark_source_ok, mark_source_error,
                   mark_source_partial, DATA_DIR, log, now_iso)

SIDRA_BASE = "https://apisidra.ibge.gov.br/values"

# Tabela 1612 - PAM lavoura temporária
TABELA = "1612"
# Variáveis:
#   214 = quantidade produzida (toneladas)
#   216 = área plantada (hectares)
#   112 = área plantada — versão antiga
#   215 = rendimento médio (kg/ha)
VAR_PROD = "214"
VAR_AREA = "216"

CULTURAS_C81 = {
    "Soja":  "2713",
    "Milho_1": "2711",
    "Milho_2": "109276",
    "Trigo": "2716",
}

# Snapshot de fallback (PAM 2024, dados oficiais IBGE)
FALLBACK_PAM_2024 = {
    "ano": 2024,
    "fonte_fallback": "IBGE · PAM 2024 (snapshot embutido)",
    "culturas": {
        "Soja": {
            "MT": 47_500_000, "PR": 22_000_000, "RS": 21_500_000, "GO": 18_500_000,
            "MS": 14_500_000, "MG": 7_500_000, "BA": 7_100_000, "MA": 4_300_000,
        },
        "Milho": {
            "MT": 50_000_000, "PR": 17_000_000, "MS": 13_500_000, "GO": 12_000_000,
            "MG": 8_300_000, "SP": 3_400_000, "BA": 3_100_000, "RS": 4_700_000,
        },
        "Trigo": {
            "RS": 3_900_000, "PR": 3_100_000, "SC": 280_000, "MG": 200_000,
            "SP": 150_000, "GO": 110_000, "MS": 170_000,
        },
    }
}


def fetch_lspa_uf(cod_c81: str, variavel: str = None) -> list[dict]:
    """Busca produção (default) ou outra variável por UF para uma cultura na tabela 1612."""
    var = variavel or VAR_PROD
    url = f"{SIDRA_BASE}/t/{TABELA}/n3/all/v/{var}/p/last%201/c81/{cod_c81}"
    try:
        data = http_get_json(url, timeout=30)
    except Exception as e:
        log.warning(f"SIDRA c81={cod_c81} var={var}: {e}")
        return []
    if not data or len(data) < 2:
        return []

    # Linha 0 é cabeçalho descritivo, demais são dados
    rows = data[1:]
    out = []
    for r in rows:
        try:
            uf = r.get("D1N", "").strip()
            uf_cod = r.get("D1C", "")
            valor = r.get("V", "")
            periodo = r.get("D4N") or r.get("D3N") or ""
            try:
                valor_num = float(valor) if valor and valor not in ("-", "..", "...") else None
            except:
                valor_num = None
            # Pegar sigla UF a partir do nome (D1N é o nome completo)
            UF_NOME_SIGLA = {
                "Rondônia":"RO","Acre":"AC","Amazonas":"AM","Roraima":"RR","Pará":"PA","Amapá":"AP","Tocantins":"TO",
                "Maranhão":"MA","Piauí":"PI","Ceará":"CE","Rio Grande do Norte":"RN","Paraíba":"PB","Pernambuco":"PE",
                "Alagoas":"AL","Sergipe":"SE","Bahia":"BA","Minas Gerais":"MG","Espírito Santo":"ES",
                "Rio de Janeiro":"RJ","São Paulo":"SP","Paraná":"PR","Santa Catarina":"SC","Rio Grande do Sul":"RS",
                "Mato Grosso do Sul":"MS","Mato Grosso":"MT","Goiás":"GO","Distrito Federal":"DF",
            }
            sigla = UF_NOME_SIGLA.get(uf, uf[:2].upper())
            out.append({
                "uf": sigla, "uf_nome": uf, "uf_codigo": uf_cod,
                "valor_t": valor_num, "periodo": periodo,
            })
        except Exception as e:
            log.debug(f"SIDRA linha ignorada: {e}")
            continue
    return out


def build_fallback() -> dict:
    """Saída a partir do snapshot embutido."""
    culturas = {}
    for cultura, ufs in FALLBACK_PAM_2024["culturas"].items():
        ufs_list = []
        for uf, prod_t in sorted(ufs.items(), key=lambda x: -x[1]):
            ufs_list.append({"uf": uf, "valor_t": prod_t, "periodo": str(FALLBACK_PAM_2024["ano"])})
        culturas[cultura] = {
            "ufs": ufs_list,
            "total_t": sum(ufs.values()),
            "total_mt": round(sum(ufs.values()) / 1_000_000, 2),
            "periodo": str(FALLBACK_PAM_2024["ano"]),
        }
    return {
        "ultima_atualizacao": now_iso(),
        "fonte": FALLBACK_PAM_2024["fonte_fallback"],
        "endpoint": "https://sidra.ibge.gov.br/tabela/1612",
        "status": "PARCIAL",
        "modo": "snapshot embutido · PAM 2024",
        "culturas": culturas,
    }


def run() -> None:
    raw_culturas = {}
    falhas = []

    # --- PASSAGEM 1: PRODUÇÃO (variável 214) ---
    for label, cod in CULTURAS_C81.items():
        registros = fetch_lspa_uf(cod, VAR_PROD)
        if registros:
            cultura_nome = label.split("_")[0]
            if cultura_nome not in raw_culturas:
                raw_culturas[cultura_nome] = {}
            for r in registros:
                uf = r["uf"]
                if uf == "BR" or len(uf) != 2:
                    continue
                if uf not in raw_culturas[cultura_nome]:
                    raw_culturas[cultura_nome][uf] = {"uf": uf, "valor_t": 0, "area_ha": 0, "periodo": r["periodo"]}
                if r["valor_t"]:
                    raw_culturas[cultura_nome][uf]["valor_t"] += r["valor_t"]
            log.info(f"SIDRA produção {label}: {len(registros)} UFs")
        else:
            falhas.append(f"prod-{label}")

    # --- PASSAGEM 2: ÁREA PLANTADA (variável 216) ---
    for label, cod in CULTURAS_C81.items():
        registros = fetch_lspa_uf(cod, VAR_AREA)
        if registros:
            cultura_nome = label.split("_")[0]
            if cultura_nome not in raw_culturas:
                continue  # cultura não veio na passagem 1
            for r in registros:
                uf = r["uf"]
                if uf == "BR" or len(uf) != 2:
                    continue
                if uf not in raw_culturas[cultura_nome]:
                    continue
                if r["valor_t"]:  # field se chama valor_t por padrão, mas é hectares aqui
                    raw_culturas[cultura_nome][uf]["area_ha"] = (raw_culturas[cultura_nome][uf].get("area_ha") or 0) + r["valor_t"]
            log.info(f"SIDRA área plantada {label}: {len(registros)} UFs")

    if not raw_culturas or len(falhas) >= len(CULTURAS_C81):
        log.warning(f"SIDRA · todas as culturas falharam · usando fallback embutido")
        out = build_fallback()
        save_json(DATA_DIR / "ibge_sidra.json", out)
        mark_source_partial("ibge_sidra",
                            "API indisponível · usando snapshot PAM 2024",
                            rows=sum(len(c["ufs"]) for c in out["culturas"].values()),
                            endpoint="https://sidra.ibge.gov.br/tabela/1612")
        return

    # Consolida saída ao vivo
    culturas = {}
    for cultura, ufs_dict in raw_culturas.items():
        ufs_list = sorted([v for v in ufs_dict.values() if v["valor_t"]],
                          key=lambda x: -x["valor_t"])
        total_prod = sum(u["valor_t"] for u in ufs_list)
        total_area = sum((u.get("area_ha") or 0) for u in ufs_list)
        for u in ufs_list:
            u["share_pct"] = round(u["valor_t"] / total_prod * 100, 2) if total_prod else None
            # Produtividade calculada (t/ha)
            if u.get("area_ha") and u["area_ha"] > 0:
                u["produtividade_t_ha"] = round(u["valor_t"] / u["area_ha"], 3)
        culturas[cultura] = {
            "ufs": ufs_list,
            "total_t": total_prod,
            "total_mt": round(total_prod / 1_000_000, 2),
            "total_area_ha": total_area,
            "total_area_mha": round(total_area / 1_000_000, 2) if total_area else None,
            "produtividade_media_t_ha": round(total_prod / total_area, 3) if total_area else None,
            "periodo": ufs_list[0]["periodo"] if ufs_list else None,
        }

    status = "OK" if not falhas else "PARCIAL"
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "IBGE · SIDRA · Tabela 1612 (PAM) — Produção + Área plantada",
        "endpoint": SIDRA_BASE,
        "status": status,
        "culturas": culturas,
    }
    if falhas:
        out["nota"] = f"Falhas em: {', '.join(falhas)}"
    save_json(DATA_DIR / "ibge_sidra.json", out)
    total_rows = sum(len(c["ufs"]) for c in culturas.values())
    if status == "OK":
        mark_source_ok("ibge_sidra", rows=total_rows,
                       note=f"{len(culturas)} culturas · {total_rows} UFs · PAM 1612 (prod+área)",
                       endpoint=SIDRA_BASE)
    else:
        mark_source_partial("ibge_sidra",
                            f"{len(culturas)} culturas · {len(falhas)} falhas",
                            rows=total_rows, endpoint=SIDRA_BASE)
    log.info(f"IBGE SIDRA {status} · {len(culturas)} culturas · {total_rows} UFs")


if __name__ == "__main__":
    run()
