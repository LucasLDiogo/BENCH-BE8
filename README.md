# Be8 · Market Intelligence Platform

> Torre de inteligência estratégica para o setor de biodiesel — atualização automática diária.

**Desenvolvido por Lucas L. Diogo para a Be8 · 2026**

---

## O que é

Um painel executivo, estilo Bloomberg/cockpit, que reúne em uma única tela:

- Câmbio (BCB PTAX · USD, EUR)
- Commodities (Brent, WTI, Soja, Milho, Trigo, Óleo de soja, Farelo, Gás natural — via Yahoo Finance)
- Grãos (CONAB · produção por UF e cultura)
- Biodiesel (ANP · produção B100, capacidade, ranking de produtores)
- Combustíveis (ANP · preços semanais por UF)
- Comércio exterior (ComexStat MDIC · API oficial)
- Macro/energia (IBGE SIDRA · FRED · EIA)
- Notícias setoriais (RSS curado · radares temáticos)
- Be8 Profile (dados institucionais públicos)
- **Radar IA**: regras determinísticas que cruzam os indicadores e geram leitura executiva
- **Modo TV**: rotaciona páginas com rolagem automática para sala de reunião / monitor de cockpit

---

## Arquitetura

```
                       ┌────────────────────────────────┐
                       │  AGENTE PYTHON (07h e 13h)     │
                       │  scripts/agente_atualizacao.py │
                       └──────────────┬─────────────────┘
                                      │
              ┌───────────────────────┼───────────────────────┐
              ▼                       ▼                       ▼
        BCB PTAX                Yahoo Finance           CONAB / ANP
        ComexStat               IBGE / FRED / EIA       RSS notícias
              │                       │                       │
              └──────────────┬────────┴───────────────────────┘
                             ▼
                       data/*.json   ← contratos estáveis (UTF-8)
                             ▼
              ┌──────────────────────────────────┐
              │  FRONTEND ESTÁTICO (HTML/CSS/JS) │
              │  fetch local · zero CORS         │
              └──────────────┬───────────────────┘
                             ▼
                       GitHub Pages
                  (publicação automática)
```

**Por que essa arquitetura?**

- O browser não acessa diretamente APIs externas → **zero problemas de CORS**
- Tudo que vem de fora passa pelo agente Python, que faz validação, retry e cache
- O HTML lê só JSONs locais → carrega em milissegundos e funciona offline depois do primeiro fetch
- O agente pode rodar em **qualquer ambiente** (Windows local, Linux server, GitHub Actions)

---

## Estrutura do projeto

```
BENCH-BE8/
├── index.html                       # painel principal (10 páginas)
├── README.md                        # este arquivo
├── DOCUMENTACAO_DASHBOARD.md        # explicação de cada card/gráfico
├── requirements.txt                 # dependências Python
│
├── assets/
│   ├── logo-be8.svg                 # identidade visual oficial
│   ├── styles.css                   # design system (818 linhas)
│   └── scripts.js                   # frontend (1.500 linhas)
│
├── data/                            # JSONs gerados pelo agente
│   ├── cambio.json                  # USD, EUR PTAX + série 90d
│   ├── commodities.json             # Brent, WTI, soja, milho, etc.
│   ├── conab_graos.json             # safras CONAB
│   ├── anp_combustiveis.json        # preços semanais ANP
│   ├── anp_b100.json                # produção biodiesel
│   ├── comex.json                   # ComexStat MDIC
│   ├── ibge_sidra.json              # IBGE LSPA
│   ├── fred_eia.json                # FRED + EIA
│   ├── noticias.json                # newsletter setorial
│   ├── be8_profile.json             # dados institucionais Be8
│   ├── status_fontes.json           # auditoria de cada fonte
│   └── build_stamp.json             # timestamp último build
│
├── downloads/                       # cache de arquivos brutos (CSV/XLS)
│   ├── anp/
│   ├── conab/
│   ├── ibge/
│   ├── eia/
│   ├── comex/
│   └── fred/
│
├── scripts/
│   ├── utils.py                     # HTTP retry, logger, salvamento atômico, status
│   ├── baixar_cambio.py             # BCB PTAX
│   ├── baixar_commodities.py        # Yahoo Finance
│   ├── baixar_anp_combustiveis.py   # CSVs semanais ANP
│   ├── baixar_anp_b100.py           # produção B100 mensal
│   ├── baixar_conab.py              # safras CONAB
│   ├── baixar_ibge_sidra.py         # IBGE SIDRA
│   ├── baixar_fred_eia.py           # FRED + EIA
│   ├── baixar_comex.py              # ComexStat API
│   ├── gerar_noticias.py            # newsletter RSS
│   ├── gerar_be8_profile.py         # dados públicos Be8
│   ├── atualizar_html.py            # injeta timestamp no HTML
│   ├── agente_atualizacao.py        # ORQUESTRADOR (rode este)
│   └── publicar_github.py           # git add/commit/push automático
│
├── logs/
│   └── atualizacao.log              # log do agente
│
└── .github/workflows/
    ├── update-data.yml              # cron 10h e 16h UTC (= 07h e 13h BRT)
    └── deploy-pages.yml             # publicação automática no GitHub Pages
```

---

## Quickstart · execução local em 4 passos

### Pré-requisitos
- Python 3.10+
- Git
- Editor de código (VS Code recomendado)
- (Opcional) Chave gratuita do FRED · https://fred.stlouisfed.org/docs/api/api_key.html
- (Opcional) Chave gratuita do EIA · https://www.eia.gov/opendata/register.php

### 1. Clonar e instalar
```bash
git clone https://github.com/lucasldiogo/BENCH-BE8.git
cd BENCH-BE8

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. (Opcional) Chaves de API
Crie um arquivo `.env` na raiz:
```env
FRED_API_KEY=sua_chave_aqui
EIA_API_KEY=sua_chave_aqui
```
Sem as chaves, FRED/EIA ficam em status PENDENTE — o painel continua funcionando com BCB/Yahoo/ComexStat/CONAB/ANP.

### 3. Rodar o agente
```bash
python scripts/agente_atualizacao.py
```

Saída esperada:
```
[09:00:01] · agente_atualizacao · iniciando ciclo
[09:00:02] · baixar_cambio · BCB PTAX · USD=R$ 5.04 · EUR=R$ 5.41
[09:00:05] · baixar_commodities · 8/8 ativos · OK
[09:00:18] · baixar_anp_combustiveis · 27 UFs · semana 2026-05-19
[09:00:32] · baixar_conab · safra 2025/26 · 27 linhas
...
[09:01:14] · agente_atualizacao · ciclo encerrado · 10/10 fontes OK
```

### 4. Visualizar o painel

```bash
python -m http.server 8000
```
Abra http://localhost:8000 no navegador.

---

## Agendamento automático

### Opção A — Windows Task Scheduler (recomendado para PC local)

1. Abra **Agendador de Tarefas** (`taskschd.msc`)
2. Criar Tarefa → "Be8 Market Intelligence"
3. **Disparadores**:
   - Diariamente · 07:00
   - Diariamente · 13:00
4. **Ações**:
   - Programa: `C:\caminho\BENCH-BE8\.venv\Scripts\python.exe`
   - Argumentos: `scripts/agente_atualizacao.py`
   - Iniciar em: `C:\caminho\BENCH-BE8`
5. **Configurações** → executar mesmo sem usuário logado

### Opção B — GitHub Actions (recomendado para produção em nuvem)

Já está pronto em `.github/workflows/update-data.yml`. Configure os secrets:

`Settings → Secrets and variables → Actions → New repository secret`

- `FRED_API_KEY` (opcional)
- `EIA_API_KEY` (opcional)

O workflow:
- Roda automaticamente às **10:00 UTC** (07:00 BRT) e **16:00 UTC** (13:00 BRT)
- Pode ser disparado manualmente em Actions → "Update Market Intelligence Data" → Run workflow
- Faz commit dos JSONs atualizados de volta no repositório
- Aciona o deploy do GitHub Pages

### Opção C — Linux cron
```bash
crontab -e
# Adicionar:
0 7,13 * * * cd /caminho/BENCH-BE8 && .venv/bin/python scripts/agente_atualizacao.py >> logs/cron.log 2>&1
```

---

## Como usar com Claude Code

Claude Code (CLI) acelera muito o workflow de manutenção do painel.

1. **Instalar** · `npm install -g @anthropic-ai/claude-code`
2. **Rodar** dentro da pasta do projeto · `claude`
3. Exemplos de comandos úteis:

```
"Adicione uma coluna 'variação 60 dias' na tabela de commodities"
"Crie um novo coletor para o índice IPCA do IBGE"
"O endpoint da CONAB mudou: ajuste o scraper em scripts/baixar_conab.py"
"Adicione um KPI de Crack Spread (Brent vs Diesel) na Visão Executiva"
```

Claude Code lê todo o repositório, faz as alterações nos arquivos certos e roda o agente para testar.

## Como usar com Claude Cowork

Cowork é a ferramenta de automação de tarefas no desktop. Você pode:

1. Configurar um "Job" que abre o terminal, ativa o venv e roda `python scripts/agente_atualizacao.py`
2. Agendar para 07h e 13h (substitui o Task Scheduler)
3. Notificações ao final do ciclo

Detalhes em https://docs.claude.com (procurar por "Cowork").

---

## Publicação no GitHub Pages

Já vem configurado em `.github/workflows/deploy-pages.yml`.

1. No GitHub: **Settings → Pages**
2. Source: `GitHub Actions`
3. Após o primeiro push, o painel fica em: `https://<seu-usuario>.github.io/BENCH-BE8/`

O fluxo completo:
- Push (manual ou via agente local) → GitHub Actions roda update-data → commit dos JSONs → deploy-pages publica → painel atualizado em ~3 minutos.

---

## Mapa das fontes de dados

| Fonte | Tipo | Frequência | Custo | Status |
|---|---|---|---|---|
| BCB PTAX | API REST OData | Diária (4×) | Grátis | ✓ Live |
| Yahoo Finance | API JSON | 15min delay | Grátis | ✓ Live |
| ComexStat MDIC | API REST oficial | Mensal | Grátis | ✓ Live |
| ANP Combustíveis | CSV semanal | Toda 6ª-feira | Grátis | ✓ Live |
| ANP B100 | XLS/CSV mensal | Mensal | Grátis | ✓ Live |
| CONAB Safras | XLS mensal | Mensal | Grátis | ✓ Live |
| IBGE SIDRA | API REST | Mensal | Grátis | ✓ Live |
| FRED + EIA | API REST | Diária | Grátis (chave) | ✓ Live |
| RSS Newsletter | Feeds RSS | Diária | Grátis | ✓ Live |
| Be8 Profile | Curadoria | Trimestral | Grátis | ✓ Live |

**Fontes premium (Sprint 3 — negociação comercial):**
- CEPEA/ESALQ (preços agro spot)
- SIFRECA (frete rodoviário)
- ANTT (piso mínimo de frete)
- Trading Economics (consensus de mercado)

---

## Princípios de governança

1. **Nunca inventar dados** · se uma fonte falha, o painel mostra `PENDENTE`/`ERRO` sem quebrar layout.
2. **Auditoria visível** · página de Governança mostra status de cada fonte e horário da última verificação.
3. **Contratos estáveis** · cada JSON tem um schema documentado em `DOCUMENTACAO_DASHBOARD.md`.
4. **Idempotência** · rodar o agente várias vezes seguidas produz o mesmo resultado.
5. **Recuperação graciosa** · falha em uma fonte não derruba as outras (try/except em todos os coletores).
6. **Sem segredos no código** · chaves de API em `.env` ou GitHub Secrets.

---

## Solução de problemas

**`ModuleNotFoundError: No module named 'requests'`**
→ Esqueceu de ativar o venv ou rodar `pip install -r requirements.txt`.

**O painel abre, mas todos os cards estão "PENDENTE"**
→ O agente ainda não rodou. Execute `python scripts/agente_atualizacao.py` e atualize a página.

**`HTTPError 403/429` em algum coletor**
→ Rate limit temporário. Espere alguns minutos. O agente tem retry exponencial embutido, mas alguns provedores são agressivos. Rodar manualmente de novo geralmente resolve.

**A URL do CSV da ANP mudou e o coletor falha**
→ Edite `scripts/baixar_anp_combustiveis.py` — a URL é descoberta dinamicamente do índice gov.br/anp. Se o índice também mudou, peça ao Claude Code "atualize a URL do CSV semanal da ANP, ela agora está em [nova URL]".

**`fatal: not a git repository` ao publicar**
→ `git init && git remote add origin https://github.com/SEU-USUARIO/BENCH-BE8.git`

---

## Roadmap

**Fase 1 (entregue · v2.0)** ✓
- 10 páginas com identidade Be8
- Agente Python orquestrador
- 10 fontes integradas
- Modo TV com configuração persistente
- Newsletter com 6 radares
- Be8 Company Profile
- GitHub Actions

**Fase 2 (próxima · v2.5)**
- Painel ANP biodiesel via scraping (planilha mensal)
- USDA FAS — benchmark global de óleo de soja
- Histórico anual (não só 90 dias)
- Export de relatório PDF executivo

**Fase 3 (v3.0)**
- CEPEA/ESALQ widget oficial
- SIFRECA + ANTT (logística)
- Modelos preditivos B100 (regressão multivariável)
- LLM (Claude) para resumos executivos diários

---

## Créditos

**Desenvolvido por Lucas L. Diogo**
para a Be8 (BSBIOS) · Passo Fundo · 2026

Identidade visual baseada nos originais de marca oficiais da Be8.
Dados públicos de fontes governamentais brasileiras e provedores abertos.
