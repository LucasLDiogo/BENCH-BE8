# Checklist de Validação · Be8 Market Intelligence

Use este checklist antes de publicar uma nova versão.

## ① Estrutura de arquivos
- [ ] `index.html` na raiz
- [ ] `assets/styles.css` · 818 linhas
- [ ] `assets/scripts.js` · ~1500 linhas
- [ ] `assets/logo-be8.svg` · identidade oficial preservada
- [ ] `data/*.json` · 12 arquivos (mínimo placeholders)
- [ ] `scripts/*.py` · 14 scripts compilando sem erro
- [ ] `requirements.txt` na raiz
- [ ] `.github/workflows/update-data.yml` e `deploy-pages.yml`
- [ ] `README.md` e `DOCUMENTACAO_DASHBOARD.md` na raiz

## ② Validação técnica
- [ ] Todos os scripts Python compilam: `for f in scripts/*.py; do python -m py_compile "$f"; done`
- [ ] JavaScript sem erro de sintaxe: `node -c assets/scripts.js`
- [ ] HTML carrega sem erro no console (abrir DevTools → Console)
- [ ] Sem chamadas a APIs externas direto do browser (apenas fetch local de `data/*.json`)
- [ ] Caminhos relativos (não `file:///` nem `localhost`)
- [ ] Fontes Google carregando (Fraunces · Inter Tight · JetBrains Mono)

## ③ Execução do agente
- [ ] `python scripts/agente_atualizacao.py` roda sem exceção fatal
- [ ] `logs/atualizacao.log` registrado
- [ ] `data/status_fontes.json` atualizado com timestamp do run
- [ ] Cada JSON em `data/` tem `ultima_atualizacao` recente
- [ ] Pelo menos 5 fontes em `status: "OK"`

## ④ Identidade visual
- [ ] Cor azul-marinho `#081f2e` no fundo
- [ ] Gradiente verde `#0eb194 → #55c94f` em elementos de destaque
- [ ] Logo Be8 oficial no topo
- [ ] Tipografia Fraunces nos títulos h1/h2
- [ ] Tipografia Inter Tight no UI geral
- [ ] Tipografia JetBrains Mono nos números
- [ ] Sem cores Bloomberg "padrão" (amarelo/laranja exagerado) — só os tons curados do design system

## ⑤ Conteúdo das 10 páginas
- [ ] **01 · Visão Executiva**: KPIs renderizam, banner IA aparece, tendência 30d desenha
- [ ] **02 · Câmbio & Commodities**: 4 line charts + matriz de correlação
- [ ] **03 · Grãos & Safra**: 3 KPIs + 2 tabelas top UFs + barras regionais + 3 cards impacto
- [ ] **04 · Biodiesel**: 4 KPIs + ranking com Be8 destacada + composição matérias-primas
- [ ] **05 · Combustíveis**: 4 KPIs ANP + 2 tabelas UFs + barras por região
- [ ] **06 · Comércio Exterior**: 6 cards de fluxo + tabela NCMs
- [ ] **07 · Radar IA**: síntese + bull/bear + ações + tabela regras
- [ ] **08 · Governança**: tabela 10 fontes auditáveis + roadmap 3 colunas
- [ ] **09 · Newsletter**: hero + top 5 + 6 radares + impacto Be8
- [ ] **10 · Be8 Profile**: hero + 4 KPIs + plantas + cadeia + timeline + sustentabilidade + posicionamento + fontes

## ⑥ Modo TV
- [ ] Botão "Modo TV" no topbar abre overlay de configuração
- [ ] Configuração persiste no localStorage
- [ ] Barra inferior aparece com relógio, label, progress bar
- [ ] Rolagem automática funciona nas páginas longas
- [ ] ESC sai do modo TV
- [ ] Space pausa/retoma
- [ ] Setinha → avança página

## ⑦ Resiliência
- [ ] Se `data/cambio.json` estiver vazio, painel mostra "PENDENTE" sem quebrar
- [ ] Se 3 fontes falharem, as outras 7 continuam funcionando
- [ ] Console limpo (apenas warnings esperados de fetch local)
- [ ] Layout responsivo (testar em 1366x768 mínimo)

## ⑧ Governança & Auditoria
- [ ] Nenhum dado inventado — toda informação rastreável até a fonte primária
- [ ] Fontes públicas validadas em `be8_profile.json` (be8energy.com, O Nacional, Wikipedia, BiodieselBR)
- [ ] Página de Governança mostra status real, não "tudo verde sempre"
- [ ] Quando faltar dado, mostra "não disponível em fonte pública validada"

## ⑨ Publicação
- [ ] `.env` no `.gitignore` (chaves de API nunca no Git)
- [ ] Commit message descritivo: "Atualização automática Market Intelligence Be8 - YYYY-MM-DD HH:MM"
- [ ] GitHub Actions secrets configurados (FRED_API_KEY, EIA_API_KEY se aplicável)
- [ ] GitHub Pages source = "GitHub Actions"
- [ ] URL final pública testada: `https://lucasldiogo.github.io/BENCH-BE8/`

## ⑩ Assinatura
- [ ] Rodapé com "Desenvolvido por Lucas L. Diogo para Be8 · Market Intelligence Platform · 2026"
