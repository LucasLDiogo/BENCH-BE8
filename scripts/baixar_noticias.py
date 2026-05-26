"""
BENCH-BE8 · baixar_noticias.py
---------------------------------------------------------------------
Coletor de notícias setoriais via RSS.

Substituto para Investing.com (que tem anti-bot Cloudflare):
  - Notícias Agrícolas (commodities, agro, grãos)
  - Agência Petrobras (energia/combustíveis)
  - Portais públicos institucionais

Saída: data/noticias.json com:
  hero · top5 · radares temáticos (regulatorio/combustiveis/agro/...)
"""
from __future__ import annotations

import re
from datetime import datetime
from xml.etree import ElementTree as ET

from utils import get_logger, http_get, save_json

log = get_logger("baixar_noticias")

# Feeds RSS estáveis · gratuitos · sem anti-bot
FEEDS = [
    {
        "url":  "https://www.noticiasagricolas.com.br/rss/noticias/graos",
        "tema": "agro",
    },
    {
        "url":  "https://www.noticiasagricolas.com.br/rss/noticias/biodiesel",
        "tema": "combustiveis",
    },
    {
        "url":  "https://www.noticiasagricolas.com.br/rss/noticias/economia",
        "tema": "commodities",
    },
    {
        "url":  "https://agenciagov.ebc.com.br/feed-noticias/feed",
        "tema": "regulatorio",
    },
]


def parse_rss(xml_bytes: bytes) -> list[dict]:
    """Parser RSS 2.0 mínimo, defensivo."""
    out = []
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return out
    # RSS 2.0: rss > channel > item
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link  = (item.findtext("link")  or "").strip()
        desc  = (item.findtext("description") or "").strip()
        date  = (item.findtext("pubDate") or "").strip()
        # Limpar HTML do description
        desc_clean = re.sub(r"<[^>]+>", "", desc).strip()
        if title and link:
            out.append({
                "titulo": title,
                "url":    link,
                "resumo": desc_clean[:280],
                "data":   date[:16] if date else "",
            })
    return out


def classificar_tema(titulo: str, default: str) -> str:
    """Reclassifica por keywords no título — supera categoria do RSS."""
    t = titulo.lower()
    if any(k in t for k in ["anp ", "anvisa", "lei ", "decreto", "mp ", "governo"]):
        return "regulatorio"
    if any(k in t for k in ["diesel", "gasolina", "etanol", "combustível", "biodiesel", "petrobras"]):
        return "combustiveis"
    if any(k in t for k in ["soja", "milho", "trigo", "safra", "colheita", "plantio"]):
        return "agro"
    if any(k in t for k in ["dólar", "câmbio", "brent", "petróleo", "wti"]):
        return "commodities"
    if any(k in t for k in ["raízen", "vibra", "be8", "atvos", "ecb", "bsbios"]):
        return "concorrentes"
    if any(k in t for k in ["energia", "eletricidade", "gás", "renovável"]):
        return "energia"
    return default


def main():
    log.info("iniciando · %d feeds", len(FEEDS))
    todas = []
    for feed in FEEDS:
        r = http_get(feed["url"], timeout=15)
        if not r:
            log.warning("feed %s · sem resposta", feed["url"])
            continue
        items = parse_rss(r.content)
        for it in items:
            it["fonte"] = "Notícias Agrícolas" if "noticiasagricolas" in feed["url"] else "Agência Gov"
            it["tag"]   = classificar_tema(it["titulo"], feed["tema"]).upper()
        todas.extend(items)
        log.info("✓ %s · %d itens", feed["url"].split("/")[-1], len(items))

    if not todas:
        save_json("noticias.json", "RSS multifonte", "erro",
                  erro="Nenhum feed retornou itens")
        return 1

    # Top 5 = mais recentes (RSS já vem por data desc)
    top5 = todas[:5]

    # Radares por tema
    radares = {"regulatorio": [], "combustiveis": [], "agro": [],
               "commodities": [], "concorrentes": [], "energia": []}
    for n in todas:
        tema = classificar_tema(n["titulo"], "commodities")
        if tema in radares and len(radares[tema]) < 6:
            radares[tema].append(n)

    hero = {
        "eyebrow":  f"EDIÇÃO DE {datetime.now().strftime('%d/%m/%Y')} · BE8 INTELLIGENCE",
        "headline": top5[0]["titulo"] if top5 else "—",
        "meta":     f"{top5[0]['fonte']} · {top5[0]['data']}" if top5 else "—",
    }

    impacto = (
        "<p>Coleta automatizada de notícias setoriais. "
        "Cruzamento de impacto com indicadores está sendo expandido com modelos LLM. "
        f"Total nesta edição: <strong>{len(todas)} manchetes</strong>.</p>"
    )

    save_json("noticias.json", "RSS multifonte", "ok",
              dados={"hero": hero, "top5": top5, "radares": radares,
                     "impacto_be8": impacto})
    log.info("ok · %d manchetes totais · top5=%d", len(todas), len(top5))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
