/* =====================================================================
   BENCH-BE8 · Market Intelligence Platform
   scripts.js · v2.4
   ---------------------------------------------------------------------
   Arquitetura defensiva:
   - safeSetText / safeFetch / updateSourceStatus / renderEmptyState
   - try/catch por módulo de renderização (erro em uma fonte NÃO derruba
     o restante do painel)
   - Logs claros no console com prefixo [BENCH-BE8]
   - Schema padronizado dos JSONs em /data:
     { fonte, status: ok|fallback|erro|indisponivel,
       ultima_atualizacao, dados, erro }
   ===================================================================== */

'use strict';

/* ---------- Helpers DOM ---------- */
const $  = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/**
 * safeSetText — atualiza textContent SEM derrubar a página se o ID
 * não existir. Loga warn no console pra debug.
 */
function safeSetText(id, value, fallback = '—') {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`[BENCH-BE8] Elemento não encontrado: #${id}`);
    return false;
  }
  el.textContent = (value === null || value === undefined || value === '') ? fallback : value;
  return true;
}

/**
 * safeSetHTML — variante que aceita innerHTML (use só com dados sanitizados,
 * tipicamente textos pré-formatados do agente Python).
 */
function safeSetHTML(id, html, fallback = '<span class="muted">—</span>') {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`[BENCH-BE8] Elemento não encontrado: #${id}`);
    return false;
  }
  el.innerHTML = (html === null || html === undefined || html === '') ? fallback : html;
  return true;
}

/**
 * safeFetch — fetch com timeout, no-cache e tratamento de 404 silencioso.
 * Retorna null em qualquer falha. NUNCA quebra o caller.
 */
async function safeFetch(url, opts = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), opts.timeout || 15000);
  try {
    const resp = await fetch(url, {
      cache: 'no-store',
      signal: ctrl.signal,
      ...opts,
    });
    clearTimeout(timer);
    if (!resp.ok) {
      console.warn(`[BENCH-BE8] safeFetch · ${url} · HTTP ${resp.status}`);
      return null;
    }
    return await resp.json();
  } catch (err) {
    clearTimeout(timer);
    console.warn(`[BENCH-BE8] safeFetch · ${url} · falhou:`, err.message);
    return null;
  }
}

/**
 * validateDataSchema — confere se o JSON segue o schema padrão da Be8.
 */
function validateDataSchema(json, requiredFields = ['fonte', 'status', 'ultima_atualizacao']) {
  if (!json || typeof json !== 'object') return false;
  return requiredFields.every((k) => k in json);
}

/**
 * updateSourceStatus — atualiza pingo de status e tooltip.
 * status: 'ok' | 'fallback' | 'erro' | 'indisponivel' | 'pendente'
 */
function updateSourceStatus(id, status, label = null) {
  const el = document.getElementById(id);
  if (!el) {
    console.warn(`[BENCH-BE8] Status não encontrado: #${id}`);
    return;
  }
  el.classList.remove('src-pending', 'src-live', 'src-fallback', 'src-error', 'src-na');
  const map = {
    ok:           { cls: 'src-live',     txt: label || 'AO VIVO' },
    fallback:     { cls: 'src-fallback', txt: label || 'FALLBACK' },
    erro:         { cls: 'src-error',    txt: label || 'ERRO' },
    indisponivel: { cls: 'src-na',       txt: label || 'INDISPONÍVEL' },
    pendente:     { cls: 'src-pending',  txt: label || '—' },
  };
  const cfg = map[status] || map.pendente;
  el.classList.add(cfg.cls);
  el.textContent = cfg.txt;
}

/**
 * renderEmptyState — preenche container vazio com mensagem padrão.
 */
function renderEmptyState(id, message = 'Sem dados disponíveis') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<div class="empty-state" style="padding:24px;text-align:center;color:var(--be8-dim);font-size:13px;font-style:italic;">${message}</div>`;
}

/* ---------- Formatadores ---------- */
const fmt = {
  brl:   (v, d = 4) => (v == null || isNaN(v)) ? '—' : 'R$ ' + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }),
  usd:   (v, d = 2) => (v == null || isNaN(v)) ? '—' : '$ '  + Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }),
  cent:  (v, d = 0) => (v == null || isNaN(v)) ? '—' : '¢ '  + Number(v).toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d }),
  num:   (v, d = 1) => (v == null || isNaN(v)) ? '—' : Number(v).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }),
  pct:   (v, d = 2) => (v == null || isNaN(v)) ? '—' : (Number(v) >= 0 ? '+' : '') + Number(v).toLocaleString('pt-BR', { minimumFractionDigits: d, maximumFractionDigits: d }) + '%',
  date:  (s) => {
    if (!s) return '—';
    try {
      const d = new Date(s);
      if (isNaN(d)) return s;
      return d.toLocaleDateString('pt-BR') + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    } catch { return s; }
  },
};

/**
 * applyDelta — aplica valor de variação e classe (up/down/flat) num elemento.
 */
function applyDelta(id, delta) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.remove('flat', 'up', 'down');
  if (delta == null || isNaN(delta)) {
    el.textContent = '—';
    el.classList.add('flat');
    return;
  }
  const v = Number(delta);
  el.textContent = fmt.pct(v);
  if (v > 0.001) el.classList.add('up');
  else if (v < -0.001) el.classList.add('down');
  else el.classList.add('flat');
}

/* =====================================================================
   STATE global
   ===================================================================== */
const STATE = {
  cambio:            null,
  commodities:       null,
  conab:             null,
  anp_combustiveis:  null,
  anp_b100:          null,
  anp_vendas:        null,
  comex:             null,
  noticias:          null,
  be8_profile:       null,
  status_fontes:     null,
  usda:              null,
  governance:        null,
  insights:          [],
  vendas_produto_ativo: 'diesel_b',
};

/* =====================================================================
   NAVEGAÇÃO ENTRE ABAS
   ===================================================================== */
function bindNavigation() {
  $$('.nav-tab').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.page;
      if (!target) return;
      $$('.nav-tab').forEach((b) => b.classList.remove('active'));
      $$('.page').forEach((p) => p.classList.remove('active'));
      btn.classList.add('active');
      const pageEl = document.getElementById('page-' + target);
      if (pageEl) pageEl.classList.add('active');
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  });
}

/* =====================================================================
   RELÓGIO de sessão
   ===================================================================== */
function setSessionClock() {
  const now = new Date();
  safeSetText('session-date', now.toLocaleDateString('pt-BR', { weekday: 'long', day: '2-digit', month: 'short', year: 'numeric' }));
  safeSetText('session-time', now.toLocaleTimeString('pt-BR'));
  safeSetText('tv-clock', now.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }));
}

/* =====================================================================
   CARREGAMENTO de todos os JSONs
   ===================================================================== */
async function reloadAllData() {
  console.log('[BENCH-BE8] reloadAllData · iniciando');
  const t0 = performance.now();

  // Todas em paralelo, com safeFetch (nenhuma derruba as outras)
  const [
    cambio, commodities, conab,
    anpComb, anpB100, anpVendas,
    comex, noticias, profile,
    status, usda, governance,
  ] = await Promise.all([
    safeFetch('data/cambio.json'),
    safeFetch('data/commodities.json'),
    safeFetch('data/conab_graos.json'),
    safeFetch('data/anp_combustiveis.json'),
    safeFetch('data/anp_b100.json'),
    safeFetch('data/anp_vendas.json'),
    safeFetch('data/comex.json'),
    safeFetch('data/noticias.json'),
    safeFetch('data/be8_profile.json'),
    safeFetch('data/status_fontes.json'),
    safeFetch('data/usda_benchmarks.json'),
    safeFetch('data/governance.json'),
  ]);

  STATE.cambio           = cambio;
  STATE.commodities      = commodities;
  STATE.conab            = conab;
  STATE.anp_combustiveis = anpComb;
  STATE.anp_b100         = anpB100;
  STATE.anp_vendas       = anpVendas;
  STATE.comex            = comex;
  STATE.noticias         = noticias;
  STATE.be8_profile      = profile;
  STATE.status_fontes    = status;
  STATE.usda             = usda;
  STATE.governance       = governance;

  // Cada render é independente — try/catch por módulo
  const modules = [
    ['Câmbio',         renderCambio],
    ['Commodities',    renderCommodities],
    ['Charts 90d',     renderCharts90d],
    ['Grãos/CONAB',    renderConab],
    ['ANP Biodiesel',  renderBiodieselANP],
    ['ANP Combustíveis', renderANPCombustiveis],
    ['ComexStat',      renderComex],
    ['Radar IA',       renderRadarIA],
    ['Newsletter',     renderNewsletter],
    ['Governança',     renderGovernance],
    ['Be8 Profile',    renderBe8Profile],
    ['Vendas & Mapa',  renderVendasMapa],
    ['Benchmark USDA', renderUSDA],
    ['Exec Summary',   renderExecutiveSummary],
    ['Ticker',         renderTicker],
  ];

  for (const [name, fn] of modules) {
    try {
      fn();
    } catch (err) {
      console.error(`[BENCH-BE8] Falha no módulo ${name}:`, err);
    }
  }

  // Footer build timestamp
  const buildTime = STATE.status_fontes?.ultima_atualizacao
                 || STATE.cambio?.ultima_atualizacao
                 || new Date().toISOString();
  safeSetText('footer-build', 'build · ' + fmt.date(buildTime));
  safeSetText('governance-last', 'build ' + fmt.date(buildTime));

  const t1 = performance.now();
  console.log(`[BENCH-BE8] reloadAllData · concluído em ${(t1 - t0).toFixed(0)}ms`);
}

/* =====================================================================
   RENDER · Câmbio (USD, EUR)
   ===================================================================== */
function renderCambio() {
  const data = STATE.cambio;

  // Sem dados → status indisponível e sai
  if (!data || !validateDataSchema(data)) {
    ['usd', 'eur'].forEach((k) => updateSourceStatus(`status-${k}`, 'indisponivel'));
    return;
  }
  if (data.status === 'erro') {
    ['usd', 'eur'].forEach((k) => updateSourceStatus(`status-${k}`, 'erro'));
    return;
  }

  const usd = data.dados?.usd || data.dados?.USD || {};
  const eur = data.dados?.eur || data.dados?.EUR || {};

  // USD card
  if (usd.cotacao != null) {
    safeSetText('usd-value', fmt.brl(usd.cotacao, 4));
    applyDelta('usd-delta', usd.variacao_pct);
    updateSourceStatus('status-usd', data.status === 'fallback' ? 'fallback' : 'ok', 'BCB');
  } else {
    updateSourceStatus('status-usd', 'indisponivel');
  }

  // EUR card
  if (eur.cotacao != null) {
    safeSetText('eur-value', fmt.brl(eur.cotacao, 4));
    applyDelta('eur-delta', eur.variacao_pct);
    updateSourceStatus('status-eur', data.status === 'fallback' ? 'fallback' : 'ok', 'BCB');
  } else {
    updateSourceStatus('status-eur', 'indisponivel');
  }
}

/* =====================================================================
   RENDER · Commodities (Brent, Soja, Milho, Trigo, Óleo de Soja, WTI)
   ===================================================================== */
const COMMODITY_KEYS = ['brent', 'soja', 'milho', 'trigo', 'oleo_soja', 'wti'];

function renderCommodities() {
  const data = STATE.commodities;

  if (!data || !validateDataSchema(data)) {
    COMMODITY_KEYS.forEach((k) => updateSourceStatus(`status-${k}`, 'indisponivel'));
    renderEmptyState('commodities-tbody', 'Coletor de commodities indisponível.');
    return;
  }

  const items = data.dados || {};

  COMMODITY_KEYS.forEach((k) => {
    const it = items[k];
    if (!it || it.cotacao == null) {
      updateSourceStatus(`status-${k}`, 'indisponivel');
      return;
    }
    // Formatação varia conforme unidade
    const unidade = (it.unidade || '').toLowerCase();
    let valueText;
    if (unidade.includes('bbl') || k === 'brent' || k === 'wti') {
      valueText = fmt.usd(it.cotacao, 2);
    } else {
      valueText = fmt.cent(it.cotacao, 0);
    }
    safeSetText(`${k}-value`, valueText);
    applyDelta(`${k}-delta`, it.variacao_pct);
    updateSourceStatus(`status-${k}`, data.status === 'fallback' ? 'fallback' : 'ok', 'Yahoo');
  });

  // Tabela completa
  const tbody = document.getElementById('commodities-tbody');
  if (tbody) {
    const allKeys = Object.keys(items);
    if (allKeys.length === 0) {
      renderEmptyState('commodities-tbody', 'Nenhum ativo coletado neste ciclo.');
    } else {
      tbody.innerHTML = allKeys.map((k) => {
        const it = items[k] || {};
        const cls = (it.variacao_pct > 0) ? 'up' : (it.variacao_pct < 0 ? 'down' : 'flat');
        return `<tr>
          <td><strong>${it.nome || k.toUpperCase()}</strong></td>
          <td>${it.mercado || '—'}</td>
          <td class="num">${it.cotacao != null ? Number(it.cotacao).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:4}) : '—'}</td>
          <td class="num">${it.cotacao_anterior != null ? Number(it.cotacao_anterior).toLocaleString('en-US', {minimumFractionDigits:2,maximumFractionDigits:4}) : '—'}</td>
          <td class="num delta ${cls}">${it.variacao_pct != null ? fmt.pct(it.variacao_pct) : '—'}</td>
          <td class="num delta ${(it.variacao_7d>0)?'up':(it.variacao_7d<0?'down':'flat')}">${it.variacao_7d != null ? fmt.pct(it.variacao_7d) : '—'}</td>
          <td class="num delta ${(it.variacao_30d>0)?'up':(it.variacao_30d<0?'down':'flat')}">${it.variacao_30d != null ? fmt.pct(it.variacao_30d) : '—'}</td>
          <td><span class="src-status src-live">OK</span></td>
        </tr>`;
      }).join('');
    }
  }
}

/* =====================================================================
   RENDER · Charts 90d (sparklines + área)
   Usa SVG inline puro — zero dependência externa.
   ===================================================================== */
function renderSparkline(containerId, points, color = '#7ad9c2') {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!points || points.length < 2) {
    el.innerHTML = '';
    return;
  }
  const w = el.clientWidth || 240;
  const h = el.clientHeight || 40;
  const vals = points.map((p) => Number(p.valor || p.value || p[1] || p));
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const stepX = w / (vals.length - 1);
  const pts = vals.map((v, i) => `${(i * stepX).toFixed(1)},${(h - ((v - min) / range) * h * 0.85 - h * 0.075).toFixed(1)}`).join(' ');
  el.innerHTML = `<svg width="${w}" height="${h}" style="display:block">
    <polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.5"/>
  </svg>`;
}

function renderAreaChart(containerId, points, color = '#7ad9c2') {
  const el = document.getElementById(containerId);
  if (!el) return;
  if (!points || points.length < 2) {
    renderEmptyState(containerId, 'Série histórica indisponível.');
    return;
  }
  const w = el.clientWidth || 480;
  const h = el.clientHeight || 220;
  const padding = { l: 40, r: 12, t: 12, b: 26 };
  const innerW = w - padding.l - padding.r;
  const innerH = h - padding.t - padding.b;
  const vals = points.map((p) => Number(p.valor || p.value || p[1] || p));
  const labels = points.map((p) => p.data || p.date || p[0] || '');
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const range = max - min || 1;
  const stepX = innerW / (vals.length - 1);

  const ptList = vals.map((v, i) => ({
    x: padding.l + i * stepX,
    y: padding.t + innerH - ((v - min) / range) * innerH,
  }));
  const linePath = ptList.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const areaPath = linePath
    + ` L${ptList[ptList.length - 1].x.toFixed(1)},${(padding.t + innerH).toFixed(1)}`
    + ` L${ptList[0].x.toFixed(1)},${(padding.t + innerH).toFixed(1)} Z`;

  // Labels Y (3 ticks)
  const yTicks = [min, (min + max) / 2, max];
  const yLabels = yTicks.map((v) => {
    const y = padding.t + innerH - ((v - min) / range) * innerH;
    return `<text x="${padding.l - 6}" y="${y + 4}" text-anchor="end" font-size="10" fill="#8a99a3" font-family="JetBrains Mono, monospace">${v.toFixed(2)}</text>
            <line x1="${padding.l}" y1="${y}" x2="${w - padding.r}" y2="${y}" stroke="rgba(168,189,201,0.08)" stroke-dasharray="2 3"/>`;
  }).join('');

  // Label X (extremos + meio)
  const xIdx = [0, Math.floor(vals.length / 2), vals.length - 1];
  const xLabels = xIdx.map((i) => {
    const lbl = (labels[i] || '').slice(5);   // pega só MM-DD
    const x = padding.l + i * stepX;
    return `<text x="${x}" y="${h - 8}" text-anchor="middle" font-size="10" fill="#8a99a3" font-family="JetBrains Mono, monospace">${lbl}</text>`;
  }).join('');

  el.innerHTML = `<svg width="${w}" height="${h}" style="display:block">
    <defs>
      <linearGradient id="grad-${containerId}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${color}" stop-opacity="0.35"/>
        <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
      </linearGradient>
    </defs>
    ${yLabels}
    <path d="${areaPath}" fill="url(#grad-${containerId})"/>
    <path d="${linePath}" fill="none" stroke="${color}" stroke-width="1.6"/>
    ${xLabels}
  </svg>`;
}

function renderCharts90d() {
  const data = STATE.commodities;
  const cambio = STATE.cambio;

  // Sparklines dos KPIs
  if (cambio?.dados) {
    renderSparkline('usd-spark', cambio.dados.usd?.serie_90d, '#7ad9c2');
    renderSparkline('eur-spark', cambio.dados.eur?.serie_90d, '#7ad9c2');
  }
  if (data?.dados) {
    renderSparkline('brent-spark', data.dados.brent?.serie_90d, '#ffb86b');
    renderSparkline('soja-spark',  data.dados.soja?.serie_90d,  '#7ad9c2');
  }

  // Charts grandes (aba 02)
  renderAreaChart('usd-90-chart',       cambio?.dados?.usd?.serie_90d,       '#7ad9c2');
  renderAreaChart('brent-90-chart',     data?.dados?.brent?.serie_90d,       '#ffb86b');
  renderAreaChart('oleo_soja-90-chart', data?.dados?.oleo_soja?.serie_90d,   '#a8d57a');
  renderAreaChart('soja-90-chart',      data?.dados?.soja?.serie_90d,        '#7ad9c2');
}

/* =====================================================================
   RENDER · Grãos / CONAB
   ===================================================================== */
function renderConab() {
  const data = STATE.conab;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('conab-status', 'indisponivel', 'CONAB · indisponível');
    updateSourceStatus('status-conab-soja', 'indisponivel');
    return;
  }
  const safras = data.dados?.safras || {};

  // Cards principais (soja, milho, trigo)
  ['soja', 'milho', 'trigo'].forEach((g) => {
    const s = safras[g];
    if (!s) {
      safeSetText(`${g}-safra-prod`, '—');
      return;
    }
    safeSetText(`${g}-safra-prod`, fmt.num(s.producao_mt, 1));
    applyDelta(`${g}-safra-delta`, s.variacao_pct_ano_anterior);
  });

  updateSourceStatus('conab-status', 'ok', 'CONAB · ' + (data.dados?.safra_ref || 'safra atual'));
  updateSourceStatus('status-conab-soja', 'ok', 'CONAB');

  // Rankings UF
  const ufs = data.dados?.ufs || {};
  ['soja', 'milho'].forEach((g) => {
    const tbody = document.getElementById(`${g}-uf-tbody`);
    if (!tbody) return;
    const ranking = ufs[g] || [];
    if (ranking.length === 0) {
      renderEmptyState(`${g}-uf-tbody`, 'Ranking de UFs indisponível.');
      return;
    }
    tbody.innerHTML = ranking.slice(0, 10).map((uf, i) =>
      `<tr><td>${i + 1}</td><td><strong>${uf.uf}</strong></td><td class="num">${fmt.num(uf.producao_mt, 2)}</td><td class="num">${fmt.num(uf.share_pct, 1)}%</td></tr>`
    ).join('');
    safeSetText(`${g}-uf-meta`, `${ranking.length} UFs`);
  });
}

/* =====================================================================
   RENDER · ANP Biodiesel B100
   ===================================================================== */
function renderBiodieselANP() {
  const data = STATE.anp_b100;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('anp-b100-status', 'indisponivel');
    renderEmptyState('biodiesel-rank-tbody', 'Coletor ANP B100 indisponível.');
    return;
  }
  const d = data.dados || {};
  safeSetText('b100-prod-total', fmt.num(d.producao_total_m3, 0) + ' m³');
  applyDelta('b100-prod-delta', d.variacao_pct_ano_anterior);
  safeSetText('b100-mistura', d.mistura_atual || '—');
  safeSetText('b100-cap-total', fmt.num(d.capacidade_total_m3, 0) + ' m³');
  safeSetText('b100-util', fmt.num(d.utilizacao_pct, 1) + '%');

  // Ranking
  const tbody = document.getElementById('biodiesel-rank-tbody');
  if (tbody && Array.isArray(d.ranking)) {
    if (d.ranking.length === 0) {
      renderEmptyState('biodiesel-rank-tbody', 'Ranking ANP indisponível.');
    } else {
      tbody.innerHTML = d.ranking.slice(0, 15).map((p, i) =>
        `<tr><td>${i + 1}</td><td><strong>${p.produtor}</strong></td><td>${p.uf || '—'}</td><td class="num">${fmt.num(p.producao_m3, 0)}</td><td class="num">${fmt.num(p.share_pct, 1)}%</td></tr>`
      ).join('');
      safeSetText('b100-rank-meta', `${d.ranking.length} produtores · ${d.ref_mes || ''}`);
    }
  }
  updateSourceStatus('anp-b100-status', 'ok', 'ANP B100');
}

/* =====================================================================
   RENDER · ANP Combustíveis (preços)
   ===================================================================== */
function renderANPCombustiveis() {
  const data = STATE.anp_combustiveis;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('anp-status', 'indisponivel');
    updateSourceStatus('status-anp-s10', 'indisponivel');
    return;
  }
  const d = data.dados || {};

  safeSetText('anp-s10', fmt.brl(d.diesel_s10?.preco_medio, 3));
  applyDelta('anp-s10-delta', d.diesel_s10?.variacao_pct);
  safeSetText('anp-s500', fmt.brl(d.diesel_s500?.preco_medio, 3));
  applyDelta('anp-s500-delta', d.diesel_s500?.variacao_pct);
  safeSetText('anp-gasolina', fmt.brl(d.gasolina?.preco_medio, 3));
  applyDelta('anp-gasolina-delta', d.gasolina?.variacao_pct);
  safeSetText('anp-etanol', fmt.brl(d.etanol?.preco_medio, 3));
  applyDelta('anp-etanol-delta', d.etanol?.variacao_pct);

  // Tabelas baratas/caras
  const baratas = d.s10_baratas || [];
  const caras   = d.s10_caras   || [];
  const tbBar = document.getElementById('anp-s10-baratas-tbody');
  const tbCar = document.getElementById('anp-s10-caras-tbody');
  if (tbBar) {
    tbBar.innerHTML = baratas.slice(0, 10).map((r) =>
      `<tr><td><strong>${r.municipio}</strong></td><td>${r.uf}</td><td class="num">${fmt.brl(r.preco, 3)}</td></tr>`
    ).join('') || `<tr><td colspan="3" style="text-align:center;color:var(--be8-dim);font-style:italic;">Sem dados</td></tr>`;
  }
  if (tbCar) {
    tbCar.innerHTML = caras.slice(0, 10).map((r) =>
      `<tr><td><strong>${r.municipio}</strong></td><td>${r.uf}</td><td class="num">${fmt.brl(r.preco, 3)}</td></tr>`
    ).join('') || `<tr><td colspan="3" style="text-align:center;color:var(--be8-dim);font-style:italic;">Sem dados</td></tr>`;
  }

  updateSourceStatus('anp-status', 'ok', 'ANP · ' + (d.ref_semana || ''));
  updateSourceStatus('status-anp-s10', 'ok', 'ANP');
}

/* =====================================================================
   RENDER · ComexStat
   ===================================================================== */
function renderComex() {
  const data = STATE.comex;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('comex-status', 'indisponivel');
    return;
  }
  const d = data.dados || {};
  safeSetText('comex-soja-vol',      fmt.num(d.soja?.volume_kg / 1e9, 2) + ' Mt');
  safeSetText('comex-farelo-vol',    fmt.num(d.farelo?.volume_kg / 1e9, 2) + ' Mt');
  safeSetText('comex-oleo-vol',      fmt.num(d.oleo?.volume_kg / 1e9, 2) + ' Mt');
  safeSetText('comex-biodiesel-vol', fmt.num(d.biodiesel?.volume_kg / 1e6, 0) + ' kt');
  safeSetText('comex-diesel-vol',    fmt.num(d.diesel?.volume_kg / 1e9, 2) + ' Mt');
  safeSetText('comex-metanol-vol',   fmt.num(d.metanol?.volume_kg / 1e6, 0) + ' kt');
  updateSourceStatus('comex-status', 'ok', 'MDIC · ' + (d.ref_ano || ''));
}

/* =====================================================================
   RENDER · Newsletter
   ===================================================================== */
function renderNewsletter() {
  const data = STATE.noticias;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('news-status', 'indisponivel');
    safeSetText('news-hero-headline', 'Coletor de notícias indisponível neste ciclo.');
    renderEmptyState('news-top5', 'Newsletter sem coleta hoje.');
    return;
  }
  const d = data.dados || {};

  // Hero
  if (d.hero) {
    safeSetText('news-hero-eyebrow', d.hero.eyebrow || 'EDIÇÃO DO DIA · BE8');
    safeSetText('news-hero-headline', d.hero.headline || '—');
    safeSetText('news-hero-meta', d.hero.meta || '—');
  }

  // Top 5
  const top5El = document.getElementById('news-top5');
  if (top5El && Array.isArray(d.top5)) {
    if (d.top5.length === 0) {
      renderEmptyState('news-top5', 'Nenhuma manchete coletada.');
    } else {
      top5El.innerHTML = d.top5.map((n, i) => renderNewsCard(n, i + 1)).join('');
    }
  }

  // Radares temáticos
  const radares = ['regulatorio', 'combustiveis', 'agro', 'commodities', 'concorrentes', 'energia'];
  radares.forEach((tema) => {
    const id = `news-radar-${tema}`;
    const list = d.radares?.[tema] || [];
    const el = document.getElementById(id);
    if (!el) return;
    if (list.length === 0) {
      renderEmptyState(id, 'Sem notícias nesta categoria.');
    } else {
      el.innerHTML = list.slice(0, 4).map(renderNewsItemMini).join('');
    }
  });

  safeSetHTML('news-impacto-be8', d.impacto_be8 || '<em style="color:var(--be8-dim)">Análise consolidada em geração…</em>');
  updateSourceStatus('news-status', 'ok', 'Newsletter · ' + (data.ultima_atualizacao ? fmt.date(data.ultima_atualizacao) : ''));
}

function renderNewsCard(n, idx) {
  return `<div class="news-item">
    <div class="news-rank">#${idx}</div>
    <div class="news-body">
      <div class="news-tag">${n.tag || 'NOTÍCIA'}</div>
      <div class="news-headline"><strong>${n.titulo || '—'}</strong></div>
      <div class="news-desc">${n.resumo || ''}</div>
      <div class="news-foot">
        <span class="news-source">${n.fonte || '—'} · ${n.data || ''}</span>
        ${n.url ? `<a href="${n.url}" target="_blank" rel="noopener" class="news-link">Abrir notícia →</a>` : ''}
      </div>
    </div>
  </div>`;
}

function renderNewsItemMini(n) {
  return `<div class="news-mini">
    <div class="news-mini-title">${n.titulo || '—'}</div>
    <div class="news-mini-foot">
      <span>${n.fonte || '—'} · ${n.data || ''}</span>
      ${n.url ? `<a href="${n.url}" target="_blank" rel="noopener">↗</a>` : ''}
    </div>
  </div>`;
}

/* =====================================================================
   RENDER · Governança (tabela de fontes)
   ===================================================================== */
function renderGovernance() {
  const data = STATE.governance;
  const tbody = document.getElementById('governance-tbody');
  if (!tbody) return;

  if (!data || !data.fontes || !Array.isArray(data.fontes)) {
    renderEmptyState('governance-tbody', 'Manifesto de governança indisponível.');
    return;
  }

  tbody.innerHTML = data.fontes.map((f) => {
    const statusCls = {
      ok:           'src-live',
      fallback:     'src-fallback',
      erro:         'src-error',
      indisponivel: 'src-na',
      pendente:     'src-pending',
    }[f.status] || 'src-pending';
    const statusTxt = {
      ok:           'AO VIVO',
      fallback:     'FALLBACK',
      erro:         'ERRO',
      indisponivel: 'INDISPONÍVEL',
      pendente:     'EM DEV',
    }[f.status] || '—';
    return `<tr>
      <td><strong>${f.fonte}</strong></td>
      <td>${f.tipo}</td>
      <td>${f.atualizacao}</td>
      <td>${f.custo}</td>
      <td><code style="font-size:11px;">${f.endpoint || '—'}</code></td>
      <td><span class="src-status ${statusCls}">${statusTxt}</span></td>
      <td class="num">${f.linhas != null ? fmt.num(f.linhas, 0) : '—'}</td>
      <td>${f.ultima_verificacao ? fmt.date(f.ultima_verificacao) : '—'}</td>
    </tr>`;
  }).join('');
}

/* =====================================================================
   RENDER · Be8 Profile
   ===================================================================== */
function renderBe8Profile() {
  const data = STATE.be8_profile;
  if (!data || !data.dados) return;
  const d = data.dados;
  // Mapeamento campo→ID
  const map = {
    'profile-tagline':         d.tagline,
    'profile-headline':        d.headline,
    'profile-summary':         d.summary,
    'profile-fundacao':        d.fundacao,
    'profile-fundacao-ctx':    d.fundacao_contexto,
    'profile-sede':            d.sede,
    'profile-capacidade':      d.capacidade,
    'profile-share':           d.share_mercado,
    'profile-share-ctx':       d.share_contexto,
    'profile-presenca':        d.presenca,
    'profile-missao':          d.missao,
    'profile-posicionamento':  d.posicionamento,
    'profile-papel':           d.papel_estrategico,
    'be8-cap':                 d.capacidade,
  };
  Object.entries(map).forEach(([id, val]) => safeSetText(id, val));

  // Listas richas (HTML)
  const listas = {
    'profile-plantas':         d.plantas_html,
    'profile-produtos':        d.produtos_html,
    'profile-indicadores':     d.indicadores_html,
    'profile-timeline':        d.timeline_html,
    'profile-cadeia':          d.cadeia_html,
    'profile-sustentabilidade': d.sustentabilidade_html,
    'profile-fontes':          d.fontes_html,
  };
  Object.entries(listas).forEach(([id, html]) => safeSetHTML(id, html));
}

/* =====================================================================
   RENDER · Vendas & Mapa (aba 11)
   ===================================================================== */
function renderVendasMapa() {
  const data = STATE.anp_vendas;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('vendas-status', 'indisponivel');
    renderEmptyState('vendas-rank-tbody', 'Coletor de vendas ANP indisponível.');
    return;
  }
  const d = data.dados || {};

  // KPIs por produto
  safeSetText('vendas-diesel-total',   fmt.num(d.diesel_b?.total_m3 / 1e3, 1) + ' mil m³');
  safeSetText('vendas-diesel-preco',   fmt.brl(d.diesel_b?.preco_medio, 3));
  safeSetText('vendas-gasolina-total', fmt.num(d.gasolina?.total_m3 / 1e3, 1) + ' mil m³');
  safeSetText('vendas-gasolina-preco', fmt.brl(d.gasolina?.preco_medio, 3));
  safeSetText('vendas-etanol-total',   fmt.num(d.etanol?.total_m3 / 1e3, 1) + ' mil m³');
  safeSetText('vendas-etanol-preco',   fmt.brl(d.etanol?.preco_medio, 3));

  // Ranking distribuidoras
  const ranking = d.ranking_distribuidoras || [];
  const tbody = document.getElementById('vendas-rank-tbody');
  if (tbody) {
    if (ranking.length === 0) {
      renderEmptyState('vendas-rank-tbody', 'Ranking indisponível neste ciclo.');
    } else {
      tbody.innerHTML = ranking.slice(0, 10).map((p, i) =>
        `<tr><td>${i + 1}</td><td><strong>${p.distribuidora}</strong></td><td class="num">${fmt.num(p.volume_m3 / 1e3, 1)}</td><td class="num">${fmt.num(p.share_pct, 1)}%</td></tr>`
      ).join('');
      safeSetText('vendas-rank-meta', `${ranking.length} distribuidoras · ${d.ref_mes || ''}`);
    }
  }

  updateSourceStatus('vendas-status', 'ok', 'ANP · ' + (d.ref_mes || ''));
}

/* =====================================================================
   RENDER · USDA Benchmark Global (aba 12)
   ===================================================================== */
function renderUSDA() {
  const data = STATE.usda;
  if (!data || !validateDataSchema(data) || data.status === 'erro') {
    updateSourceStatus('usda-status', 'indisponivel');
    renderEmptyState('usda-rank-soja-tbody', 'USDA WASDE indisponível.');
    renderEmptyState('usda-rank-biod-tbody', 'USDA Biodiesel indisponível.');
    return;
  }
  const d = data.dados || {};
  safeSetText('usda-safra-ref', d.safra_ref || '—');
  safeSetText('usda-soja-mundo',   fmt.num(d.soja_mundo_mt, 1) + ' Mt');
  safeSetText('usda-brasil-soja',  fmt.num(d.brasil_soja_mt, 1) + ' Mt');
  safeSetText('usda-brasil-soja-ctx', d.brasil_soja_contexto || '');
  safeSetText('usda-biod-mundo',   fmt.num(d.biodiesel_mundo_mt, 1) + ' Mt');
  safeSetText('usda-brasil-biod',  fmt.num(d.brasil_biodiesel_mt, 1) + ' Mt');
  safeSetText('usda-brasil-biod-ctx', d.brasil_biodiesel_contexto || '');

  // Rankings
  const sojaRk = d.ranking_soja || [];
  const biodRk = d.ranking_biodiesel || [];
  const tbSoja = document.getElementById('usda-rank-soja-tbody');
  const tbBiod = document.getElementById('usda-rank-biod-tbody');
  if (tbSoja) {
    tbSoja.innerHTML = sojaRk.length
      ? sojaRk.map((p, i) => `<tr style="${p.pais === 'Brasil' ? 'background:rgba(122,217,194,0.07)' : ''}"><td>${i + 1}</td><td><strong>${p.pais}</strong></td><td class="num">${fmt.num(p.producao_mt, 1)}</td><td class="num">${fmt.num(p.share_pct, 1)}%</td></tr>`).join('')
      : `<tr><td colspan="4" style="text-align:center;color:var(--be8-dim);font-style:italic;">Sem dados</td></tr>`;
  }
  if (tbBiod) {
    tbBiod.innerHTML = biodRk.length
      ? biodRk.map((p, i) => `<tr style="${p.pais === 'Brasil' ? 'background:rgba(122,217,194,0.07)' : ''}"><td>${i + 1}</td><td><strong>${p.pais}</strong></td><td class="num">${fmt.num(p.producao_mt, 1)}</td><td class="num">${fmt.num(p.share_pct, 1)}%</td></tr>`).join('')
      : `<tr><td colspan="4" style="text-align:center;color:var(--be8-dim);font-style:italic;">Sem dados</td></tr>`;
  }

  updateSourceStatus('usda-status', 'ok', 'USDA · ' + (d.safra_ref || ''));
}

/* =====================================================================
   RENDER · Resumo Executivo + Radar IA
   ===================================================================== */
function renderExecutiveSummary() {
  const summary = STATE.status_fontes?.exec_summary
              || STATE.noticias?.dados?.impacto_be8
              || 'Aguardando consolidação de dados…';
  safeSetText('exec-summary', stripHtml(summary));

  // Status das fontes (lateral)
  renderSourcesSummary();
}

function stripHtml(s) {
  if (!s) return '';
  return String(s).replace(/<[^>]+>/g, '');
}

function renderSourcesSummary() {
  const el = document.getElementById('sources-summary');
  if (!el) return;
  const fontes = STATE.governance?.fontes || [];
  if (fontes.length === 0) {
    el.innerHTML = '<div style="color:var(--be8-dim);font-style:italic;">Aguardando governança…</div>';
    safeSetText('sources-meta', '—');
    return;
  }
  const counts = fontes.reduce((acc, f) => {
    acc[f.status] = (acc[f.status] || 0) + 1;
    return acc;
  }, {});
  const total = fontes.length;
  const ok = counts.ok || 0;

  el.innerHTML = fontes.slice(0, 8).map((f) => {
    const dot = {
      ok: '#7ad9c2', fallback: '#ffb86b', erro: '#ff8585',
      indisponivel: '#8a99a3', pendente: '#a8bdc9',
    }[f.status] || '#a8bdc9';
    return `<div style="display:flex;align-items:center;gap:8px;justify-content:space-between;">
      <span style="color:var(--be8-ice);font-size:11.5px;">${f.fonte}</span>
      <span style="color:${dot};font-size:10.5px;font-family:var(--font-mono);text-transform:uppercase;">${f.status}</span>
    </div>`;
  }).join('');

  safeSetText('sources-meta', `${ok}/${total} ao vivo`);
}

function renderRadarIA() {
  // Regras de inferência aplicadas sobre STATE.commodities + STATE.cambio
  const c = STATE.commodities?.dados || {};
  const cb = STATE.cambio?.dados || {};
  const bull = [];
  const bear = [];
  const acoes = [];

  // Regra 1: óleo soja sobe + Brent sobe → pressão B100 alta
  if (c.oleo_soja?.variacao_pct > 0.5 && c.brent?.variacao_pct > 0.5) {
    bear.push({ titulo: 'Pressão de alta no B100', desc: 'Óleo soja e Brent simultaneamente em alta.' });
    acoes.push({ titulo: 'Repassar custo via contrato', desc: 'Avaliar contratos com cláusula de repasse.' });
  }
  // Regra 2: USD/BRL sobe → janela de exportação
  if (cb.usd?.variacao_pct > 0.3) {
    bull.push({ titulo: 'Janela favorável a exportação', desc: 'USD/BRL em alta — competitividade externa melhora.' });
    acoes.push({ titulo: 'Acelerar contratos de exportação', desc: 'Aproveitar real desvalorizado.' });
  }
  // Regra 3: Brent cai + óleo soja sobe → compressão de margem
  if (c.brent?.variacao_pct < -0.3 && c.oleo_soja?.variacao_pct > 0.3) {
    bear.push({ titulo: 'Compressão de margem B100', desc: 'Brent em queda reduz competitividade do biodiesel.' });
  }
  // Regra 4: soja sobe forte → originação concorrida
  if (c.soja?.variacao_pct > 1) {
    bull.push({ titulo: 'Produtores em posição vendedora', desc: 'Soja CBOT em alta forte estimula venda.' });
    bear.push({ titulo: 'Originação mais cara', desc: 'Disputa com exportação encarece insumo.' });
  }
  // Regra 5: USD/BRL cai → importação favorecida
  if (cb.usd?.variacao_pct < -0.3) {
    bull.push({ titulo: 'Importação de insumos favorecida', desc: 'Real apreciado barateia metanol importado.' });
  }

  const renderList = (id, items, emptyMsg) => {
    const el = document.getElementById(id);
    if (!el) return;
    if (items.length === 0) {
      el.innerHTML = `<div style="color:var(--be8-dim);font-style:italic;font-size:13px;padding:8px 0;">${emptyMsg}</div>`;
      return;
    }
    el.innerHTML = items.map((it) =>
      `<div class="radar-item"><div class="radar-title">${it.titulo}</div><div class="radar-desc">${it.desc}</div></div>`
    ).join('');
  };

  renderList('radar-bull',  bull,  'Sem drivers positivos relevantes neste ciclo.');
  renderList('radar-bear',  bear,  'Sem riscos significativos neste ciclo.');
  renderList('radar-acoes', acoes, 'Sem ações urgentes recomendadas.');

  const synth = bull.length + bear.length > 0
    ? `${bull.length} driver(s) positivo(s) e ${bear.length} risco(s) detectado(s) cruzando câmbio e commodities.`
    : 'Mercado lateral — sem sinais fortes cruzando câmbio e commodities neste ciclo.';
  safeSetText('radar-summary', synth);
}

/* =====================================================================
   RENDER · Ticker rolante (topo)
   ===================================================================== */
function renderTicker() {
  const el = document.getElementById('ticker-track');
  if (!el) return;
  const items = [];
  const cb = STATE.cambio?.dados;
  const cm = STATE.commodities?.dados;
  if (cb?.usd?.cotacao) items.push(`USD ${fmt.brl(cb.usd.cotacao, 4)} ${fmt.pct(cb.usd.variacao_pct)}`);
  if (cb?.eur?.cotacao) items.push(`EUR ${fmt.brl(cb.eur.cotacao, 4)} ${fmt.pct(cb.eur.variacao_pct)}`);
  if (cm?.brent?.cotacao) items.push(`Brent ${fmt.usd(cm.brent.cotacao, 2)} ${fmt.pct(cm.brent.variacao_pct)}`);
  if (cm?.soja?.cotacao)  items.push(`Soja ${fmt.cent(cm.soja.cotacao, 0)} ${fmt.pct(cm.soja.variacao_pct)}`);
  if (cm?.milho?.cotacao) items.push(`Milho ${fmt.cent(cm.milho.cotacao, 0)} ${fmt.pct(cm.milho.variacao_pct)}`);
  if (cm?.oleo_soja?.cotacao) items.push(`Óleo soja ${fmt.cent(cm.oleo_soja.cotacao, 0)} ${fmt.pct(cm.oleo_soja.variacao_pct)}`);
  if (cm?.wti?.cotacao)   items.push(`WTI ${fmt.usd(cm.wti.cotacao, 2)} ${fmt.pct(cm.wti.variacao_pct)}`);

  if (items.length === 0) {
    el.innerHTML = '<span style="color:var(--be8-dim);font-style:italic;">Aguardando coleta…</span>';
    return;
  }
  // Duplicar pra rolagem infinita
  const html = items.concat(items).map((t) => `<span class="ticker-item">${t}</span>`).join('');
  el.innerHTML = html;
}

/* =====================================================================
   MODO TV · rotação automática entre páginas
   ===================================================================== */
const TV_STATE = {
  running: false,
  paused: false,
  idx: 0,
  pages: [],
  timer: null,
  scrollTimer: null,
};

function defaultTVConfig() {
  return $$('.nav-tab').map((b) => ({
    page: b.dataset.page,
    label: b.textContent.trim(),
    on: true,
    seconds: 18,
    scroll: true,
  }));
}

function loadTVConfig() {
  try {
    const raw = localStorage.getItem('be8_tv_config');
    if (!raw) return defaultTVConfig();
    const cfg = JSON.parse(raw);
    if (!Array.isArray(cfg) || cfg.length === 0) return defaultTVConfig();
    return cfg;
  } catch { return defaultTVConfig(); }
}

function saveTVConfig(cfg) {
  localStorage.setItem('be8_tv_config', JSON.stringify(cfg));
}

function buildTVConfigUI() {
  const tbody = document.getElementById('tv-config-tbody');
  if (!tbody) return;
  const cfg = loadTVConfig();
  tbody.innerHTML = cfg.map((row, i) => `<tr>
    <td>${row.label}</td>
    <td><input type="checkbox" data-i="${i}" data-k="on" ${row.on ? 'checked' : ''}></td>
    <td><input type="number" min="5" max="120" value="${row.seconds}" data-i="${i}" data-k="seconds" style="width:60px;"></td>
    <td><input type="checkbox" data-i="${i}" data-k="scroll" ${row.scroll ? 'checked' : ''}></td>
    <td>${i + 1}</td>
  </tr>`).join('');
}

function readTVConfigFromUI() {
  const cfg = loadTVConfig();
  $$('#tv-config-tbody input').forEach((inp) => {
    const i = +inp.dataset.i;
    const k = inp.dataset.k;
    if (inp.type === 'checkbox') cfg[i][k] = inp.checked;
    else cfg[i][k] = Number(inp.value) || 18;
  });
  return cfg;
}

function startTV() {
  const cfg = loadTVConfig().filter((c) => c.on);
  if (cfg.length === 0) {
    alert('Selecione ao menos uma página no Modo TV.');
    return;
  }
  TV_STATE.pages = cfg;
  TV_STATE.idx = 0;
  TV_STATE.running = true;
  TV_STATE.paused = false;
  $('#tv-bar').style.display = 'flex';
  document.body.classList.add('tv-mode');
  goToTVPage();
}

function stopTV() {
  TV_STATE.running = false;
  TV_STATE.paused = false;
  clearTimeout(TV_STATE.timer);
  clearInterval(TV_STATE.scrollTimer);
  $('#tv-bar').style.display = 'none';
  document.body.classList.remove('tv-mode');
}

function goToTVPage() {
  if (!TV_STATE.running) return;
  const cur = TV_STATE.pages[TV_STATE.idx];
  if (!cur) return;
  const btn = $$('.nav-tab').find((b) => b.dataset.page === cur.page);
  if (btn) btn.click();
  safeSetText('tv-page-label', `PÁGINA · ${cur.label.toUpperCase()}`);

  const fillEl = $('#tv-fill');
  if (fillEl) {
    fillEl.style.transition = 'none';
    fillEl.style.width = '0%';
    requestAnimationFrame(() => {
      fillEl.style.transition = `width ${cur.seconds}s linear`;
      fillEl.style.width = '100%';
    });
  }

  // Auto-scroll suave
  clearInterval(TV_STATE.scrollTimer);
  if (cur.scroll) {
    const dur = cur.seconds * 1000;
    const start = performance.now();
    TV_STATE.scrollTimer = setInterval(() => {
      if (TV_STATE.paused) return;
      const elapsed = performance.now() - start;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo(0, (elapsed / dur) * max);
      if (elapsed >= dur) clearInterval(TV_STATE.scrollTimer);
    }, 30);
  }

  clearTimeout(TV_STATE.timer);
  TV_STATE.timer = setTimeout(() => {
    if (TV_STATE.paused) return;
    TV_STATE.idx = (TV_STATE.idx + 1) % TV_STATE.pages.length;
    goToTVPage();
  }, cur.seconds * 1000);
}

function bindTVControls() {
  $('#tv-toggle')?.addEventListener('click', () => {
    buildTVConfigUI();
    $('#tv-config-overlay').classList.add('active');
  });
  $('#tv-config-cancel')?.addEventListener('click', () => {
    $('#tv-config-overlay').classList.remove('active');
  });
  $('#tv-config-save')?.addEventListener('click', () => {
    saveTVConfig(readTVConfigFromUI());
    $('#tv-config-overlay').classList.remove('active');
    startTV();
  });
  $('#tv-exit')?.addEventListener('click', stopTV);
  $('#tv-pause')?.addEventListener('click', () => {
    TV_STATE.paused = !TV_STATE.paused;
    const btn = $('#tv-pause');
    if (btn) btn.textContent = TV_STATE.paused ? '▶ Retomar' : '⏸ Pausar';
  });
  $('#tv-next')?.addEventListener('click', () => {
    TV_STATE.idx = (TV_STATE.idx + 1) % TV_STATE.pages.length;
    goToTVPage();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && TV_STATE.running) stopTV();
  });
}

/* =====================================================================
   SNAPSHOT (impressão do navegador)
   ===================================================================== */
function snapshotPNG() {
  // Versão pragmática: usa window.print(). O usuário escolhe "Salvar como PDF"
  // no diálogo do navegador. Sem dependência externa.
  window.print();
}

/* =====================================================================
   BOOT
   ===================================================================== */
async function boot() {
  console.log('[BENCH-BE8] boot · v2.4');

  bindNavigation();
  bindTVControls();
  setSessionClock();
  setInterval(setSessionClock, 1000);

  await reloadAllData();

  $('#refresh-all')?.addEventListener('click', () => {
    console.log('[BENCH-BE8] refresh manual disparado');
    reloadAllData();
  });
  $('#export-snapshot')?.addEventListener('click', snapshotPNG);

  console.log('[BENCH-BE8] boot · pronto');
}

document.addEventListener('DOMContentLoaded', boot);
