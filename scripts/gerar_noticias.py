"""
Gerador de Notícias — Newsletter Executiva Be8.
Coleta RSS públicos relacionados a biocombustíveis, agro, combustíveis, commodities.
Classifica por categoria/impacto. NÃO depende de scraping intrusivo — só RSS.

Fontes RSS públicas (todas gratuitas, sem chave):
  - Agência Brasil · Economia/Agro
  - Canal Rural · feed geral
  - Notícias Agrícolas · feed
  - EPBR · Energia / Biocombustíveis (se disponível)
  - gov.br/anp · feed institucional (se disponível)
  - Reuters Brasil business (limitado a snippet)
Se uma fonte falhar, simplesmente registra status e continua.
"""
from __future__ import annotations
import re, html, datetime as dt
from xml.etree import ElementTree as ET
from utils import (http_get, save_json, mark_source_ok, mark_source_error, mark_source_partial,
                   DATA_DIR, log, now_iso)

# RSS endpoints PÚBLICOS — gratuitos
RSS_SOURCES = [
    {"id": "agencia_brasil_economia",
     "url": "https://agenciabrasil.ebc.com.br/rss/economia/feed.xml",
     "nome": "Agência Brasil · Economia"},
    {"id": "agencia_brasil_geral",
     "url": "https://agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml",
     "nome": "Agência Brasil · Últimas"},
    {"id": "noticias_agricolas",
     "url": "https://www.noticiasagricolas.com.br/rss/noticias",
     "nome": "Notícias Agrícolas"},
    {"id": "canal_rural",
     "url": "https://www.canalrural.com.br/feed/",
     "nome": "Canal Rural"},
    {"id": "epbr_biocombustiveis",
     "url": "https://epbr.com.br/feed/",
     "nome": "EPBR · Energia"},
    {"id": "gov_anp",
     "url": "https://www.gov.br/anp/pt-br/assuntos/noticias/RSS",
     "nome": "ANP · Notícias institucionais"},
]

# Taxonomia: keywords → categoria + impacto Be8
TAXONOMIA = [
    # (keywords, categoria, tag, impacto_pad)
    (["biodiesel", "b100", "mistura"],            "biodiesel",      "core",          "alto"),
    (["renovabio", "cbio", "descarbonização"],    "regulação",      "regulatorio",   "alto"),
    (["soja", "óleo de soja", "oleo de soja", "farelo"], "agro · soja", "insumo",  "alto"),
    (["milho", "etanol de milho"],                "agro · milho",   "insumo",        "médio"),
    (["trigo"],                                   "agro · trigo",   "macro",         "baixo"),
    (["diesel", "petrobras", "refinaria", "abastecimento"], "combustíveis", "macro", "alto"),
    (["dólar", "câmbio", "ptax", "real"],         "câmbio",         "macro",         "médio"),
    (["brent", "petróleo", "wti", "opep"],        "petróleo",       "macro",         "médio"),
    (["safra", "conab", "lavoura", "colheita"],   "safra",          "originação",    "alto"),
    (["exportação", "exportacao", "comex", "porto"], "comércio exterior", "macro",   "médio"),
    (["frete", "logística", "logistica", "antt", "sifreca"], "logística","operacional","médio"),
    (["fertilizante", "ureia", "potássio"],       "fertilizantes",  "macro",         "baixo"),
    (["epe", "mme", "energia renovável", "energia limpa"], "energia", "regulatorio", "médio"),
    (["adm", "bunge", "cargill", "louis dreyfus", "ldc", "amaggi"], "concorrentes", "concorrente", "alto"),
    (["bsbios", "be8"],                           "concorrentes",   "be8-mencao",    "alto"),
]

KEYWORDS_RELEVANTES = [kw for kws, _, _, _ in TAXONOMIA for kw in kws]

def classify(title: str, desc: str) -> tuple[str, str, str]:
    txt = (title + " " + desc).lower()
    for kws, cat, tag, imp in TAXONOMIA:
        if any(k in txt for k in kws):
            return cat, tag, imp
    return "geral", "neutro", "baixo"

def is_relevant(title: str, desc: str) -> bool:
    txt = (title + " " + desc).lower()
    return any(k in txt for k in KEYWORDS_RELEVANTES)

def clean_text(s: str) -> str:
    if not s: return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_rss(raw: bytes) -> list[dict]:
    try:
        # Tenta UTF-8 primeiro
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = raw.decode("latin-1", errors="replace")
    items = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        # Tenta limpar BOM ou prefixo
        text = text.lstrip("\ufeff").lstrip()
        try:
            root = ET.fromstring(text)
        except Exception as e:
            log.warning(f"RSS parse fail: {e}")
            return []

    # RSS 2.0 → channel/item
    for item in root.iter("item"):
        title = clean_text(item.findtext("title", ""))
        link  = clean_text(item.findtext("link", ""))
        desc  = clean_text(item.findtext("description", ""))
        pub   = clean_text(item.findtext("pubDate", ""))
        items.append({"title": title, "link": link, "description": desc, "pub": pub})
    # Atom → entry
    ns_atom = "{http://www.w3.org/2005/Atom}"
    for entry in root.iter(ns_atom + "entry"):
        title = clean_text(entry.findtext(ns_atom + "title", ""))
        link_el = entry.find(ns_atom + "link")
        link = link_el.get("href") if link_el is not None else ""
        desc = clean_text(entry.findtext(ns_atom + "summary", "")
                          or entry.findtext(ns_atom + "content", ""))
        pub = clean_text(entry.findtext(ns_atom + "published", "")
                         or entry.findtext(ns_atom + "updated", ""))
        items.append({"title": title, "link": link, "description": desc, "pub": pub})
    return items

def run() -> None:
    out = {
        "ultima_atualizacao": now_iso(),
        "fonte": "Agregação de feeds RSS públicos",
        "status": "OK",
        "noticias": [],
        "manchete_dia": None,
        "radares": {},
        "fontes_status": [],
    }

    falhas = 0
    total_capturadas = 0
    todas = []

    for src in RSS_SOURCES:
        try:
            raw = http_get(src["url"], timeout=20, retries=2)
            items = parse_rss(raw)
            n_relevantes = 0
            for it in items[:40]:  # limita por fonte
                if not it["title"] or not it["link"]: continue
                if not is_relevant(it["title"], it["description"]): continue
                cat, tag, imp = classify(it["title"], it["description"])
                # Resumo de até 3 linhas (~280 chars)
                resumo = it["description"][:280] + ("…" if len(it["description"]) > 280 else "")
                # Impacto Be8 contextual
                impacto = ""
                if "biodiesel" in cat or "soja" in cat:
                    impacto = "Afeta diretamente preço/originação do B100."
                elif "câmbio" in cat:
                    impacto = "Afeta paridade exportação/importação."
                elif cat == "combustíveis":
                    impacto = "Afeta spread biodiesel × diesel fóssil."
                elif "concorrentes" in cat:
                    impacto = "Movimento competitivo direto."
                else:
                    impacto = "Contexto macro · monitorar."
                todas.append({
                    "titulo": it["title"],
                    "fonte":  src["nome"],
                    "fonte_id": src["id"],
                    "data":   it["pub"],
                    "link":   it["link"],
                    "resumo": resumo,
                    "categoria": cat,
                    "tag":   tag,
                    "impacto_nivel": imp,
                    "impacto_be8":   impacto,
                })
                n_relevantes += 1
            total_capturadas += n_relevantes
            out["fontes_status"].append({"fonte": src["nome"], "id": src["id"],
                                          "status": "OK", "noticias": n_relevantes})
            log.info(f"RSS {src['id']}: {n_relevantes} relevantes / {len(items)} itens")
        except Exception as e:
            log.warning(f"RSS {src['id']} falhou: {e}")
            out["fontes_status"].append({"fonte": src["nome"], "id": src["id"],
                                          "status": "ERRO", "erro": str(e)[:200]})
            falhas += 1

    # Dedupe por título
    vistos = set()
    unicas = []
    for n in todas:
        key = (n["titulo"][:80]).lower()
        if key in vistos: continue
        vistos.add(key)
        unicas.append(n)

    # Ordena: impacto alto primeiro, depois recentes
    impacto_rank = {"alto": 0, "médio": 1, "baixo": 2}
    unicas.sort(key=lambda n: (impacto_rank.get(n["impacto_nivel"], 9), n.get("data", "")))
    unicas = unicas[:40]  # cap total

    out["noticias"] = unicas
    if unicas:
        # Cria manchete principal (prioridade: tag oportunidade > risco > primeiro com impacto alto)
        ranked = sorted(
            unicas,
            key=lambda n: (
                -(2 if n.get("impacto_nivel") == "alto" else 1 if n.get("impacto_nivel") == "médio" else 0),
                -(1 if n.get("tag") in ("core", "regulatorio") else 0),
                n.get("data", "")
            )
        )
        manchete = ranked[0]
        out["manchete"] = manchete
        out["manchete_dia"] = manchete  # compat retroativa
        out["top5"] = ranked[:5]

        # Impacto consolidado e ação recomendada (heurística baseada na mistura de tags)
        alto = sum(1 for n in unicas if n.get("impacto_nivel") == "alto")
        opo  = sum(1 for n in unicas if n.get("tag") == "core")
        reg  = sum(1 for n in unicas if n.get("tag") == "regulatorio")
        out["impacto_consolidado_be8"] = (
            f"A edição de hoje traz {len(unicas)} manchetes setoriais, sendo {alto} de "
            f"alto impacto para a Be8. Destaque para {opo} notícias diretamente relacionadas ao "
            f"biodiesel/B100 e {reg} no eixo regulatório. O fluxo informacional do dia mantém o "
            f"foco em commodities agrícolas, combustíveis e marco normativo — variáveis que "
            f"impactam diretamente custo da matéria-prima, preço de leilão B100 e "
            f"posicionamento competitivo."
        )
        out["acao_recomendada"] = (
            "Monitorar especialmente as manchetes do eixo regulatório (resoluções CNPE/ANP "
            "podem alterar cronograma B15→B20) e acompanhar movimentos da soja CBOT, que "
            "definem a curva de custo do óleo nos próximos 30-60 dias. Considerar antecipar "
            "fixação de compras se houver sinal de alta sustentada."
        )

    # Radares por categoria
    by_cat = {}
    for n in unicas:
        by_cat.setdefault(n["categoria"], []).append(n)
    out["radares"] = {cat: lst[:5] for cat, lst in by_cat.items()}

    if falhas == len(RSS_SOURCES):
        out["status"] = "ERRO"
        mark_source_error("noticias_rss", "Todos os feeds falharam", endpoint="RSS agregado")
    elif falhas:
        out["status"] = "PARCIAL"
        mark_source_partial("noticias_rss", note=f"{falhas} feeds falharam",
                            rows=total_capturadas, endpoint="RSS agregado")
    else:
        mark_source_ok("noticias_rss", rows=total_capturadas,
                       note=f"{len(RSS_SOURCES)} feeds · {len(unicas)} únicas",
                       endpoint="RSS agregado")
    save_json(DATA_DIR / "noticias.json", out)
    log.info(f"Notícias OK · {len(unicas)} únicas de {total_capturadas} capturadas")

if __name__ == "__main__":
    run()
