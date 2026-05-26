# Be8 Market Intelligence · Documentação dos Cards e Gráficos

> Documentação card-a-card. Para cada elemento: **fonte**, **cálculo**, **objetivo gerencial**, **interpretação executiva**, **regra de alerta** e **limitações**.

---

## Página 01 · Visão Executiva

### Resumo executivo do dia (banner IA)
- **Fonte**: composição automática a partir de `cambio.json` + `commodities.json` + regras do Radar IA.
- **Cálculo**: extrai cotações do fechamento, calcula variação diária e seleciona o insight mais relevante de `STATE.insights`.
- **Objetivo**: dar uma leitura de 1 frase para abrir reuniões executivas.
- **Interpretação**: se aparecer "lateral / misto", o dia não tem gatilho forte. Se aparecer "construtivo" ou "riscos elevados", olhe os cards de oportunidades/riscos.
- **Limitação**: não substitui leitura humana — é heurística determinística, não LLM.

### Status das fontes
- **Fonte**: `status_fontes.json` (preenchido pelo agente a cada execução).
- **Cálculo**: contagem `OK` / total. Cada linha mostra o nome curto da fonte com ✓ (OK), ~ (parcial), ○ (pendente), ✕ (erro).
- **Objetivo**: dar previsibilidade — você sabe quando os dados são confiáveis.
- **Alerta**: se ficar ≥3 fontes em ✕ ou ○, investigar logs.

### KPI Dólar PTAX
- **Fonte**: Banco Central · serviço PTAX (Olinda OData).
- **Cálculo**: cotação de fechamento de venda. Variação = (PTAX hoje − PTAX D-1) / PTAX D-1 × 100.
- **Objetivo**: monitorar o custo de insumos importados (metanol, catalisadores) e a competitividade de exportações da Be8.
- **Interpretação**: real desvalorizando favorece a exportação de óleo/farelo e penaliza importações; real valorizando faz o oposto.
- **Alerta**: variação diária > ±1% acende alerta de pricing.
- **Limitação**: o BCB só divulga PTAX após as 13h30 BRT; antes disso, mostra o dia anterior.

### KPI Euro PTAX
- **Fonte**: BCB Olinda OData.
- **Cálculo**: idem dólar.
- **Objetivo**: exposição em embarques para a Europa via Be8 Switzerland.

### KPI Brent / WTI
- **Fonte**: Yahoo Finance (`BZ=F` Brent · `CL=F` WTI).
- **Cálculo**: último preço de fechamento. Variação D-1 e séries 7d/30d/90d.
- **Objetivo**: benchmark do **diesel substituído**. O preço-teto do biodiesel é fixado em leilões ANP que correlacionam com diesel B (atrelado ao Brent).
- **Interpretação**: Brent subindo → ambiente favorável a repasse de preço para B100.
- **Limitação**: Yahoo tem 15 min de delay e fecha sextas; em finais de semana mostra dado de sexta.

### KPI Soja CBOT
- **Fonte**: Yahoo Finance (`ZS=F`).
- **Cálculo**: contrato futuro mais próximo em ¢/bushel.
- **Objetivo**: indicador macro da matéria-prima. Sojas em alta pressionam custo do óleo (subproduto do esmagamento).
- **Conversão útil**: 1 bushel soja ≈ 27,2 kg; ¢ 1.000/bu ≈ US$ 367/t.

### KPI Milho CBOT (`ZC=F`)
- **Objetivo**: concorrente energético do biodiesel — usado no etanol de milho em forte expansão no Brasil.

### KPI Trigo CBOT (`ZW=F`)
- **Objetivo**: contextualizar área agrícola disputada com soja no inverno (RS, PR).

### KPI Óleo de Soja CBOT (`ZL=F`)
- **Fonte**: Yahoo Finance.
- **Cálculo**: contrato futuro em ¢/libra.
- **Objetivo**: **principal insumo do B100 brasileiro** (~70% do mix). Variável de margem mais sensível.
- **Conversão útil**: ¢ 50/lb ≈ US$ 1.100/t.
- **Alerta**: alta de 2σ em 30d aciona "competição por matéria-prima" no Radar IA.

### Top 3 Oportunidades / Top 3 Riscos
- **Fonte**: regras determinísticas em `scripts.js → buildInsights()`.
- **Cálculo**: filtros sobre os indicadores ao vivo (ex.: "se óleo soja sobe E Brent sobe, então pressão de alta no B100").
- **Objetivo**: aterrissar a leitura macro em ações práticas.
- **Interpretação**: cada item carrega tag (CÂMBIO, BIODIESEL, INSUMO, …) e classe (bull/bear/alert/neutral).
- **Limitação**: regras são auditáveis (estão na página Radar IA · 07.B). Não é LLM nem modelo treinado.

### Tendência 30 dias — base 100
- **Fonte**: `cambio.json` + `commodities.json`.
- **Cálculo**: cada série é normalizada para 100 no D-30. As linhas mostram a evolução relativa de USD/BRL, Brent e Soja.
- **Objetivo**: ver descolamento/convergência dos três indicadores de margem do biodiesel.
- **Interpretação**: as três linhas se movem juntas em ciclos de risk-on/risk-off. Quando divergem, há trade ou notícia idiossincrática (ex.: sanção, geada).

### Alertas Críticos
- **Fonte**: insights do Radar IA filtrados por `type === 'alert' || 'bear'`.
- **Objetivo**: fila de atenção imediata da diretoria.

---

## Página 02 · Câmbio & Commodities

### USD/BRL · série 90 dias
- **Fonte**: BCB PTAX, série fechamento diário.
- **Cálculo**: gráfico de linha + área. Eixos auto-escalados (mín − 10%, máx + 10%).
- **Objetivo**: ver tendência e regime — câmbio em alta/baixa/lateralizado.
- **Limitação**: dias úteis apenas (não há fechamento aos fins de semana).

### Brent / Óleo Soja / Soja · séries 90 dias
- **Fonte**: Yahoo Finance (séries diárias).
- **Cálculo**: idem USD/BRL.
- **Objetivo**: regime visual do principal vetor de margem.

### Painel de commodities (tabela 8 ativos)
- **Fonte**: `commodities.json`.
- **Colunas**: nome · mercado · último · D-1 · variação % · 7d % · 30d % · status.
- **Cálculo**: var_d_pct = (último - anterior) / anterior × 100; var_7d_pct usa fechamento de 7 pregões atrás; var_30d_pct, 30 pregões.
- **Objetivo**: visão única de toda a "cesta" relevante.
- **Interpretação**: olhar a coluna 30d% — viés de curto prazo. Compare com 7d% para detectar reversão.

### Matriz de correlação
- **Fonte**: séries 60 pregões de USD/BRL, Brent, Óleo Soja, Soja, Milho.
- **Cálculo**: coeficiente de Pearson entre cada par de séries.
- **Objetivo**: confirmar que o B100 é função (óleo soja, USD/BRL, Brent). Detectar quando a relação se quebra.
- **Interpretação**:
  - Cor verde forte (>0,7): movimento conjunto — hedge de uma proxy funciona.
  - Cor vermelha forte (<−0,5): hedge cruzado precisa inverter posição.
  - Cor pálida (~0): correlação fraca — diversificação.
- **Limitação**: Pearson assume linearidade; em quebras estruturais (ex.: guerra, sanção) a correlação histórica explode. Use rolling window.

---

## Página 03 · Grãos & Safra

### KPI Soja / Milho / Trigo (safra atual)
- **Fonte**: CONAB · Acompanhamento da Safra Brasileira de Grãos.
- **Cálculo**: soma da produção (Mt) de todas as UFs para a cultura na safra mais recente do arquivo. Variação = (atual − anterior) / anterior × 100.
- **Objetivo**: dimensionar disponibilidade de matéria-prima.
- **Interpretação**: para soja, oferta brasileira é folgada para o consumo doméstico — o preço é fixado pela paridade de exportação (Chicago × USD/BRL × frete).
- **Limitação**: CONAB revisa estimativas várias vezes; uma queda mensal pode ser ajuste estatístico, não realidade física.

### Top UFs produtoras (soja e milho)
- **Fonte**: CONAB.
- **Cálculo**: ordena UFs por `producao_mt` decrescente. Share % = produção UF / total cultura × 100.
- **Objetivo**: ver concentração regional e prever logística.
- **Interpretação**: MT + PR + RS respondem por ~60% da soja brasileira. Frete dessas três UFs é o que importa para custo de originação.

### Composição regional (barra horizontal · soja)
- **Fonte**: CONAB agregado por região.
- **Cálculo**: soma UFs por região geográfica (CO, S, SE, NE, N) e calcula % do total.
- **Objetivo**: visualizar o eixo CO + S = ~85% da soja.

### Impacto para biodiesel (3 cards)
- **Fonte**: derivação a partir de CONAB.
- **Cálculo**:
  - Óleo estimado = Soja total × 18% (taxa típica de extração).
  - Óleo para B100 = Óleo total × 35% (parcela histórica destinada ao biodiesel).
- **Objetivo**: traduzir produção agrícola em equivalência de biodiesel.
- **Limitação**: parâmetros 18% e 35% são médias históricas — variam por ano e por mix de matérias-primas.

---

## Página 04 · Biodiesel & Market Share

### KPI Produção B100 Brasil (m³/mês)
- **Fonte**: ANP · Painel Dinâmico Produção de Biodiesel.
- **Cálculo**: produção mensal mais recente disponível.
- **Objetivo**: dimensionar mercado total para calcular market share Be8.

### KPI Capacidade Instalada (m³/ano)
- **Fonte**: Anuário Estatístico ANP (anual).
- **Cálculo**: soma de capacidade autorizada de todas as plantas.
- **Subindicador**: taxa de utilização = produção anualizada / capacidade × 100.
- **Interpretação**: setor histórico opera em 50-70% de utilização — espaço para crescimento com B15/B20.

### KPI Mistura Vigente
- **Fonte**: regulatório · CNPE Resolução vigente.
- **Cálculo**: hardcoded (B15 desde mar/2025, Lei 14.993/24 prevê +1 p.p./ano até B20 em 2030).
- **Objetivo**: contexto institucional crítico para projeções de demanda.

### KPI Be8 · Capacidade total
- **Fonte**: be8energy.com, releases públicos, O Nacional 2024.
- **Cálculo**: soma das duas plantas (Passo Fundo + Marialva) = 1.080 milhões L/ano = 1.080.000 m³/ano.
- **Objetivo**: âncora institucional do painel.

### Ranking de produtores B100
- **Fonte**: ANP painel + curadoria pública dos principais grupos.
- **Cálculo**: ordena por market share % decrescente.
- **Visual**: linha da Be8 destacada em verde Be8 (`--be8-green-2`).
- **Limitação**: quando a ANP não publica share por produtor, mostra apenas capacidade autorizada e marca status PENDENTE.

### Be8 no contexto nacional (card lateral)
- **Fonte**: `be8_profile.json` + manual.
- **Cálculo**: exibe market share histórico (referência pública 2023: 10,9%).
- **Objetivo**: posicionamento competitivo em uma vista.

### Composição matérias-primas B100 (barra empilhada)
- **Fonte**: Anuário Estatístico ANP · planilha "Matérias-primas utilizadas na produção de biodiesel".
- **Cálculo**: parcela % de cada matéria-prima na produção anual.
- **Valores**: 70% óleo soja · 13% gordura bovina · 5% algodão · 4% óleos ácidos · 8% outros (referência histórica média).
- **Objetivo**: mostrar dependência do óleo de soja → justifica a importância do card de óleo soja CBOT na p.02.
- **Limitação**: valores são benchmarks históricos. Para mês corrente real, precisa carregar a planilha mensal da ANP.

---

## Página 05 · Combustíveis ANP

### KPIs Diesel S10, Diesel S500, Gasolina, Etanol (R$/L)
- **Fonte**: ANP · Levantamento Semanal de Preços de Combustíveis (CSV publicado toda 6ª-feira).
- **Cálculo**: média Brasil ponderada por amostra ANP. Variação = vs. semana anterior.
- **Objetivo**: monitorar competitividade do diesel B (com mistura B15) e detectar movimentos da Petrobras/refinarias.
- **Interpretação**: Diesel S10 sobe → benchmark para repasse da Petrobras → cascata para B100 nos próximos leilões.
- **Limitação**: dado **semanal**, não diário. Atualiza só às 6ª-feiras.

### Ranking UFs mais caras / mais baratas (Diesel S10)
- **Fonte**: CSV ANP por UF.
- **Cálculo**: ordena por preço médio. vs. Brasil = (UF − média BR) / média BR × 100.
- **Objetivo**: identificar arbitragem regional e onde a Be8 (RS/PR) está em relação ao Brasil.
- **Interpretação**: Norte/Nordeste tipicamente +5% a +10% acima da média; CO e S próximo da média.

### Preço por região (barras)
- **Fonte**: ANP médias regionais.
- **Cálculo**: média simples das UFs em cada região.
- **Visual**: barras proporcionais com escala min-max.

---

## Página 06 · Comércio Exterior

### Cards Diesel / Óleo Soja / Biodiesel / Farelo / Soja Grão / Metanol (YTD)
- **Fonte**: API oficial **api-comexstat.mdic.gov.br/general** (MDIC).
- **Cálculo**: agrega NCM correspondente por ano atual (YTD). Volume em kg ou ton, valor em US$ FOB.
- **Objetivo**: medir dependência (importações) e oportunidades (exportações) para o setor.
- **NCMs monitorados**:
  - `2710.19.21` Óleo diesel (importação)
  - `3826.00.00` Biodiesel B100 (export/import)
  - `1507.10.00` Óleo soja bruto (exportação)
  - `1507.90.11` Óleo soja refinado (exportação)
  - `2304.00.10` Farelo de soja (exportação)
  - `2905.11.00` Metanol (importação)
  - `1201.90.00` Soja em grão (exportação)
- **Limitação**: ComexStat atualiza com 30-60 dias de defasagem. Os dados de "hoje" são do mês anterior.

### Tabela NCMs monitorados
- **Fonte**: documentação curada.
- **Objetivo**: relevância de cada NCM para a Be8 anotada em uma coluna explícita.

---

## Página 07 · Radar IA

### Síntese executiva (banner)
- **Fonte**: `STATE.insights` (regras determinísticas) + tom calculado por bull − bear.
- **Tom**: ≥+2 → construtivo · ≤−2 → riscos elevados · entre eles → lateral.
- **Objetivo**: leitura de 1 parágrafo apta a abrir e-mail diário.

### Drivers positivos / Drivers negativos
- **Fonte**: `STATE.insights` filtrado por type.
- **Visual**: classe bull (verde) · bear/alert (vermelho/âmbar).

### Ações recomendadas
- **Fonte**: mapeamento heurístico → para cada insight, sugere ação prática (EXPORT, HEDGE, PRICING, ORIGINAÇÃO, COMERCIAL).
- **Limitação**: sugestões automáticas — necessitam aprovação humana antes de execução.

### Tabela de regras (07.B)
- **Fonte**: hardcoded em `scripts.js → buildInsights()`.
- **Auditabilidade**: cada regra é uma condição lógica simples. Diretoria pode pedir para ajustar thresholds ou adicionar regras.

---

## Página 08 · Governança

### Tabela mestra de fontes
- **Fonte**: `status_fontes.json` + metadados curados.
- **Colunas**:
  - Nome · tipo · atualização · custo · endpoint · status atual · linhas baixadas · última verificação.
- **Objetivo**: trilha de auditoria completa — qualquer indicador no painel pode ser rastreado até a fonte primária.
- **Status possíveis**:
  - **Live**: fonte respondeu OK na última execução.
  - **Parcial**: fonte respondeu, mas com warnings (ex.: campo opcional ausente).
  - **Pendente**: fonte ainda não executou (primeiro run).
  - **Erro**: última tentativa falhou — ver `logs/atualizacao.log`.

### Roadmap (3 fases)
- **Objetivo**: alinhar expectativas. Fase 1 já entregue, Fase 2 em pipeline, Fase 3 depende de negociação comercial.

---

## Página 09 · Newsletter Executiva

### Hero editorial (manchete do dia)
- **Fonte**: `noticias.json` · campo `manchete` (notícia de maior `peso` ou primeira ordenada por data).
- **Cálculo**: o coletor `gerar_noticias.py` parseia múltiplos feeds RSS (BiodieselBR, Valor, BroadcastAg, NovaCana, EPBR, AgEconomia, etc.), aplica filtros temáticos e classifica por relevância para Be8.

### Top 5 manchetes do dia
- **Fonte**: `noticias.json` · campo `top5` (ou primeiras 5 de `noticias`).
- **Cada card mostra**:
  - Categoria · fonte · data
  - Título com link externo
  - Resumo (1-2 linhas)
  - Tag `oportunidade | risco | neutro`
  - Nível `alto | médio | baixo`
  - Impacto Be8 (frase curta de leitura crítica para o negócio)

### Radares temáticos (6 cartões)
- **Fonte**: filtragem por palavras-chave sobre `noticias.json`.
- **Categorias**: Regulatório, Combustíveis, Agro, Commodities, Concorrentes, Energia.
- **Cálculo**: cada radar filtra `noticia.titulo + categoria + resumo` por keywords específicas. Mostra até 3 notícias.

### Impacto consolidado para Be8 + ação recomendada
- **Fonte**: `noticias.json` · campos `impacto_consolidado_be8` e `acao_recomendada` (preenchidos pelo coletor ou IA).
- **Fallback**: se ausente, gera resumo automático contando alto/médio/baixo e tags.

---

## Página 10 · Be8 Company Profile

### Hero (tagline + headline + sumário)
- **Fonte**: `be8_profile.json` · campos `tagline`, `identidade`.
- **Conteúdo**: baseado em fontes públicas validadas (be8energy.com, Wikipedia, O Nacional 2024, BiodieselBR).

### KPIs institucionais (4 cards)
- Fundação · Sede · Capacidade B100 · Market Share histórico.
- **Fonte**: `be8_profile.json` · `identidade`, `capacidade_total`, `indicadores_publicos`.

### Plantas industriais
- **Fonte**: `be8_profile.json` · `plantas_industriais`.
- **Conteúdo**:
  - Passo Fundo (RS) · desde 2007 · 540 M L/ano + 1 M t/ano esmagamento
  - Marialva (PR) · desde 2010 · 540 M L/ano

### Cadeia de valor (10 etapas)
- **Fonte**: `be8_profile.json` · `cadeia_valor`.
- **Visual**: cards horizontais numerados, sequência soja → esmagamento → óleo → B100 → comercialização.

### Linha do tempo
- **Fonte**: `be8_profile.json` · `linha_do_tempo`.
- **Marcos públicos**: 2005 fundação · 2007 início produção · 2009 aquisição Marialva · 2016 export · 2023 rebrand BSBIOS → Be8 · 2023 ampliação para 1.080 M L/ano · etc.

### Sustentabilidade & Posicionamento (2 cards)
- **Fonte**: `be8_profile.json` · `sustentabilidade_inovacao`, `posicionamento_competitivo`.
- **Atenção**: apenas itens **documentados publicamente**. Quando uma informação não tem fonte aberta, o JSON traz "não disponível em fonte pública validada".

### Fontes consultadas
- **Fonte**: `be8_profile.json` · `fontes_referencia`.
- **Objetivo**: rastreabilidade completa — cada afirmação tem link externo de origem.

---

## Modo TV

### Configuração persistente
- **Storage**: `localStorage.be8_tv_config` (browser do operador da sala).
- **Campos por página**: enabled, duration (segundos), scroll (true/false), order.
- **Padrão**: todas as páginas habilitadas exceto Governança · duração entre 30-75s · rolagem ativa nas páginas longas.

### Barra inferior
- Relógio atualizado a cada segundo.
- Label da página atual.
- Barra de progresso (verde Be8) animada por interpolação linear.
- Botões: Pausar / Próxima / Sair.

### Atalhos de teclado
- `Esc` · sair do modo TV
- `Space` · pausar/retomar
- `→` · pular para próxima página

---

## Notas finais

**Atualização das séries**: 90 dias é o padrão. Para histórico mais longo, mudar a constante em cada coletor (`baixar_cambio.py`, `baixar_commodities.py`).

**Fuso horário**: o painel usa `BRT` (UTC-3). O agente é agnóstico ao fuso, mas o cron do GitHub Actions roda em UTC.

**Acessibilidade**: cores foram escolhidas com contraste AA (verde Be8 sobre azul-marinho · 4.7:1). Ícones têm fallback textual.

**Performance**: o painel pesa ~75 KB (HTML+CSS+JS) sem dados. Cada JSON varia de 5-50 KB. Carrega <1s mesmo em 3G.

**Privacidade**: o painel não carrega nenhum tracker, analytics, fonte externa não-essencial, ou pixel de terceiros. Apenas Google Fonts via CSS.
