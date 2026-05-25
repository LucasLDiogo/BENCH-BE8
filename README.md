# Be8 · Market Intelligence Platform

Plataforma executiva de inteligência de mercado para o setor de biodiesel, grãos e commodities. Arquivo único `index.html` + logo SVG, sem build, sem dependências instaladas. Roda em qualquer browser moderno.

---

## ✅ O QUE JÁ ESTÁ ATIVO (atualização automática diária)

Quando o usuário abre o painel, ele faz fetch em tempo real das seguintes fontes:

| Fonte | API | O que entrega |
|---|---|---|
| **Banco Central (BCB) PTAX** | `olinda.bcb.gov.br/olinda/servico/PTAX/v1` | USD e EUR — cotação de fechamento + série de 90 dias |
| **Yahoo Finance** (via `corsproxy.io`) | `query1.finance.yahoo.com/v8/finance/chart` | Brent, WTI, Soja, Milho, Trigo, Óleo de Soja, Farelo, Gás Natural |
| **ComexStat MDIC** | `api-comexstat.mdic.gov.br/general` | Exportação/importação por NCM (diesel, óleo soja, biodiesel, farelo, metanol) |

Tudo gratuito, sem chave de API. O painel se reabre todo dia e puxa os dados frescos sozinho.

---

## 🚀 COMO HOSPEDAR PARA O PAINEL RODAR TODO DIA

### Opção A · GitHub Pages (recomendado, 100% gratuito)

1. Crie um repositório privado no GitHub Be8 (`be8-market-intel`)
2. Faça upload de `index.html` e `logo-be8.svg`
3. Vá em **Settings → Pages → Source: main branch**
4. Em 1 minuto sua URL fica `https://<org-be8>.github.io/be8-market-intel/`
5. Pronto — todo executivo que abre o link vê os dados atualizados em tempo real

### Opção B · Servidor interno Be8

Se preferir hospedar dentro da rede:
- Coloque os 2 arquivos em qualquer servidor web (IIS, Nginx, Apache, Sharepoint)
- Não precisa de servidor de aplicação, banco de dados ou backend
- Pode rodar inclusive dentro de um SharePoint corporativo

### Opção C · Distribuir como `.html` por email

Funciona até por anexo de email — o arquivo é autocontido. Cada vez que o destinatário abrir, busca os dados ao vivo.

---

## 📡 MAPA DE FONTES — Quais funcionam, custos e roadmap

### 🟢 LIVE — funcionando agora, gratuitas

| Fonte | Custo | Atualização | Como acessa |
|---|---|---|---|
| BCB PTAX (câmbio) | Grátis | Diária 4x | API REST OData JSON · CORS aberto |
| Yahoo Finance (Brent/WTI/grãos CBOT) | Grátis | 15min delay | Via corsproxy.io (free) |
| ComexStat (export/import) | Grátis | Mensal | API REST oficial MDIC |
| AwesomeAPI (câmbio backup) | Grátis | Tempo real | API REST sem chave |

### 🟡 PIPELINE PENDENTE — gratuitas, mas precisam de Power Query/scraper diário

| Fonte | O que entrega | Como integrar |
|---|---|---|
| **ANP — Preços de revenda combustíveis** | Diesel S10/S500, Gasolina, Etanol, GLP por UF, semanal | Power Query baixa CSV em `gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis` toda 6ª-feira |
| **ANP — Produção B100 mensal** | Volume produzido por planta, por UF | Planilha XLS em `gov.br/anp/dados-estatisticos`. Python/Power Query agendado mensal |
| **ANP — Anuário Estatístico** | Capacidade instalada, matérias-primas, share por produtor | CSV anual em `gov.br/anp`, atualização anual |
| **CONAB — Safra grãos** | Produção, área plantada, produtividade soja/milho/trigo por UF | Tabela CSV em `portaldeinformacoes.conab.gov.br/safra-serie-historica-graos.html` — mensal |
| **IBGE/SIDRA** | LSPA (Levantamento Sistemático da Produção Agrícola) | API REST `apisidra.ibge.gov.br` — tabelas 1612, 6588 |
| **USDA FAS PSD** | Produção mundial soja/milho/trigo, comparativo Brasil × mundo | API REST `apps.fas.usda.gov/OpenData/api/psd` — gratuita |
| **FRED St. Louis Fed** | Estoques diesel EUA, séries macro globais | API REST `api.stlouisfed.org/fred` — chave grátis (5 min) |
| **EIA Energy Info** | Petróleo, estoques, refino global | API REST `api.eia.gov` — chave grátis |

### 🔴 PENDENTE — gratuitas, mas sem API direta (scraping ou widget)

| Fonte | Realidade | Caminho |
|---|---|---|
| **CEPEA/ESALQ** (soja, milho, trigo R$/sc) | Tem widget HTML institucional mas **não tem API REST aberta**. Cotações são propriedade intelectual do CEPEA | (a) Embed do widget oficial `cepea.org.br/br/widget.aspx` em iframe; (b) Scraping autorizado da página pública com cache; (c) Contrato comercial com Cepea/ESALQ para dados estruturados |
| **SIFRECA / ESALQ-LOG** (frete) | PDF mensal | Download programado + parser tabula-py |
| **ANTT — Piso mínimo frete** | XLS no site | Scraper Power Automate |
| **ABIOVE — Esmagamento soja** | PDF mensal | Download programado + parser |
| **EPE — Projeções energia** | PDF anual + relatórios trimestrais | Download manual + extração |
| **Petrobras — Preço refinaria** | PDF semanal | Scraper open-source existe (`github.com/royopa/petrobras-scraper`) |
| **B3 — CBIO** | Dados via cadastro B3 | Cadastro institucional Be8 |

### 💰 OPCIONAIS PAGAS (se quiser cobertura premium)

- **Trading Economics** — calendário macro global (~US$ 75/mês)
- **Refinitiv/LSEG** — cotações profissionais soja/milho intraday (US$ 600+/mês)
- **S&P Global Platts** — preços diesel internacional, biodiesel europeu
- **Argus Media** — biocombustíveis globais

Honestamente: **para 90% do uso decisório, as gratuitas + pipeline diário cobrem tudo**. Pagas só fazem sentido se Be8 quiser fazer trading ativo de futuros.

---

## 🏗 ARQUITETURA RECOMENDADA — Bloomberg interna Be8

```
┌──────────────────────────────────────────────────────────────────┐
│  CAMADA 1 — INGESTÃO (Power Automate · Python · Power Query)     │
│  ├─ APIs REST (BCB, ComexStat, Yahoo, FRED, IBGE, USDA)          │
│  ├─ CSV download agendado (ANP, MDIC bulk)                       │
│  ├─ PDF/XLS scrapers (CONAB, ABIOVE, Petrobras)                  │
│  └─ HTML scrapers autorizados (CEPEA widget)                     │
│         ↓                                                        │
│  CAMADA 2 — DATA LAKE (Azure Data Lake Gen2 ou OneDrive Be8)     │
│  ├─ /raw/{fonte}/{ano}/{mes}/                                    │
│  ├─ /staged/ (parquet limpo)                                     │
│  └─ /curated/ (modelo estrela)                                   │
│         ↓                                                        │
│  CAMADA 3 — SEMÂNTICA (Power BI Dataset · DAX)                   │
│  ├─ dim_data, dim_produto, dim_uf, dim_produtor                  │
│  ├─ fato_cambio, fato_commodities, fato_b100, fato_comex         │
│  └─ _Medidas (Cotação Atual, Market Share, YoY, CAGR…)           │
│         ↓                                                        │
│  CAMADA 4 — APRESENTAÇÃO                                         │
│  ├─ Power BI Service (relatórios operacionais)                   │
│  ├─ Este HTML (cockpit executivo · Bloomberg Be8)                │
│  └─ Mobile app (radar push notifications)                        │
│         ↓                                                        │
│  CAMADA 5 — DECISÃO                                              │
│  ├─ Radar IA (regras + LLM via Anthropic API)                    │
│  ├─ Alertas Slack/Email automáticos                              │
│  └─ Snapshot PDF diretoria/conselho                              │
└──────────────────────────────────────────────────────────────────┘
```

---

## 📅 ROADMAP DE EVOLUÇÃO

### Sprint 1 — esta entrega ✅
- Cockpit HTML standalone com câmbio + commodities + comex ao vivo
- Identidade visual Be8
- Radar IA com 5 regras determinísticas
- Governança transparente de fontes

### Sprint 2 — pipeline diário (1-2 semanas)
- Power Query M para ANP preços combustíveis (semanal)
- Scraper CONAB safras (mensal)
- API SIDRA IBGE
- Cadastro chave FRED + EIA

### Sprint 3 — Power BI integrado (3-4 semanas)
- Modelo estrela completo
- DAX measures (Market Share, YoY, CAGR, etc.)
- Refresh agendado dataset
- Embed do Power BI no HTML via REST API

### Sprint 4 — IA avançada (1-2 meses)
- Integração Anthropic API (Claude) para resumos executivos automáticos
- Modelos preditivos B100 (ML)
- Alertas Slack/Email
- Snapshot PDF semanal automatizado

---

## 🔐 OBSERVAÇÕES IMPORTANTES

**Sobre o corsproxy.io (commodities Yahoo):**
- Funciona, é gratuito e amplamente usado, mas é serviço externo
- Para produção corporativa Be8, recomenda-se **criar próprio proxy interno** (Cloudflare Worker, Azure Function ou Lambda) — 100% controlado, sem dependência de terceiros, sem rate limits

**Sobre dados pendentes:**
- O painel **nunca inventa números**. Quando uma fonte está pendente, aparece "Pipeline pendente" ou "Aguardando integração" com transparência total na página Governança
- Conforme suas próprias diretrizes (NÃO inventar dados)

**Sobre o "atualiza todo dia":**
- O HTML não precisa ser rebuildado/regenerado todo dia
- Ele puxa dados frescos a cada abertura do browser
- Tem auto-refresh às 11h e 16h BRT (após fechamento PTAX e meio do pregão)
- Para forçar atualização: botão "↻ Atualizar dados" no canto superior

---

## 🎨 IDENTIDADE VISUAL APLICADA

Extraída do logo oficial Be8:
- **Base institucional:** `#081f2e` (azul-marinho profundo)
- **Gradiente energia:** `#0eb194` → `#55c94f` (verde-água → verde-folha)
- **Tipografia executiva:** Fraunces (editorial display) + Inter Tight (UI) + JetBrains Mono (dados técnicos)

Inspirações: Bloomberg Terminal, terminal Reuters, dashboards McKinsey, design system Apple/Tesla.
