# 🚀 Atualização v2.1 → v2.2

> Esta versão corrige 3 bugs críticos identificados nos prints + adiciona 5 novas seções no Be8 Profile.

## 🐛 Bugs corrigidos

| Página | Bug | Causa | Fix |
|---|---|---|---|
| 03 · Grãos | Soja 0,0 Mt · Trigo 0,0 Mt · Milho com UFs erradas | Coletor pegava `dsc_safra_previsao` (1ª/2ª/Única) como safra, em vez de `ano_agricola` (2025/26) | Coletor CONAB reescrito · agora soma 1ª+2ª+3ª safras por ano agrícola |
| 05 · Combustíveis ANP | Tudo vazio (R$ —) | Frontend procurava `medias_brasil.diesel_s10` mas backend salva `produtos[]` | Frontend reescrito para ler `produtos[]` com fallback por id e por nome |
| 06 · Comex | Todos os 6 cards "Sem dados" | Frontend procurava `fluxos.diesel_imp` (objeto) mas backend salva `fluxos[]` (array) | Frontend reescrito para mapear `(categoria, fluxo)` do array |

## ✨ Novas seções (aproveitando dados ricos dos JSONs)

### Página 10 · Be8 Profile (5 novas seções)
1. **10.D · Papel estratégico** — parágrafo institucional sobre o papel da Be8 na cadeia brasileira
2. **10.E · Frentes de atuação** — 6 frentes (biodiesel, esmagamento, óleo, farelo, glicerina, exportação)
3. **10.F · Portfólio de produtos** — 6 produtos com descrição
4. **10.G · Presença geográfica + Indicadores públicos auditáveis** — 4 localizações + tabela com 8 indicadores rastreáveis (cada um com fonte)

### Página 06 · Comex (melhorias dentro dos cards existentes)
- Cada card agora mostra **variação % YoY** (vs. ano anterior)
- Quando disponível, exibe **preço médio implícito (US$/t)** — útil para comparar com CBOT
- Mostra valor secundário (FOB se principal é volume, vice-versa)

### Página 04 · Biodiesel
- Taxa de utilização agora vem direto do JSON (`taxa_utilizacao_pct`)
- Mistura vigente lida do JSON (`mistura_vigente`)

---

## 📋 Passo a passo (mesmo procedimento de antes)

### 1. PowerShell na pasta
```powershell
cd "C:\Be8 - Project\Be8 - Bench\BENCH-BE8"
git pull origin main
```

### 2. Extrair BENCH-BE8-v2.2.zip substituindo arquivos
Clique direito no ZIP → **Extrair tudo** → destino: `C:\Be8 - Project\Be8 - Bench\BENCH-BE8` → **Substituir tudo**.

### 3. Rodar o agente
```powershell
.venv\Scripts\activate
python scripts\agente_atualizacao.py
```

Você verá no log do CONAB algo como:
```
CONAB · idx mapeados · produto=3 uf=2 safra/ano=0 tipo=1 prod=6 area=5
CONAB · 623 registros · 4 safras únicas
CONAB · safras detectadas (mais recentes): ['2025/26', '2024/25', '2023/24']
CONAB · Soja safra 2025/26: 12 UFs · total 175.8 Mt
CONAB · Milho safra 2025/26: 17 UFs · total 130.4 Mt
CONAB · Trigo safra 2025/26: 8 UFs · total 8.2 Mt
```

### 4. Testar local
```powershell
python -m http.server 8000
```
Abra http://localhost:8000 → ir na **Página 03 (Grãos)** e conferir que a Soja agora aparece com produção total real (~170+ Mt).

### 5. Subir
```powershell
git add .
git commit -m "v2.2 · Corrige Graos/ANP/Comex + ampliacao Be8 Profile"
git push
```

---

## 🎯 O que conferir após o deploy

1. **Página 03 · Grãos**: Soja deve ter ~170 Mt (não 0), Milho deve mostrar MT, PR, MS no topo (não RS, MG, SC)
2. **Página 05 · Combustíveis**: Diesel S10 deve mostrar R$ ~5,90 (média Brasil); rankings UF preenchidos
3. **Página 06 · Comex**: cards mostram US$ 3,19 bi (diesel import), US$ 799 mi (óleo soja export), etc., com variação YoY
4. **Página 10 · Be8 Profile**: rolar até o fim — deve ter Papel estratégico, Frentes de atuação (tags), Produtos (grid), Presença geográfica + Indicadores públicos (tabela com fontes)

Manda print da página 10 inteira que eu quero ver o resultado final 🎯
