# 🚀 Atualização v2.0 → v2.1 · Guia rápido

> Esta versão corrige os bugs identificados na primeira análise e adiciona melhorias visuais significativas.

## 🆕 O que mudou

### ✅ Bugs corrigidos
- **Status das fontes** na Visão Executiva agora mostra todas as 10 fontes (antes só 6)
- **Top 3 Oportunidades / Riscos** sempre populados (regras de fallback estruturais)
- **CONAB** com URL correta (.txt) + fallback embutido com dados oficiais 2024/25
- **ANP B100** com snapshot de 13 produtores e market shares públicos
- **IBGE SIDRA** com query corrigida (tabela 1612)
- **FRED + EIA** com mensagem clara sobre chaves opcionais
- **Newsletter** com cards mais ricos e botão "ABRIR NOTÍCIA →"
- **Be8 Profile** com hero visual da Cadeia de Valor (imagem oficial)

### ✨ Novos recursos
- **Botão Atualizar** agora recarrega JSONs sem reload da página (suave)
- **Botão Snapshot** baixa PNG do painel atual
- **Tooltips interativos** em todos os gráficos (já estavam, mas confirmados)
- **Imagem Cadeia de Valor Be8** na página 10 como hero

---

## 📋 Passo a passo da atualização

### 1. No PC: abra o PowerShell e entre na pasta do projeto

```powershell
cd "C:\Be8 - Project\Be8 - Bench\BENCH-BE8"
```

### 2. Sincronize com o GitHub primeiro (evita conflitos)

```powershell
git pull origin main
```

### 3. Baixe o ZIP `BENCH-BE8-v2.1.zip` e extraia DENTRO da pasta atual, substituindo arquivos

**No Windows:**
1. Baixe o arquivo `BENCH-BE8-v2.1.zip`
2. Clique com botão direito → "Extrair tudo..."
3. Aponte o destino para: `C:\Be8 - Project\Be8 - Bench\BENCH-BE8`
4. Escolha **"Substituir os arquivos no destino"**

> ⚠️ A extração vai sobrescrever: `index.html`, `assets/`, `data/`, `scripts/`, `README.md`, `DOCUMENTACAO_DASHBOARD.md`, `CHECKLIST.md`, `requirements.txt`, `.gitignore`, `.github/`
> 
> ✅ Mantém: `.venv/`, `.git/`, `downloads/`, `logs/`

### 4. Verifique o que mudou (opcional, mas instrutivo)

```powershell
git status
```

Deve aparecer uma lista com os arquivos modificados.

### 5. Rode o agente de novo para popular dados ao vivo

```powershell
.venv\Scripts\activate
python scripts\agente_atualizacao.py
```

Agora você deve ver:
- ✅ BCB Câmbio OK
- ✅ Yahoo Commodities OK
- ✅ ANP Preços combustíveis OK
- ✅ **ANP B100 PARCIAL** (com 13 produtores via snapshot)
- ✅ **CONAB PARCIAL** (com fallback, ou OK se URL.txt funcionar)
- ✅ **IBGE SIDRA PARCIAL** (com snapshot)
- ✅ ComexStat OK
- ✅ Notícias OK
- ✅ Be8 Profile OK

### 6. Teste localmente

```powershell
python -m http.server 8000
```

Abra http://localhost:8000 e confira:
- Status das fontes mostra 10/10 (8 OK + 4 PARCIAL/PENDENTE)
- Top 3 Oportunidades e Top 3 Riscos têm conteúdo
- Página Grãos preenchida com dados (CO + S = 85%+ da soja)
- Página Biodiesel com ranking completo e Be8 destacada em verde
- Página Newsletter com botões "ABRIR NOTÍCIA →"
- Página Be8 Profile (10) com a IMAGEM grande da Cadeia de Valor no topo

### 7. Suba para o GitHub

```powershell
git add .
git commit -m "v2.1 · Correções de bugs + Cadeia de Valor + tooltips + snapshots"
git push
```

### 8. Aguarde 2-3 minutos e confira no ar:

```
https://lucasldiogo.github.io/BENCH-BE8/
```

---

## 🔑 (Opcional) Configurar FRED + EIA — 5 minutos

Para ativar a 10ª fonte (estoques globais de energia):

### FRED (St. Louis Fed)
1. Acesse https://fred.stlouisfed.org/docs/api/api_key.html
2. Crie conta (e-mail apenas)
3. Copie sua chave (32 caracteres)

### EIA (US Energy Info)
1. Acesse https://www.eia.gov/opendata/register.php
2. Digite e-mail → chave chega instantaneamente

### Configurar no GitHub Actions
1. Repo no GitHub → **Settings** → **Secrets and variables** → **Actions**
2. Clique **New repository secret** duas vezes:
   - Nome: `FRED_API_KEY` · Valor: sua chave FRED
   - Nome: `EIA_API_KEY` · Valor: sua chave EIA
3. Pronto. Na próxima execução do workflow, as duas fontes ficam Live.

### Configurar localmente (opcional)
Crie um arquivo `.env` na raiz do projeto:
```
FRED_API_KEY=sua_chave_aqui
EIA_API_KEY=sua_chave_aqui
```
O `.gitignore` já está configurado para NÃO subir esse arquivo ao GitHub.

---

## 🆘 Se algo der errado

| Problema | Solução |
|---|---|
| `git pull` dá conflito de novo | `git checkout --ours <arquivo>` para cada conflito · `git add` · `git commit` |
| Página em branco no localhost | Abra DevTools (F12) → Console → me manda o erro |
| Imagem Cadeia de Valor não aparece | Confira se o arquivo `assets/cadeia-valor-be8.png` existe (~340 KB) |
| Ainda mostra "4/10 OK" | Limpe cache (Ctrl+Shift+R) — o navegador pode estar com versão antiga do JS |

---

## ✅ Checklist final

- [ ] `git pull` rodou sem erro
- [ ] ZIP extraído na pasta certa, arquivos substituídos
- [ ] Agente rodou e mostrou 10/10 fontes (mesmo que algumas em PARCIAL)
- [ ] Localhost mostra novidades (10 fontes no status, Cadeia de Valor com imagem)
- [ ] `git push` enviou ao GitHub
- [ ] Site público atualizado
- [ ] (Opcional) Chaves FRED+EIA configuradas

Quando tudo isso estiver ✓, me manda print da Visão Executiva nova para a gente celebrar! 🎉
