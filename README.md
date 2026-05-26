# BENCH-BE8 · Market Intelligence Platform · v2.4

> Torre de inteligência estratégica para Be8 — câmbio, commodities, biodiesel, regulatório, comex.
> Atualização automática via GitHub Actions duas vezes ao dia.

---

## Filosofia

> **Menos cards funcionando 100% com dados reais > muitos cards bonitos sem atualização real.**

- Se uma fonte funciona → mostra ao vivo
- Se a fonte está com problema mas tem cache → mostra fallback (badge laranja)
- Se a fonte está indisponível → mostra indisponível (badge cinza), **não inventa dado**
- Se a fonte foi desativada por estratégia → fica na governança como "em desenvolvimento"

---

## Stack

- **Frontend:** HTML estático + CSS + JS vanilla (zero CDN, zero framework)
- **Backend de coleta:** Python 3.11 + `requests`
- **Automação:** GitHub Actions agendado
- **Charts:** SVG inline gerado no JS

---

## Como rodar localmente

```bash
git clone https://github.com/lucasldiogo/BENCH-BE8.git
cd BENCH-BE8

# 1. Setup Python
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Mac/Linux
pip install -r requirements.txt

# 2. Rodar o agente (atualiza /data/*.json)
python scripts/agente_atualizacao.py

# 3. Servir o painel localmente
python -m http.server 8000

# 4. Abrir http://localhost:8000 no navegador
```

---

## Como ativar a atualização automática (GitHub Actions)

O workflow `.github/workflows/update-data.yml` já está configurado para rodar:
- **07:00 BRT (10:00 UTC)** todo dia
- **13:00 BRT (16:00 UTC)** todo dia
- Manualmente via Actions → "Update Market Intelligence Data" → Run workflow

Para funcionar é só dar push para o `main` que o GitHub Actions descobre o cron sozinho.

O workflow:
1. Instala Python 3.11 + requests
2. Roda `python scripts/agente_atualizacao.py`
3. Faz commit dos JSONs atualizados de volta no repo
4. Aciona o GitHub Pages (se estiver ativo)

**Não precisa de secrets** — todas as fontes ativas são públicas e sem chave.

---

## Estrutura do projeto

```
BENCH-BE8/
├── index.html                       12 abas, 193 IDs
├── README.md                        este arquivo
├── DIAGNOSTICO_v2.4.md              ← diagnóstico técnico, card por card
├── requirements.txt
├── .github/workflows/update-data.yml
├── assets/
│   ├── styles.css                   (mantém o seu)
│   ├── styles-v24-patch.css         complemento para classes novas
│   └── scripts.js                   v2.4 defensivo, 1154 linhas
├── data/                            JSONs schema padronizado
└── scripts/                         13 módulos Python
```

Detalhes de cada card e status → ver `DIAGNOSTICO_v2.4.md`.

---

## Status das fontes (resumo)

| # | Fonte | Tipo | Status |
|---|-------|------|--------|
| 1 | BCB PTAX | API pública | ✅ OK |
| 2 | Yahoo Finance | API pública | ✅ OK |
| 3 | ANP SLP combustíveis | CSV semanal | ✅ OK |
| 4 | ComexStat MDIC | API REST | ✅ OK |
| 5 | Notícias Agrícolas RSS | RSS | ✅ OK |
| 6 | Be8 institucional | Manifesto | ✅ OK |
| 7 | ANP B100 | XLS mensal | 🟡 Fallback (parser pendente) |
| 8 | ANP vendas UF | CSV mensal | 🟡 Fallback (parser pendente) |
| 9 | USDA FAS PSD | API REST | 🟡 Fallback (queries específicas pendentes) |
| 10 | CONAB safras | CSV mensal | ⚪ Indisponível (download manual) |
| 11 | FRED · estoques EUA | API key | ⚫ Em desenvolvimento (sem chave) |
| 12 | EIA · energia global | API key | ⚫ Em desenvolvimento (sem chave) |
| 13 | Investing.com | Anti-bot | ⚫ Em desenvolvimento (substituído por Yahoo + RSS) |

---

## Modo TV

Clique em "TV" no canto superior direito para configurar e iniciar a rotação automática entre páginas. Configuração salva em `localStorage` (por navegador).

---

## Desenvolvimento — adicionando uma nova fonte

1. Criar `scripts/baixar_NOVA.py` seguindo o padrão dos outros (`save_json` no schema padrão)
2. Adicionar em `PIPELINE` no `scripts/agente_atualizacao.py`
3. Adicionar entrada em `CATALOGO` no `scripts/gerar_governance.py`
4. Criar função `renderNOVA()` em `assets/scripts.js` e chamá-la em `reloadAllData()`
5. Testar localmente · commit · push

---

## Créditos

Desenvolvido por Lucas L. Diogo para Be8 · 2026.
