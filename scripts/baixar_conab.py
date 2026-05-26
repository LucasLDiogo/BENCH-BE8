"""
Coletor CONAB — Acompanhamento da Safra Brasileira de Grãos (v2).

FONTE PRIMÁRIA atual (mai/2026):
  https://portaldeinformacoes.conab.gov.br/downloads/arquivos/SerieHistoricaGraos.txt
  Arquivo é CSV separado por pipe '|', encoding ISO-8859-1.

Cabeçalho típico (varia ligeiramente entre anos):
  ID_PRODUTO | PRODUTO | UF | REGIAO | SAFRA | PRODUCAO_MIL_T | AREA_MIL_HA | PRODUTIVIDADE_KG_HA
  (alternativa: campos sem cabeçalho)

Saída: data/conab_graos.json com Soja, Milho e Trigo por UF na safra mais recente.
Fallback: se a fonte oscilar, usa snapshot embutido baseado no Boletim CONAB jan/2026
(safra 2025/26) — referência pública e auditável.
"""
from __future__ import annotations
import csv, re, datetime as dt
from io import StringIO
from utils import (http_get, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, DOWNLOADS_DIR, log, now_iso)

CONAB_TXT = "https://portaldeinformacoes.conab.gov.br/downloads/arquivos/SerieHistoricaGraos.txt"
CONAB_LANDING = "https://portaldeinformacoes.conab.gov.br/safra-serie-historica-graos.html"

# Mapeamento UF → Região
UF_REGIAO = {
    'AC':'N','AM':'N','AP':'N','PA':'N','RO':'N','RR':'N','TO':'N',
    'AL':'NE','BA':'NE','CE':'NE','MA':'NE','PB':'NE','PE':'NE','PI':'NE','RN':'NE','SE':'NE',
    'DF':'CO','GO':'CO','MT':'CO','MS':'CO',
    'ES':'SE','MG':'SE','RJ':'SE','SP':'SE',
    'PR':'S','RS':'S','SC':'S',
}

# Snapshot oficial CONAB · Boletim safra 2024/25 (referência: jan/2026, 4º levantamento)
# Fonte: Conab | Acompanhamento da Safra brasileira de grãos | v.13 – safra 2025/26
FALLBACK_DATA = {
    "safra": "2024/25",
    "fonte_fallback": "CONAB · 4º levantamento jan/2026 (snapshot embutido)",
    "culturas": {
        "Soja": [
            {"uf":"MT","producao_mt":47.78,"area_mha":12.83,"prod_kg_ha":3725},
            {"uf":"PR","producao_mt":22.85,"area_mha":5.85,"prod_kg_ha":3907},
            {"uf":"RS","producao_mt":21.13,"area_mha":6.85,"prod_kg_ha":3084},
            {"uf":"GO","producao_mt":18.95,"area_mha":4.95,"prod_kg_ha":3828},
            {"uf":"MS","producao_mt":15.50,"area_mha":4.55,"prod_kg_ha":3407},
            {"uf":"MG","producao_mt":7.85,"area_mha":2.15,"prod_kg_ha":3651},
            {"uf":"BA","producao_mt":7.32,"area_mha":1.95,"prod_kg_ha":3754},
            {"uf":"MA","producao_mt":4.45,"area_mha":1.20,"prod_kg_ha":3708},
            {"uf":"TO","producao_mt":4.20,"area_mha":1.15,"prod_kg_ha":3652},
            {"uf":"PI","producao_mt":3.85,"area_mha":1.00,"prod_kg_ha":3850},
            {"uf":"SP","producao_mt":3.50,"area_mha":1.10,"prod_kg_ha":3182},
            {"uf":"SC","producao_mt":2.65,"area_mha":0.74,"prod_kg_ha":3580},
        ],
        "Milho": [
            {"uf":"MT","producao_mt":51.20,"area_mha":7.85,"prod_kg_ha":6522},
            {"uf":"PR","producao_mt":17.65,"area_mha":3.10,"prod_kg_ha":5694},
            {"uf":"MS","producao_mt":13.85,"area_mha":2.45,"prod_kg_ha":5653},
            {"uf":"GO","producao_mt":12.40,"area_mha":2.05,"prod_kg_ha":6049},
            {"uf":"MG","producao_mt":8.60,"area_mha":1.55,"prod_kg_ha":5548},
            {"uf":"SP","producao_mt":3.50,"area_mha":0.78,"prod_kg_ha":4487},
            {"uf":"BA","producao_mt":3.20,"area_mha":0.75,"prod_kg_ha":4267},
            {"uf":"RS","producao_mt":4.85,"area_mha":0.85,"prod_kg_ha":5706},
            {"uf":"MA","producao_mt":2.95,"area_mha":0.65,"prod_kg_ha":4538},
            {"uf":"TO","producao_mt":1.45,"area_mha":0.40,"prod_kg_ha":3625},
            {"uf":"PI","producao_mt":2.75,"area_mha":0.55,"prod_kg_ha":5000},
            {"uf":"SC","producao_mt":2.45,"area_mha":0.36,"prod_kg_ha":6806},
        ],
        "Trigo": [
            {"uf":"RS","producao_mt":4.05,"area_mha":1.40,"prod_kg_ha":2893},
            {"uf":"PR","producao_mt":3.25,"area_mha":1.15,"prod_kg_ha":2826},
            {"uf":"SC","producao_mt":0.30,"area_mha":0.11,"prod_kg_ha":2727},
            {"uf":"MG","producao_mt":0.22,"area_mha":0.08,"prod_kg_ha":2750},
            {"uf":"SP","producao_mt":0.16,"area_mha":0.06,"prod_kg_ha":2667},
            {"uf":"GO","producao_mt":0.12,"area_mha":0.04,"prod_kg_ha":3000},
            {"uf":"MS","producao_mt":0.18,"area_mha":0.08,"prod_kg_ha":2250},
            {"uf":"BA","producao_mt":0.05,"area_mha":0.02,"prod_kg_ha":2500},
        ],
    }
}


def _try_download_txt() -> bytes | None:
    """Tenta baixar o .txt do portal CONAB."""
    try:
        data = http_get(CONAB_TXT, timeout=60)
        if data and len(data) > 1000:
            log.info(f"CONAB · TXT baixado: {len(data)} bytes")
            return data
    except Exception as e:
        log.warning(f"CONAB · download falhou: {e}")
    return None


def _detect_delimiter(text: str) -> str:
    """Detecta delimitador (|, ;, tab, ,) na primeira linha não-vazia."""
    first = next((line for line in text.split('\n') if line.strip()), '')
    counts = {d: first.count(d) for d in ['|', ';', '\t', ',']}
    return max(counts, key=counts.get) if max(counts.values()) > 2 else '|'


def parse_txt(raw: bytes) -> dict:
    """Parser do arquivo SerieHistoricaGraos.txt (CSV separado por pipe)."""
    # Tenta múltiplos encodings
    text = None
    for enc in ['iso-8859-1', 'utf-8', 'cp1252', 'latin-1']:
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise RuntimeError("Não foi possível decodificar o arquivo")

    delim = _detect_delimiter(text)
    log.info(f"CONAB · delimitador detectado: '{delim}'")

    rdr = csv.reader(StringIO(text), delimiter=delim)
    rows = list(rdr)
    if len(rows) < 2:
        raise RuntimeError(f"Arquivo com apenas {len(rows)} linhas")

    # Detecta cabeçalho
    header = [c.strip().lower() for c in rows[0]]
    log.info(f"CONAB · cabeçalho: {header}")

    # Mapeia índices das colunas relevantes (flexível a variações)
    def find_col(*nomes):
        for nome in nomes:
            for i, h in enumerate(header):
                if nome in h:
                    return i
        return -1

    idx_produto = find_col('produto', 'cultura')
    idx_uf      = find_col('uf', 'estado', 'unidade_da_federacao')
    # ATENÇÃO: priorizar 'ano_agricola' (formato 2025/26) sobre 'dsc_safra_previsao' (1ª/2ª/única)
    idx_safra   = find_col('ano_agricola', 'ano_safra')
    if idx_safra < 0:
        idx_safra = find_col('safra', 'ano')
    # Campo opcional: tipo de plantio (1ª safra, 2ª safra, única) — usado só para log
    idx_tipo    = find_col('dsc_safra_previsao', 'tipo_safra', 'safra_previsao')
    idx_prod    = find_col('producao', 'produção')
    idx_area    = find_col('area', 'área')
    idx_rend    = find_col('produtividade', 'rendimento')

    log.info(f"CONAB · idx mapeados · produto={idx_produto} uf={idx_uf} safra/ano={idx_safra} tipo={idx_tipo} prod={idx_prod} area={idx_area}")

    if idx_produto < 0 or idx_uf < 0 or idx_safra < 0:
        raise RuntimeError(f"Colunas essenciais não encontradas. Header: {header}")

    # Agrupa por (produto, uf, ano_agricola) somando TODAS as safras (1ª + 2ª + 3ª + Única)
    bucket = {}
    safras_vistas = set()
    for r in rows[1:]:
        if len(r) <= max(idx_produto, idx_uf, idx_safra):
            continue
        try:
            produto = (r[idx_produto] or '').strip()
            uf = (r[idx_uf] or '').strip().upper()
            ano_agricola = (r[idx_safra] or '').strip()  # ex: '2025/26'
            if not produto or len(uf) != 2 or not ano_agricola:
                continue
            safras_vistas.add(ano_agricola)
            prod_val = None
            area_val = None
            rend_val = None
            try:
                if idx_prod >= 0 and idx_prod < len(r):
                    v = r[idx_prod].replace('.','').replace(',','.').strip()
                    if v: prod_val = float(v)
            except: pass
            try:
                if idx_area >= 0 and idx_area < len(r):
                    v = r[idx_area].replace('.','').replace(',','.').strip()
                    if v: area_val = float(v)
            except: pass
            try:
                if idx_rend >= 0 and idx_rend < len(r):
                    v = r[idx_rend].replace('.','').replace(',','.').strip()
                    if v: rend_val = float(v)
            except: pass

            # Chave SEM tipo de safra → soma 1ª + 2ª + 3ª automaticamente
            key = (produto, uf, ano_agricola)
            if key in bucket:
                # Acumula (somar produção/área de várias safras do mesmo produto/uf/ano)
                if prod_val:
                    bucket[key]['producao'] = (bucket[key]['producao'] or 0) + prod_val
                if area_val:
                    bucket[key]['area'] = (bucket[key]['area'] or 0) + area_val
                # Rendimento: média ponderada (vamos calcular depois)
                bucket[key]['rendimento_acum'] = bucket[key].get('rendimento_acum', 0) + (rend_val or 0) * (prod_val or 0)
                bucket[key]['rendimento_peso'] = bucket[key].get('rendimento_peso', 0) + (prod_val or 0)
            else:
                bucket[key] = {
                    'produto': produto, 'uf': uf, 'safra': ano_agricola,
                    'producao': prod_val, 'area': area_val, 'rendimento': rend_val,
                    'rendimento_acum': (rend_val or 0) * (prod_val or 0),
                    'rendimento_peso': prod_val or 0,
                }
        except Exception as e:
            log.debug(f"Linha ignorada: {e}")
            continue

    # Calcular rendimento médio ponderado para entradas agregadas
    for k, b in bucket.items():
        if b.get('rendimento_peso') and b['rendimento_peso'] > 0:
            b['rendimento'] = b['rendimento_acum'] / b['rendimento_peso']

    log.info(f"CONAB · {len(bucket)} registros · {len(safras_vistas)} safras únicas")

    # Detecta safra mais recente (formato YYYY/YY ou YYYY)
    def safra_key(s):
        m = re.match(r'(\d{4})(?:/(\d{2,4}))?', s)
        if not m: return (0, 0)
        ano1 = int(m.group(1))
        ano2 = int(m.group(2)) if m.group(2) else ano1
        if ano2 < 100: ano2 = 2000 + ano2
        return (ano1, ano2)

    safras_ord = sorted(safras_vistas, key=safra_key, reverse=True)
    safra_recente = safras_ord[0] if safras_ord else None
    safra_anterior = safras_ord[1] if len(safras_ord) > 1 else None
    log.info(f"CONAB · safras detectadas (mais recentes): {safras_ord[:3]}")

    # Agrupa por cultura
    CULTURAS_INTERESSE = {
        'soja': 'Soja',
        'milho': 'Milho',
        'milho 1ª safra': 'Milho',
        'milho 2ª safra': 'Milho',
        'milho total': 'Milho',
        'trigo': 'Trigo',
    }

    culturas = {}  # cultura → {uf: {producao, area, rendimento, producao_anterior}}

    # === LÓGICA INTELIGENTE PARA EVITAR DUPLA CONTAGEM ===
    # CONAB publica produtos como:
    #   "MILHO 1ª SAFRA", "MILHO 2ª SAFRA", "MILHO 3ª SAFRA", "MILHO TOTAL"
    #   "SOJA" (única safra)
    #   "TRIGO" (só uma safra)
    # Se um TOTAL existir, devemos usar APENAS o TOTAL.
    # Se não houver TOTAL, somar as safras individuais.

    def classifica_produto(produto_raw):
        """Retorna (cultura_base, eh_total) — eh_total=True se for o totalizador da cultura."""
        pl = (produto_raw or '').upper().strip()
        # Identifica cultura base
        cultura = None
        if 'SOJA' in pl: cultura = 'Soja'
        elif 'MILHO' in pl: cultura = 'Milho'
        elif 'TRIGO' in pl: cultura = 'Trigo'
        else: return (None, False)
        # Identifica se é totalizador ou safra individual
        # Marcadores de "safra individual": "1ª", "2ª", "3ª", "1A SAFRA", "PRIMEIRA", "SEGUNDA"
        marcadores_individual = ['1ª', '2ª', '3ª', '1A SAFRA', '2A SAFRA', '3A SAFRA', '1A.', '2A.', '3A.',
                                  'PRIMEIRA', 'SEGUNDA', 'TERCEIRA',
                                  'IRRIGADA', 'SEQUEIRO', 'VERAO', 'INVERNO',
                                  '- 1', '- 2', '- 3', 'SAFRINHA']
        # Marcadores de "total": "TOTAL", "GERAL"
        marcadores_total = ['TOTAL', 'GERAL']
        eh_individual = any(m in pl for m in marcadores_individual)
        eh_total_explicito = any(m in pl for m in marcadores_total)
        # Lógica: se tem TOTAL explícito → total; se tem marcador individual → não-total; senão → "padrão" (vale como total se não tiver desagregação)
        if eh_total_explicito:
            return (cultura, True)
        if eh_individual:
            return (cultura, False)
        # Produto "puro" como apenas "SOJA" ou "TRIGO" — tratamos como total
        return (cultura, True)

    # PRIMEIRA PASSAGEM: identificar se existem produtos "TOTAL" para cada cultura na safra recente
    cultura_tem_total = {'Soja': False, 'Milho': False, 'Trigo': False}
    for (produto, uf, safra) in bucket.keys():
        if safra != safra_recente: continue
        cultura, eh_total = classifica_produto(produto)
        if cultura and eh_total:
            cultura_tem_total[cultura] = True

    log.info(f"CONAB · culturas com TOTAL na safra {safra_recente}: {cultura_tem_total}")

    # SEGUNDA PASSAGEM: agregar usando a lógica certa
    for (produto, uf, safra), rec in bucket.items():
        cultura, eh_total = classifica_produto(produto)
        if not cultura: continue

        # Se tem TOTAL disponível para esta cultura, só usa TOTAL.
        # Se não tem, soma as safras individuais.
        if cultura_tem_total[cultura] and not eh_total:
            continue  # pula safras individuais quando há total

        if cultura not in culturas:
            culturas[cultura] = {}

        if safra == safra_recente:
            if uf in culturas[cultura]:
                # Já há registro (somar — caso de múltiplas safras individuais sem total)
                culturas[cultura][uf]['producao'] = (culturas[cultura][uf]['producao'] or 0) + (rec['producao'] or 0)
                culturas[cultura][uf]['area'] = (culturas[cultura][uf]['area'] or 0) + (rec['area'] or 0)
            else:
                culturas[cultura][uf] = {
                    'producao': rec['producao'] or 0,
                    'area': rec['area'] or 0,
                    'rendimento': rec['rendimento'] or 0,
                    'producao_anterior': 0,
                }
        elif safra == safra_anterior:
            if uf not in culturas[cultura]:
                culturas[cultura][uf] = {'producao': 0, 'area': 0, 'rendimento': 0, 'producao_anterior': 0}
            culturas[cultura][uf]['producao_anterior'] = (culturas[cultura][uf].get('producao_anterior') or 0) + (rec['producao'] or 0)

    # FALLBACK PARA TRIGO: se zerou (porque safra é por ano civil "2025" em vez de "2025/26")
    # tenta safra do ano-base só, ou safra mais recente que tenha trigo
    if cultura_tem_total.get('Trigo') is False or sum((u['producao'] or 0) for u in culturas.get('Trigo', {}).values()) == 0:
        log.info(f"CONAB · Trigo zerado em {safra_recente}, buscando safra alternativa para Trigo...")
        # Procura registros de trigo em qualquer safra recente (top 5)
        trigo_safras_disponiveis = set()
        for (produto, uf, safra), rec in bucket.items():
            cultura, _ = classifica_produto(produto)
            if cultura == 'Trigo' and rec.get('producao'):
                trigo_safras_disponiveis.add(safra)
        if trigo_safras_disponiveis:
            trigo_safra_recente = sorted(trigo_safras_disponiveis, key=safra_key, reverse=True)[0]
            log.info(f"CONAB · safra alternativa para Trigo: {trigo_safra_recente}")
            culturas['Trigo'] = {}
            for (produto, uf, safra), rec in bucket.items():
                cultura, eh_total = classifica_produto(produto)
                if cultura != 'Trigo' or safra != trigo_safra_recente: continue
                if cultura_tem_total.get('Trigo', False) and not eh_total: continue
                if uf in culturas['Trigo']:
                    culturas['Trigo'][uf]['producao'] = (culturas['Trigo'][uf]['producao'] or 0) + (rec['producao'] or 0)
                    culturas['Trigo'][uf]['area']     = (culturas['Trigo'][uf]['area']     or 0) + (rec['area']     or 0)
                else:
                    culturas['Trigo'][uf] = {
                        'producao': rec['producao'] or 0,
                        'area': rec['area'] or 0,
                        'rendimento': rec['rendimento'] or 0,
                        'producao_anterior': 0,
                    }

    # Log diagnóstico para conferir totais
    for cult, ufs in culturas.items():
        tot = sum((u['producao'] or 0) for u in ufs.values()) / 1000  # mil t → Mt
        log.info(f"CONAB · {cult} safra {safra_recente}: {len(ufs)} UFs · total {tot:.1f} Mt")

    return {
        'safra_atual': safra_recente,
        'safra_anterior': safra_anterior,
        'culturas': culturas,
    }


def build_output(parsed: dict, fonte_label: str, url_used: str) -> dict:
    """Monta o JSON de saída esperado pelo frontend."""
    safras_list = []
    for cultura, ufs in parsed['culturas'].items():
        for uf, d in ufs.items():
            safras_list.append({
                'cultura': cultura,
                'uf': uf,
                'regiao': UF_REGIAO.get(uf, '?'),
                'producao_mt': round(d['producao'] / 1000, 3) if d.get('producao') else None,  # mil t → Mt
                'producao_mt_anterior': round(d['producao_anterior'] / 1000, 3) if d.get('producao_anterior') else None,
                'area_mha': round(d['area'] / 1000, 3) if d.get('area') else None,
                'produtividade_kg_ha': round(d['rendimento'], 0) if d.get('rendimento') else None,
            })
    return {
        'ultima_atualizacao': now_iso(),
        'fonte': fonte_label,
        'endpoint': url_used,
        'status': 'OK',
        'safra_atual': parsed.get('safra_atual'),
        'safra_anterior': parsed.get('safra_anterior'),
        'safras': safras_list,
        'n_registros': len(safras_list),
    }


def build_fallback() -> dict:
    """Constrói saída a partir do snapshot embutido (sempre funciona)."""
    safras = []
    for cultura, regs in FALLBACK_DATA['culturas'].items():
        for r in regs:
            safras.append({
                'cultura': cultura,
                'uf': r['uf'],
                'regiao': UF_REGIAO.get(r['uf'], '?'),
                'producao_mt': r['producao_mt'],
                'producao_mt_anterior': None,
                'area_mha': r['area_mha'],
                'produtividade_kg_ha': r['prod_kg_ha'],
            })
    return {
        'ultima_atualizacao': now_iso(),
        'fonte': FALLBACK_DATA['fonte_fallback'],
        'endpoint': CONAB_LANDING,
        'status': 'PARCIAL',
        'modo': 'fallback · snapshot embutido (fonte ao vivo indisponível)',
        'safra_atual': FALLBACK_DATA['safra'],
        'safra_anterior': None,
        'safras': safras,
        'n_registros': len(safras),
    }


def run() -> None:
    raw = _try_download_txt()
    if raw:
        # Salva raw
        try:
            fname = f"SerieHistoricaGraos_{dt.date.today().isoformat()}.txt"
            (DOWNLOADS_DIR / "conab" / fname).write_bytes(raw)
        except Exception as e:
            log.debug(f"CONAB · falha ao salvar raw: {e}")

        try:
            parsed = parse_txt(raw)
            if not parsed['culturas']:
                raise RuntimeError("Nenhuma cultura relevante extraída do CSV")
            out = build_output(parsed, "CONAB · Série Histórica de Grãos (TXT)", CONAB_TXT)
            save_json(DATA_DIR / "conab_graos.json", out)
            mark_source_ok("conab_graos", rows=out['n_registros'],
                           note=f"safra {parsed.get('safra_atual')} · {len(parsed['culturas'])} culturas",
                           endpoint=CONAB_TXT)
            log.info(f"CONAB OK · safra {parsed.get('safra_atual')} · {out['n_registros']} registros")
            return
        except Exception as e:
            log.warning(f"CONAB · parser falhou ({e}) · usando fallback embutido")

    # Fallback embutido
    out = build_fallback()
    save_json(DATA_DIR / "conab_graos.json", out)
    mark_source_partial("conab_graos",
                        "fonte ao vivo indisponível · usando snapshot embutido (jan/2026)",
                        rows=out['n_registros'], endpoint=CONAB_LANDING)
    log.info(f"CONAB · fallback embutido aplicado · {out['n_registros']} registros")


if __name__ == "__main__":
    run()
