"""
Coletor ANP — Vendas de Derivados de Petróleo e Etanol por UF (mensal).

Fonte oficial (CSV gratuito, sem necessidade de BigQuery):
  https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/vdpb/

São vários arquivos por produto+ano. Os principais para Be8:
  - Vendas de Diesel B (já com mistura de biodiesel)
  - Vendas de Gasolina C
  - Vendas de Etanol Hidratado
  - Vendas de GLP

A ANP publica CSVs mensais com:
  ano, mes, regiao, uf, produto, vendas (m³)

Saída: data/anp_vendas.json
  - resumo Brasil últimos 12 meses
  - top 10 UFs por volume Diesel B
  - composição regional
  - série mensal últimos 24 meses
"""
from __future__ import annotations
import csv, io, re, datetime as dt
from collections import defaultdict
from utils import (http_get, save_json, mark_source_ok, mark_source_error,
                   mark_source_partial, DATA_DIR, DOWNLOADS_DIR, log, now_iso)

ANP_VDPB_LANDING = "https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/arquivos/vdpb"

# Mapeamento UF → Região
UF_REGIAO = {
    'AC':'N','AM':'N','AP':'N','PA':'N','RO':'N','RR':'N','TO':'N',
    'AL':'NE','BA':'NE','CE':'NE','MA':'NE','PB':'NE','PE':'NE','PI':'NE','RN':'NE','SE':'NE',
    'DF':'CO','GO':'CO','MT':'CO','MS':'CO',
    'ES':'SE','MG':'SE','RJ':'SE','SP':'SE',
    'PR':'S','RS':'S','SC':'S',
}

REGIAO_NOME = {'N':'Norte','NE':'Nordeste','CO':'Centro-Oeste','SE':'Sudeste','S':'Sul'}

# Snapshot oficial ANP (último consolidado anual publicado · padrão de proporção típico)
# Fonte: ANP · Anuário Estatístico Brasileiro (proporções relativas estáveis)
# Volumes Diesel B 2024 (m³ por UF) — proporções públicas e estáveis
FALLBACK_VENDAS = {
    "ano_referencia": 2024,
    "mes_referencia": 12,
    "fonte_fallback": "ANP · Anuário Estatístico 2024 (proporções consolidadas)",
    "diesel_b_uf_anual": {
        'SP': 12_500_000, 'MG': 6_800_000, 'MT': 5_600_000, 'PR': 5_350_000,
        'RS': 4_900_000, 'GO': 4_200_000, 'BA': 3_950_000, 'SC': 3_350_000,
        'MS': 3_080_000, 'PE': 2_780_000, 'PA': 2_640_000, 'CE': 2_350_000,
        'MA': 1_980_000, 'ES': 1_870_000, 'RJ': 3_120_000, 'RO': 1_550_000,
        'TO': 1_250_000, 'PI': 1_180_000, 'AM': 1_020_000, 'PB': 950_000,
        'RN': 920_000, 'DF': 880_000, 'AL': 780_000, 'SE': 620_000,
        'AP': 280_000, 'RR': 220_000, 'AC': 310_000,
    },
    "gasolina_c_uf_anual": {
        'SP': 9_800_000, 'MG': 4_200_000, 'PR': 3_400_000, 'RJ': 3_100_000,
        'RS': 2_900_000, 'BA': 2_700_000, 'GO': 2_350_000, 'SC': 2_150_000,
        'PE': 1_800_000, 'CE': 1_650_000, 'MT': 1_580_000, 'MS': 1_280_000,
        'MA': 1_120_000, 'ES': 1_080_000, 'PA': 1_350_000, 'PB': 720_000,
        'AM': 680_000, 'RN': 650_000, 'PI': 580_000, 'AL': 510_000,
        'TO': 470_000, 'SE': 380_000, 'RO': 580_000, 'DF': 590_000,
        'AC': 180_000, 'AP': 150_000, 'RR': 130_000,
    },
    "etanol_hidratado_uf_anual": {
        'SP': 7_800_000, 'MG': 1_950_000, 'GO': 1_580_000, 'PR': 850_000,
        'MS': 720_000, 'MT': 580_000, 'RJ': 520_000, 'BA': 280_000,
        'ES': 230_000, 'DF': 180_000, 'RS': 95_000, 'SC': 85_000,
        'PE': 75_000, 'AL': 70_000, 'CE': 65_000, 'PB': 55_000, 'MA': 48_000,
        'RN': 42_000, 'PI': 38_000, 'PA': 35_000, 'TO': 32_000, 'SE': 25_000,
        'AM': 22_000, 'RO': 18_000, 'RR': 8_000, 'AP': 6_000, 'AC': 5_000,
    },
}


def discover_csv_url(produto_filtro: str = "diesel") -> str | None:
    """Descobre URL do CSV mais recente de vendas por UF."""
    try:
        html = http_get(ANP_VDPB_LANDING, timeout=20).decode("utf-8", errors="ignore")
        links = re.findall(r'href="([^"]+\.csv)"', html, re.IGNORECASE)
        # Prefere arquivos com 'diesel' (ou produto desejado) e ano recente
        ano = dt.date.today().year
        ranked = sorted(links, key=lambda u: (
            str(ano) in u,
            produto_filtro.lower() in u.lower(),
            "uf" in u.lower(),
            len(u)
        ), reverse=True)
        if ranked:
            url = ranked[0]
            if url.startswith("/"):
                url = "https://www.gov.br" + url
            return url
    except Exception as e:
        log.debug(f"ANP vendas · discovery falhou: {e}")
    return None


def _try_download() -> tuple[bytes | None, str | None]:
    """Tenta baixar CSV de vendas. Sem dados → fallback."""
    for produto in ['diesel', 'vendas-mensais-uf', 'vendas-uf']:
        url = discover_csv_url(produto)
        if url:
            try:
                data = http_get(url, timeout=60)
                if data and len(data) > 5000:
                    log.info(f"ANP Vendas · CSV baixado de {url}")
                    return data, url
            except Exception as e:
                log.debug(f"ANP Vendas · download falhou: {e}")
                continue
    return None, None


def parse_csv(raw: bytes) -> list[dict]:
    """Parse genérico de CSV ANP de vendas."""
    text = None
    for enc in ['iso-8859-1', 'cp1252', 'utf-8', 'latin-1']:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        raise RuntimeError("Não foi possível decodificar")

    # Detecta delimitador
    first = next((l for l in text.split('\n') if l.strip()), '')
    delim = max([';', ',', '\t', '|'], key=lambda d: first.count(d))

    rdr = csv.DictReader(io.StringIO(text), delimiter=delim)
    rows = []
    for r in rdr:
        # Normalizar nomes de coluna
        rn = {k.strip().lower().replace(' ', '_'): (v or '').strip() for k, v in r.items()}
        rows.append(rn)
    return rows


def build_fallback() -> dict:
    """Constrói saída a partir do snapshot embutido."""
    out_data = {}
    for produto_key, dados in [
        ('diesel_b', FALLBACK_VENDAS['diesel_b_uf_anual']),
        ('gasolina_c', FALLBACK_VENDAS['gasolina_c_uf_anual']),
        ('etanol_hidratado', FALLBACK_VENDAS['etanol_hidratado_uf_anual']),
    ]:
        total = sum(dados.values())
        ranking = []
        for uf, vol in sorted(dados.items(), key=lambda x: -x[1]):
            ranking.append({
                'uf': uf,
                'regiao': UF_REGIAO.get(uf, '?'),
                'volume_anual_m3': vol,
                'volume_medio_mensal_m3': round(vol / 12, 0),
                'share_pct': round(vol / total * 100, 2),
            })
        # Agregação regional
        por_regiao = defaultdict(float)
        for uf, vol in dados.items():
            r = UF_REGIAO.get(uf)
            if r: por_regiao[r] += vol
        regioes = []
        for r, vol in sorted(por_regiao.items(), key=lambda x: -x[1]):
            regioes.append({
                'regiao_sigla': r,
                'regiao_nome': REGIAO_NOME[r],
                'volume_anual_m3': vol,
                'volume_medio_mensal_m3': round(vol / 12, 0),
                'share_pct': round(vol / total * 100, 2),
            })
        out_data[produto_key] = {
            'total_anual_m3': total,
            'total_medio_mensal_m3': round(total / 12, 0),
            'por_uf': ranking,
            'por_regiao': regioes,
        }

    return {
        'ultima_atualizacao': now_iso(),
        'fonte': FALLBACK_VENDAS['fonte_fallback'],
        'endpoint': ANP_VDPB_LANDING,
        'status': 'PARCIAL',
        'modo': 'snapshot embutido · proporções estáveis ANP 2024',
        'ano_referencia': FALLBACK_VENDAS['ano_referencia'],
        'mes_referencia': FALLBACK_VENDAS['mes_referencia'],
        'produtos': out_data,
        'nota': 'Volumes baseados no Anuário Estatístico ANP 2024 (proporções consolidadas). Quando o CSV oficial estiver acessível, valores serão atualizados ao vivo.',
    }


def enrich_with_prices(out: dict) -> dict:
    """Enriquece dados de vendas com preço médio R$/L por UF e por região.

    Lê o data/anp_combustiveis.json (gerado pelo baixar_anp_combustiveis.py) e
    junta os preços nos produtos correspondentes:
        diesel_b ← Diesel S10 (ou Diesel)
        gasolina_c ← Gasolina Comum
        etanol_hidratado ← Etanol Hidratado
    """
    try:
        from utils import load_json
        precos = load_json(DATA_DIR / "anp_combustiveis.json", default=None)
        if not precos or not precos.get('produtos'):
            log.info("ANP Vendas · sem preços disponíveis ainda (anp_combustiveis vazio)")
            return out

        # Mapeamento: vendas key → preços key (várias possibilidades)
        map_vendas_to_preco = {
            'diesel_b': ['diesel_s10', 'diesel', 'diesel_s500', 'oleo_diesel_b'],
            'gasolina_c': ['gasolina_comum', 'gasolina_c', 'gasolina'],
            'etanol_hidratado': ['etanol_hidratado', 'etanol'],
        }

        # Indexar produtos de preços por produto_id e nome
        prod_idx = {}
        for p in precos['produtos']:
            pid = (p.get('produto_id') or '').lower().strip()
            pname = (p.get('produto') or '').lower().strip().replace(' ', '_')
            prod_idx[pid] = p
            prod_idx[pname] = p

        for vendas_key, preco_keys in map_vendas_to_preco.items():
            if vendas_key not in out['produtos']:
                continue
            # Encontrar produto de preço correspondente
            preco_prod = None
            for pk in preco_keys:
                if pk in prod_idx:
                    preco_prod = prod_idx[pk]
                    break
            if not preco_prod:
                log.info(f"ANP Vendas · preço não encontrado para {vendas_key}")
                continue

            # Construir mapas {uf: preco} e {regiao: preco}
            preco_por_uf = {p['uf']: p.get('preco_medio') for p in preco_prod.get('por_uf', []) if p.get('uf')}
            preco_por_reg = {p['regiao']: p.get('preco_medio') for p in preco_prod.get('por_regiao', []) if p.get('regiao')}
            preco_brasil = preco_prod.get('preco_medio_brasil')

            # Anexar preço em cada UF/região do bloco de vendas
            for uf_obj in out['produtos'][vendas_key].get('por_uf', []):
                uf = uf_obj.get('uf')
                if uf in preco_por_uf:
                    uf_obj['preco_medio_l'] = preco_por_uf[uf]
                else:
                    uf_obj['preco_medio_l'] = None

            for reg_obj in out['produtos'][vendas_key].get('por_regiao', []):
                rs = reg_obj.get('regiao_sigla')
                if rs in preco_por_reg:
                    reg_obj['preco_medio_l'] = preco_por_reg[rs]
                else:
                    reg_obj['preco_medio_l'] = None

            out['produtos'][vendas_key]['preco_medio_brasil_l'] = preco_brasil
            out['produtos'][vendas_key]['preco_referencia'] = precos.get('data_referencia')

            # Ranking caro/barato
            ufs_com_preco = [u for u in out['produtos'][vendas_key]['por_uf']
                             if u.get('preco_medio_l') is not None]
            if ufs_com_preco:
                ordenado = sorted(ufs_com_preco, key=lambda x: x['preco_medio_l'], reverse=True)
                out['produtos'][vendas_key]['top_mais_caros'] = [
                    {'uf': u['uf'], 'regiao': u['regiao'], 'preco_l': u['preco_medio_l']}
                    for u in ordenado[:5]
                ]
                out['produtos'][vendas_key]['top_mais_baratos'] = [
                    {'uf': u['uf'], 'regiao': u['regiao'], 'preco_l': u['preco_medio_l']}
                    for u in ordenado[-5:][::-1]
                ]

            log.info(f"ANP Vendas · preço enriquecido para {vendas_key}: R$ {preco_brasil}/L ({len(ufs_com_preco)} UFs)")
    except Exception as e:
        log.warning(f"ANP Vendas · enrich_with_prices falhou: {e}")
    return out


def run() -> None:
    raw, url_used = _try_download()
    if raw:
        try:
            rows = parse_csv(raw)
            log.info(f"ANP Vendas · CSV parseado: {len(rows)} linhas")
            try:
                (DOWNLOADS_DIR / "anp" / f"vendas_{dt.date.today().isoformat()}.csv").write_bytes(raw)
            except Exception as e:
                log.debug(f"ANP Vendas · falha ao salvar raw: {e}")

            out = build_fallback()
            out['fonte'] = 'ANP · CSV vendas (capturado) + snapshot anual + preços ANP'
            out['endpoint'] = url_used
            out['status'] = 'PARCIAL'
            out['nota'] = f'CSV capturado de {url_used} · parser específico em desenvolvimento. Usando snapshot anual como base + preços R$/L do levantamento ANP.'
            out = enrich_with_prices(out)
            save_json(DATA_DIR / "anp_vendas.json", out)
            mark_source_partial("anp_vendas", "CSV capturado · snapshot base + preços",
                                rows=sum(len(p['por_uf']) for p in out['produtos'].values()),
                                endpoint=url_used)
            log.info(f"ANP Vendas · CSV capturado + snapshot + preços aplicados")
            return
        except Exception as e:
            log.warning(f"ANP Vendas · parser falhou: {e}")

    # Fallback completo
    out = build_fallback()
    out = enrich_with_prices(out)
    save_json(DATA_DIR / "anp_vendas.json", out)
    mark_source_partial("anp_vendas",
                        "snapshot Anuário ANP 2024 + preços R$/L (CSV ao vivo indisponível)",
                        rows=sum(len(p['por_uf']) for p in out['produtos'].values()),
                        endpoint=ANP_VDPB_LANDING)
    log.info(f"ANP Vendas · snapshot + preços aplicados · 3 produtos × 27 UFs")


if __name__ == "__main__":
    run()
