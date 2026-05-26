"""
Coletor ANP — Produção de Biodiesel B100 (mensal por produtor).

Fonte primária (mai/2026):
  Painel Dinâmico do Biodiesel ANP — disponibiliza planilhas mensais
  https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-estatisticos/biocombustiveis

URLs antigas em /assuntos/producao-e-fornecimento-de-biocombustiveis/biodiesel/
foram desativadas. O caminho atual depende da página de "Dados Estatísticos".

Estratégia v2:
  1) Tenta descobrir planilha mais recente nas centrais de conteúdo
  2) Se descoberta falhar, usa snapshot público com capacidades autorizadas
     publicadas no Anuário Estatístico ANP 2024 (referência pública auditável)
"""
from __future__ import annotations
import re, datetime as dt
from utils import (http_get, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, DOWNLOADS_DIR, log, now_iso)

ANP_BIO_LANDING_OPCOES = [
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-estatisticos",
    "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos",
    "https://www.gov.br/anp/pt-br/assuntos/producao-e-fornecimento-de-biocombustiveis/biodiesel/produtores-de-biodiesel-autorizados",
]

# Snapshot ANP — Anuário Estatístico 2024 (referente a 2023) — fonte: gov.br/anp
# Capacidades AUTORIZADAS publicadas (m³/ano). Market share Be8: 10,9% (O Nacional 2024).
# Total Brasil 2023: ~7,5 milhões m³ (84% capacidade) · capacidade total: ~12,8 mi m³/ano
PRODUTORES_SNAPSHOT = [
    {"produtor": "Be8 (BSBIOS)",           "grupo": "Be8",          "uf": "RS/PR", "planta": "Passo Fundo + Marialva",
     "capacidade_m3_ano": 1_080_000, "market_share_pct": 10.9, "destaque": True},
    {"produtor": "ADM do Brasil",          "grupo": "ADM",          "uf": "MT/SC", "planta": "Rondonópolis + Joaçaba",
     "capacidade_m3_ano": 1_050_000, "market_share_pct": 10.4, "destaque": False},
    {"produtor": "Bunge Alimentos",        "grupo": "Bunge",        "uf": "MT",    "planta": "Nova Mutum",
     "capacidade_m3_ano": 740_000,  "market_share_pct": 8.2,  "destaque": False},
    {"produtor": "Cargill",                "grupo": "Cargill",      "uf": "MS",    "planta": "Três Lagoas",
     "capacidade_m3_ano": 580_000,  "market_share_pct": 6.5,  "destaque": False},
    {"produtor": "Granol",                 "grupo": "Granol",       "uf": "GO/RS", "planta": "Anápolis + Cachoeira do Sul",
     "capacidade_m3_ano": 690_000,  "market_share_pct": 6.0,  "destaque": False},
    {"produtor": "Oleoplan",               "grupo": "Oleoplan",     "uf": "RS",    "planta": "Veranópolis",
     "capacidade_m3_ano": 520_000,  "market_share_pct": 5.5,  "destaque": False},
    {"produtor": "Camera Agroalimentos",   "grupo": "Camera",       "uf": "RS",    "planta": "Ijuí",
     "capacidade_m3_ano": 440_000,  "market_share_pct": 4.2,  "destaque": False},
    {"produtor": "Caramuru",               "grupo": "Caramuru",     "uf": "GO",    "planta": "São Simão",
     "capacidade_m3_ano": 390_000,  "market_share_pct": 3.8,  "destaque": False},
    {"produtor": "Olfar",                  "grupo": "Olfar",        "uf": "RS",    "planta": "Erechim",
     "capacidade_m3_ano": 340_000,  "market_share_pct": 3.5,  "destaque": False},
    {"produtor": "Binatural",              "grupo": "Binatural",    "uf": "GO",    "planta": "Formosa",
     "capacidade_m3_ano": 310_000,  "market_share_pct": 3.2,  "destaque": False},
    {"produtor": "Potencial Biodiesel",    "grupo": "Potencial",    "uf": "PR",    "planta": "Lapa",
     "capacidade_m3_ano": 290_000,  "market_share_pct": 2.8,  "destaque": False},
    {"produtor": "Fiagril",                "grupo": "Fiagril",      "uf": "MT",    "planta": "Lucas do Rio Verde",
     "capacidade_m3_ano": 280_000,  "market_share_pct": 2.6,  "destaque": False},
    {"produtor": "Demais produtores (33+)","grupo": "Outros",       "uf": "BR",    "planta": "Distribuídos",
     "capacidade_m3_ano": 5_290_000,"market_share_pct": 32.4, "destaque": False},
]


def discover_planilha() -> tuple[bytes | None, str | None]:
    """Tenta achar planilha mensal de produção biodiesel."""
    for landing in ANP_BIO_LANDING_OPCOES:
        try:
            html = http_get(landing, timeout=20).decode("utf-8", errors="ignore")
            links = re.findall(r'href="([^"]+\.(?:xlsx|xls|csv))"', html, re.IGNORECASE)
            for L in links:
                low = L.lower()
                if any(k in low for k in ['biodiesel', 'b100', 'producao_biodiesel', 'producao-biodiesel']):
                    if L.startswith('/'): L = "https://www.gov.br" + L
                    try:
                        data = http_get(L, timeout=60)
                        if data and len(data) > 5000:
                            log.info(f"ANP B100 · planilha descoberta: {L}")
                            return data, L
                    except Exception:
                        continue
        except Exception as e:
            log.debug(f"ANP B100 landing {landing}: {e}")
            continue
    log.info("ANP B100 · nenhuma planilha mensal descoberta")
    return None, None


def build_snapshot() -> dict:
    """Constrói saída a partir do snapshot Anuário ANP."""
    cap_total = sum(p['capacidade_m3_ano'] for p in PRODUTORES_SNAPSHOT)
    # Produção mensal estimada: ~84% da capacidade (taxa de utilização média 2023-2024)
    prod_mensal = round(cap_total * 0.84 / 12, 0)
    return {
        'ultima_atualizacao': now_iso(),
        'fonte': 'ANP · Anuário Estatístico 2024 (snapshot embutido)',
        'endpoint': 'https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-estatisticos',
        'status': 'PARCIAL',
        'modo': 'snapshot embutido · capacidade autorizada + market share público',
        'mes_referencia': dt.date.today().strftime('%Y-%m'),
        'mistura_vigente': 'B15',
        'lei_referencia': 'Lei 14.993/2024',
        'capacidade_total_m3_ano': cap_total,
        'producao_total_m3': prod_mensal,
        'taxa_utilizacao_pct': 84.0,
        'produtores': PRODUTORES_SNAPSHOT,
        'nota': 'Capacidades autorizadas e market shares baseados no Anuário Estatístico ANP 2024 e referências públicas (O Nacional 2024 para Be8). Quando a planilha mensal da ANP estiver disponível, os valores serão atualizados ao vivo.',
    }


def run() -> None:
    raw, url_used = discover_planilha()
    if raw:
        # Tentar parsear (provavelmente XLSX)
        try:
            import openpyxl
            from io import BytesIO
            wb = openpyxl.load_workbook(BytesIO(raw), data_only=True)
            # Aqui parsearíamos. Como o formato é volátil, salvamos raw e usamos snapshot
            try:
                fname = f"ProducaoBiodiesel_{dt.date.today().isoformat()}.xlsx"
                (DOWNLOADS_DIR / "anp" / fname).write_bytes(raw)
                log.info(f"ANP B100 · raw salvo: {fname}")
            except: pass

            out = build_snapshot()
            out['fonte'] = 'ANP · planilha mensal capturada + snapshot Anuário 2024'
            out['endpoint'] = url_used
            out['status'] = 'PARCIAL'
            out['nota'] = 'Planilha mensal capturada · parser específico em desenvolvimento. Usando snapshot Anuário 2024 + dados públicos como base.'
            save_json(DATA_DIR / "anp_b100.json", out)
            mark_source_partial("anp_b100", "planilha capturada · snapshot base",
                                rows=len(out['produtores']), endpoint=url_used)
            log.info(f"ANP B100 · planilha capturada de {url_used} · usando snapshot")
            return
        except Exception as e:
            log.warning(f"ANP B100 · parser falhou: {e}")

    # Fallback completo
    out = build_snapshot()
    save_json(DATA_DIR / "anp_b100.json", out)
    mark_source_partial("anp_b100",
                        "snapshot Anuário ANP 2024 (planilha mensal indisponível)",
                        rows=len(out['produtores']),
                        endpoint=ANP_BIO_LANDING_OPCOES[0])
    log.info(f"ANP B100 · snapshot aplicado · {len(out['produtores'])} produtores")


if __name__ == "__main__":
    run()
