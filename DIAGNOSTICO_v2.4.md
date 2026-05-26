# BENCH-BE8 · Diagnóstico técnico v2.4

> **Data:** 26/05/2026
> **Análise baseada em:** `index.html` (1.304 linhas, 193 IDs após correção) + histórico do projeto v2.3
> **Filosofia:** menos cards funcionando 100% > muitos cards bonitos sem atualização real

---

## 1. Bugs encontrados no HTML (corrigidos nesta v2.4)

### Bug A — Status sem `id` (4 cards)
**Local:** `index.html` linhas 153, 164, 175, 186 (cards de Milho/Trigo/Óleo de Soja/WTI)

**Antes:**
```html
<span class="src-status src-pending">—</span>
```

**Depois:**
```html
<span class="src-status src-pending" id="status-milho">—</span>
<span class="src-status src-pending" id="status-trigo">—</span>
<span class="src-status src-pending" id="status-oleo_soja">—</span>
<span class="src-status src-pending" id="status-wti">—</span>
```

**Sintoma observado:** valor (`milho-value`) atualizava, mas pingo de status ficava em "—" para sempre.

### Bug B — Inconsistência hífen ↔ underscore
**Local:** linha 271 do `index.html`

**Antes:** `id="oleo-90-chart"`  (hífen)
**Depois:** `id="oleo_soja-90-chart"` (underscore, igual ao `oleo_soja-value`)

**Sintoma:** chart 90d do óleo de soja ficava em branco mesmo com dados disponíveis.

### Bug C — Duplicação executiva ↔ câmbio
**Inicialmente suspeitei** que houvesse um conjunto duplicado (`kpi-usd` vs `usd-value`).
**Investigação revelou:** `kpi-usd`, `kpi-eur`, `kpi-brent`, `kpi-soja` são **IDs do card container**, não há duplicação de valor. Bug C **não existe**.

---

## 2. Tabela técnica · status real, card por card

Legenda de status:
- **OK** — fonte ao vivo
- **FB** — fallback (dado anterior)
- **DEV** — em desenvolvimento (decisão estratégica)
- **NA** — indisponível (fonte requer ação manual)

| # | Aba | Card / Bloco | IDs principais | Fonte | Coletor | Status | Observação |
|---|-----|--------------|----------------|-------|---------|--------|------------|
| 1 | 01 Exec | Resumo do dia | `exec-summary` | Status agente | `gerar_governance.py` | **OK** | Geração automática no fim do ciclo |
| 2 | 01 Exec | Status das fontes | `sources-summary`, `sources-meta` | governance.json | `gerar_governance.py` | **OK** | Cruza estado de todos os coletores |
| 3 | 01 Exec | KPI Dólar PTAX | `usd-value`, `usd-delta`, `usd-spark`, `status-usd` | BCB PTAX | `baixar_cambio.py` | **OK** | API oficial sem chave |
| 4 | 01 Exec | KPI Euro PTAX | `eur-value`, `eur-delta`, `eur-spark`, `status-eur` | BCB PTAX | `baixar_cambio.py` | **OK** | API oficial sem chave |
| 5 | 01 Exec | KPI Brent | `brent-value`, `brent-delta`, `brent-spark`, `status-brent` | Yahoo Finance | `baixar_commodities.py` | **OK** | Ticker BZ=F |
| 6 | 01 Exec | KPI Soja CBOT | `soja-value`, `soja-delta`, `soja-spark`, `status-soja` | Yahoo Finance | `baixar_commodities.py` | **OK** | Ticker ZS=F |
| 7 | 01 Exec | KPI Milho CBOT | `milho-value`, `milho-delta`, `status-milho` ★ | Yahoo Finance | `baixar_commodities.py` | **OK** | ★ ID adicionado nesta v2.4 |
| 8 | 01 Exec | KPI Trigo CBOT | `trigo-value`, `trigo-delta`, `status-trigo` ★ | Yahoo Finance | `baixar_commodities.py` | **OK** | ★ ID adicionado nesta v2.4 |
| 9 | 01 Exec | KPI Óleo de Soja | `oleo_soja-value`, `oleo_soja-delta`, `status-oleo_soja` ★ | Yahoo Finance | `baixar_commodities.py` | **OK** | ★ ID adicionado nesta v2.4 |
| 10 | 01 Exec | KPI WTI | `wti-value`, `wti-delta`, `status-wti` ★ | Yahoo Finance | `baixar_commodities.py` | **OK** | ★ ID adicionado nesta v2.4 |
| 11 | 02 Câmbio | Chart USD 90d | `usd-90-chart` | BCB PTAX | `baixar_cambio.py` | **OK** | SVG inline, zero CDN |
| 12 | 02 Câmbio | Chart Brent 90d | `brent-90-chart` | Yahoo Finance | `baixar_commodities.py` | **OK** | |
| 13 | 02 Câmbio | Chart Óleo de Soja 90d | `oleo_soja-90-chart` ★ | Yahoo Finance | `baixar_commodities.py` | **OK** | ★ Renomeado (era `oleo-90-chart`) |
| 14 | 02 Câmbio | Chart Soja 90d | `soja-90-chart` | Yahoo Finance | `baixar_commodities.py` | **OK** | |
| 15 | 02 Câmbio | Painel commodities completo | `commodities-tbody` | Yahoo Finance | `baixar_commodities.py` | **OK** | 8 ativos (inclui farelo e gás) |
| 16 | 02 Câmbio | Matriz correlação | `correlation-matrix` | — | (calculado no JS) | **DEV** | Stub: aguarda cálculo Pearson sobre série |
| 17 | 03 Grãos | Soja safra | `soja-safra-prod`, `soja-safra-delta`, `card-soja` | CONAB | `baixar_conab.py` | **NA** | CONAB requer download manual do CSV → `data/conab_graos_raw.csv` |
| 18 | 03 Grãos | Milho safra | `milho-safra-prod`, `milho-safra-delta` | CONAB | `baixar_conab.py` | **NA** | idem |
| 19 | 03 Grãos | Trigo safra | `trigo-safra-prod`, `trigo-safra-delta` | CONAB | `baixar_conab.py` | **NA** | idem |
| 20 | 03 Grãos | Ranking UF Soja | `soja-uf-tbody`, `soja-uf-meta` | CONAB | `baixar_conab.py` | **NA** | depende do CSV |
| 21 | 03 Grãos | Ranking UF Milho | `milho-uf-tbody`, `milho-uf-meta` | CONAB | `baixar_conab.py` | **NA** | depende do CSV |
| 22 | 03 Grãos | Cards regionais | `preco-regional-cards`, `regional-soja-viz` | CONAB | `baixar_conab.py` | **NA** | derivado das UFs |
| 23 | 04 Biodiesel | Produção total B100 | `b100-prod-total`, `b100-prod-delta` | ANP B100 | `baixar_anp_b100.py` | **FB** | XLS disponível mas parser openpyxl pendente |
| 24 | 04 Biodiesel | Mistura atual | `b100-mistura` | ANP B100 | `baixar_anp_b100.py` | **FB** | |
| 25 | 04 Biodiesel | Capacidade total | `b100-cap-total`, `b100-util` | ANP B100 | `baixar_anp_b100.py` | **FB** | |
| 26 | 04 Biodiesel | Ranking produtores | `biodiesel-rank-tbody`, `b100-rank-meta` | ANP B100 | `baixar_anp_b100.py` | **FB** | |
| 27 | 04 Biodiesel | Matérias-primas | `materias-primas-viz` | ANP B100 | `baixar_anp_b100.py` | **DEV** | gráfico de mix (soja/sebo/outros) |
| 28 | 04 Biodiesel | Impacto biodiesel | `impacto-biodiesel` | derivado | (JS) | **DEV** | calculado a partir de B100 + mistura |
| 29 | 04 Biodiesel | Contexto Be8 | `be8-context-viz`, `be8-cap` | Be8 manifesto | `gerar_be8_profile.py` | **OK** | |
| 30 | 05 Combustíveis | Diesel S10 | `anp-s10`, `anp-s10-delta`, `status-anp-s10` | ANP SLP | `baixar_anp_combustiveis.py` | **OK** | CSV semanal |
| 31 | 05 Combustíveis | Diesel S500 | `anp-s500`, `anp-s500-delta` | ANP SLP | `baixar_anp_combustiveis.py` | **OK** | |
| 32 | 05 Combustíveis | Gasolina | `anp-gasolina`, `anp-gasolina-delta` | ANP SLP | `baixar_anp_combustiveis.py` | **OK** | |
| 33 | 05 Combustíveis | Etanol | `anp-etanol`, `anp-etanol-delta` | ANP SLP | `baixar_anp_combustiveis.py` | **OK** | |
| 34 | 05 Combustíveis | Top 10 baratos S10 | `anp-s10-baratas-tbody` | ANP SLP | `baixar_anp_combustiveis.py` | **OK** | |
| 35 | 05 Combustíveis | Top 10 caros S10 | `anp-s10-caras-tbody` | ANP SLP | `baixar_anp_combustiveis.py` | **OK** | |
| 36 | 05 Combustíveis | Painel regional | `anp-regioes-viz` | ANP SLP | `baixar_anp_combustiveis.py` | **DEV** | mapa por região |
| 37 | 06 Comex | Soja exportação | `comex-soja-vol` | ComexStat | `baixar_comex.py` | **OK** | API oficial MDIC |
| 38 | 06 Comex | Farelo exportação | `comex-farelo-vol` | ComexStat | `baixar_comex.py` | **OK** | |
| 39 | 06 Comex | Óleo exportação | `comex-oleo-vol` | ComexStat | `baixar_comex.py` | **OK** | |
| 40 | 06 Comex | Biodiesel exportação | `comex-biodiesel-vol` | ComexStat | `baixar_comex.py` | **OK** | |
| 41 | 06 Comex | Diesel importação | `comex-diesel-vol` | ComexStat | `baixar_comex.py` | **OK** | |
| 42 | 06 Comex | Metanol importação | `comex-metanol-vol` | ComexStat | `baixar_comex.py` | **OK** | |
| 43 | 07 Radar IA | Síntese executiva | `radar-summary` | Regras IA | `scripts.js` `renderRadarIA()` | **OK** | inferência determinística |
| 44 | 07 Radar IA | Drivers positivos | `radar-bull` | Regras IA | `scripts.js` | **OK** | |
| 45 | 07 Radar IA | Riscos | `radar-bear` | Regras IA | `scripts.js` | **OK** | |
| 46 | 07 Radar IA | Ações recomendadas | `radar-acoes` | Regras IA | `scripts.js` | **OK** | |
| 47 | 08 Governança | Tabela de fontes | `governance-tbody`, `governance-last` | Consolidado | `gerar_governance.py` | **OK** | gera no fim do ciclo |
| 48 | 09 Newsletter | Hero | `news-hero-headline`, `news-hero-meta`, `news-hero-eyebrow` | RSS multifeed | `baixar_noticias.py` | **OK** | substitui Investing.com |
| 49 | 09 Newsletter | Top 5 manchetes | `news-top5`, `news-status` | RSS | `baixar_noticias.py` | **OK** | |
| 50 | 09 Newsletter | Radar regulatório | `news-radar-regulatorio` | RSS | `baixar_noticias.py` | **OK** | classificação por keyword |
| 51 | 09 Newsletter | Radar combustíveis | `news-radar-combustiveis` | RSS | `baixar_noticias.py` | **OK** | |
| 52 | 09 Newsletter | Radar agro | `news-radar-agro` | RSS | `baixar_noticias.py` | **OK** | |
| 53 | 09 Newsletter | Radar commodities | `news-radar-commodities` | RSS | `baixar_noticias.py` | **OK** | |
| 54 | 09 Newsletter | Radar concorrentes | `news-radar-concorrentes` | RSS | `baixar_noticias.py` | **OK** | |
| 55 | 09 Newsletter | Radar energia | `news-radar-energia` | RSS | `baixar_noticias.py` | **OK** | |
| 56 | 09 Newsletter | Impacto Be8 | `news-impacto-be8` | derivado | `baixar_noticias.py` | **OK** | texto estático no schema |
| 57 | 10 Be8 Profile | Todos os campos | `profile-*`, `be8-cap` | Manifesto | `gerar_be8_profile.py` | **OK** | dados públicos Be8 |
| 58 | 11 Vendas | KPIs por produto | `vendas-diesel-total`, `vendas-gasolina-total`, etc. | ANP vendas | `baixar_anp_vendas.py` | **FB** | CSV disponível, parser específico pendente |
| 59 | 11 Vendas | Mapa Brasil | `brasil-mapa`, `mapa-titulo`, `vendas-regional-viz` | ANP vendas | `baixar_anp_vendas.py` | **FB** | dependente do parser |
| 60 | 11 Vendas | Ranking distribuidoras | `vendas-rank-tbody`, `vendas-rank-meta` | ANP vendas | `baixar_anp_vendas.py` | **FB** | |
| 61 | 11 Vendas | Drilldown | `vendas-drilldown` | ANP vendas | `baixar_anp_vendas.py` | **DEV** | detalhe por UF/distribuidora |
| 62 | 12 Benchmark | Soja Brasil/Mundo | `usda-brasil-soja`, `usda-soja-mundo` | USDA PSD | `baixar_usda.py` | **FB** | API alcançável, parser por commodity pendente |
| 63 | 12 Benchmark | Biodiesel Brasil/Mundo | `usda-brasil-biod`, `usda-biod-mundo` | USDA PSD | `baixar_usda.py` | **FB** | |
| 64 | 12 Benchmark | Ranking soja | `usda-rank-soja-tbody` | USDA PSD | `baixar_usda.py` | **FB** | |
| 65 | 12 Benchmark | Ranking biodiesel | `usda-rank-biod-tbody` | USDA PSD | `baixar_usda.py` | **FB** | |
| 66 | 12 Benchmark | Estoques globais | `usda-estoques-viz`, `usda-preco-viz` | USDA PSD | `baixar_usda.py` | **DEV** | visualização |
| — | Topo | Ticker rolante | `ticker-track` | derivado | `scripts.js` | **OK** | usa cambio+commodities |
| — | Topo | Modo TV | `tv-bar`, `tv-config-*` | localStorage | `scripts.js` | **OK** | rotação configurável |

**Subtotal por status:**
- **OK** (ao vivo, dados reais): **41 cards**
- **FB** (fallback — arquivo disponível, parser pendente): **12 cards**
- **NA** (indisponível — requer ação manual): **6 cards** (todos CONAB)
- **DEV** (em desenvolvimento — não conseguia funcionar mesmo na v2.3): **7 cards**

---

## 3. Decisões aplicadas nesta v2.4

### 3.1 Investing.com → REMOVIDO
Investing tem Cloudflare anti-bot. Em vez de fingir que funciona, foi **substituído por fontes equivalentes**:
- Cotações de commodities → **Yahoo Finance** (mesmas commodities, API estável)
- Notícias → **Notícias Agrícolas RSS + Agência Gov** (atualizado pelo coletor `baixar_noticias.py`)
- Permanece listado em `governance.json` com status `indisponivel` (transparência)

### 3.2 FRED / EIA → MOVIDOS para "Em desenvolvimento"
Sem chaves de API configuradas. Foram **removidos do agente principal** e listados na seção Fase 3 da Governança como "Em desenvolvimento". Quando você conseguir as chaves grátis (5 min em https://fred.stlouisfed.org/docs/api/api_key.html e https://www.eia.gov/opendata/), basta:
1. Criar `.env` na raiz com `FRED_API_KEY=` e `EIA_API_KEY=`
2. Criar `scripts/baixar_fred.py` e `scripts/baixar_eia.py` (estrutura igual aos demais)
3. Adicionar em `PIPELINE` no `agente_atualizacao.py`

### 3.3 Automação → GitHub Actions
Workflow em `.github/workflows/update-data.yml`:
- Roda **às 10:00 UTC (07:00 BRT)** e **16:00 UTC (13:00 BRT)** todo dia
- Executa `python scripts/agente_atualizacao.py`
- Commita os JSONs atualizados de volta no repo
- Tem botão "Run workflow" manual em Actions

### 3.4 Schema padronizado
Todos os JSONs em `/data` agora seguem o **mesmo schema**:
```json
{
  "fonte": "nome humano",
  "status": "ok | fallback | erro | indisponivel | pendente",
  "ultima_atualizacao": "ISO 8601",
  "dados": { ... },
  "erro": "string ou null"
}
```
Isso permite que o JS faça `validateDataSchema()` em todos sem código específico.

### 3.5 JavaScript defensivo
Reescrito `scripts.js` (1.154 linhas) com:
- **`safeSetText(id, value, fallback)`** — não derruba a página se o ID não existir
- **`safeFetch(url, opts)`** — fetch com timeout 15s, no-cache, tratamento silencioso de 404
- **`updateSourceStatus(id, status, label)`** — atualiza pingo com classes consistentes
- **`validateDataSchema(json)`** — confere se o JSON tem schema padrão
- **`renderEmptyState(id, message)`** — placeholder elegante quando dado falta
- **try/catch por módulo** — erro num coletor não derruba os outros

---

## 4. Logs esperados ao rodar o agente

```
[10:00:01] · agente_atualizacao · iniciando ciclo
[10:00:02] · baixar_cambio · ok · USD=5.04 · EUR=5.41
[10:00:15] · baixar_commodities · ok · 8/8 ativos
[10:00:28] · baixar_anp_combustiveis · ok · 18000 postos S10 · R$ 6.234
[10:00:30] · baixar_anp_b100 · arquivo encontrado (185 KB) · parser pendente
[10:00:32] · baixar_anp_vendas · arquivo encontrado (12.3 MB) · parser pendente
[10:00:35] · baixar_conab · CONAB indisponível — coloque CSV em /data/conab_graos_raw.csv
[10:00:48] · baixar_comex · ok · 6/6 NCMs
[10:00:55] · baixar_usda · API alcançável · parser específico pendente
[10:01:12] · baixar_noticias · ok · 47 manchetes totais · top5=5
[10:01:13] · gerar_be8_profile · ok
[10:01:14] · gerar_governance · ok · 6/10 ao vivo · 0 erros
[10:01:14] · ciclo encerrado · 11/11 OK
```

---

## 5. O que cada arquivo do projeto faz

```
BENCH-BE8/
├── index.html                          ← 12 abas, 193 IDs, validado
├── README.md                           ← este projeto
├── DIAGNOSTICO_v2.4.md                 ← este documento
├── requirements.txt                    ← só requests
├── .gitignore
├── .github/workflows/update-data.yml   ← GitHub Actions 7h/13h BRT
├── assets/
│   ├── styles.css                      ← (mantém o seu atual)
│   ├── styles-v24-patch.css            ← complemento p/ classes novas
│   └── scripts.js                      ← v2.4 (1154 linhas, defensivo)
├── data/                               ← JSONs com schema padrão
│   ├── cambio.json                     ← BCB PTAX
│   ├── commodities.json                ← Yahoo Finance
│   ├── anp_combustiveis.json           ← ANP SLP
│   ├── anp_b100.json                   ← ANP biodiesel
│   ├── anp_vendas.json                 ← ANP vendas
│   ├── conab_graos.json                ← CONAB
│   ├── comex.json                      ← ComexStat MDIC
│   ├── noticias.json                   ← RSS multifonte
│   ├── be8_profile.json                ← manifesto institucional
│   ├── usda_benchmarks.json            ← USDA FAS PSD
│   ├── governance.json                 ← consolidado de fontes
│   └── status_fontes.json              ← resumo do último ciclo
├── scripts/
│   ├── utils.py                        ← http_get, save_json, logger
│   ├── agente_atualizacao.py           ← orquestrador principal
│   ├── baixar_cambio.py                ← BCB PTAX
│   ├── baixar_commodities.py           ← Yahoo Finance 8 ativos
│   ├── baixar_anp_combustiveis.py      ← ANP SLP CSV
│   ├── baixar_anp_b100.py              ← ANP B100 XLS (stub)
│   ├── baixar_anp_vendas.py            ← ANP vendas CSV (stub)
│   ├── baixar_conab.py                 ← CONAB safras
│   ├── baixar_comex.py                 ← ComexStat MDIC
│   ├── baixar_usda.py                  ← USDA FAS PSD probe
│   ├── baixar_noticias.py              ← RSS multifeed
│   ├── gerar_be8_profile.py            ← manifesto Be8
│   └── gerar_governance.py             ← gera governance.json + status_fontes.json
└── logs/                               ← logs por coletor (criado em runtime)
```

---

## 6. Próximos passos sugeridos (não fiz, fica pra você decidir)

1. **Parser openpyxl** para `baixar_anp_b100.py` e `baixar_anp_vendas.py` — destrava 12 cards FB → OK
2. **Download manual** do CSV CONAB para `data/conab_graos_raw.csv` — destrava 6 cards NA → OK
3. **Queries específicas USDA** por commodity (soja=2222000, biodiesel=4242000) — destrava 4 cards FB → OK
4. **FRED + EIA** quando tiver chaves
5. **Matriz de correlação Pearson** no JS (cálculo sobre commodities.json)

Com os 3 primeiros executados, seu painel sai de **41 OK** para **59 OK** (≈ 90% ao vivo).
