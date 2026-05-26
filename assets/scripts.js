/* =====================================================================
   BE8 · MARKET INTELLIGENCE PLATFORM · frontend
   Sem CORS: tudo lê JSONs locais gerados pelo agente Python.
   Se um JSON estiver ausente ou em PENDENTE, mostra status sem quebrar.
   ===================================================================== */

const STATE = {
  cambio: null,
  commodities: null,
  conab: null,
  anp_combustiveis: null,
  anp_b100: null,
  comex: null,
  noticias: null,
  be8_profile: null,
  status_fontes: null,
  insights: [],
};

const $ = sel => document.querySelector(sel);
const $$ = sel => Array.from(document.querySelectorAll(sel));

/* =====================================================================
   HELPERS
   ===================================================================== */
const fmtBRL  = v => v == null ? '—' : 'R$ ' + Number(v).toLocaleString('pt-BR', {minimumFractionDigits:4, maximumFractionDigits:4});
const fmtBRL2 = v => v == null ? '—' : 'R$ ' + Number(v).toLocaleString('pt-BR', {minimumFractionDigits:3, maximumFractionDigits:3});
const fmtUSD  = v => v == null ? '—' : '$ '  + Number(v).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
const fmtCent = v => v == null ? '—' : '¢ '  + Number(v).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2});
const fmtNum  = (v,d=2) => v == null ? '—' : Number(v).toLocaleString('pt-BR', {minimumFractionDigits:d, maximumFractionDigits:d});
const fmtPct  = v => v == null ? '—' : (v >= 0 ? '+' : '') + Number(v).toFixed(2) + '%';

function deltaClass(pct) {
  if (pct == null || isNaN(pct)) return 'flat';
  if (pct > 0.05) return 'up';
  if (pct < -0.05) return 'down';
  return 'flat';
}

async function loadJSON(path) {
  try {
    const r = await fetch(path + '?v=' + Date.now(), {cache: 'no-store'});
    if (!r.ok) return null;
    return await r.json();
  } catch (e) {
    console.warn(`Falha carregando ${path}:`, e);
    return null;
  }
}

function setSessionClock() {
  const now = new Date();
  $('#session-date').textContent = now.toLocaleDateString('pt-BR', {day:'2-digit', month:'short', year:'numeric'}).toUpperCase();
  $('#session-time').textContent = now.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit'}) + ' BRT';
  $('#footer-build').textContent = 'build · ' + now.toISOString().slice(0,16).replace('T',' ');
  const tvClock = $('#tv-clock');
  if (tvClock) tvClock.textContent = now.toLocaleTimeString('pt-BR', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
}

/* =====================================================================
   NAVIGATION
   ===================================================================== */
function setActivePage(pageId) {
  $$('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.page === pageId));
  $$('.page').forEach(p => p.classList.toggle('active', p.id === 'page-' + pageId));
  window.scrollTo({top: 0, behavior: 'smooth'});
}

$$('.nav-tab').forEach(tab => {
  tab.addEventListener('click', () => setActivePage(tab.dataset.page));
});

/* =====================================================================
   SVG CHARTS
   ===================================================================== */
function renderSparkline(containerId, series, color = '#0eb194') {
  const c = $('#' + containerId);
  if (!c) return;
  if (!series || series.length < 2) {
    c.innerHTML = '';
    return;
  }
  const W = c.clientWidth || 200, H = 44;
  const values = series.map(p => p.valor);
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const pts = series.map((p, i) => {
    const x = (i / (series.length - 1)) * W;
    const y = H - ((p.valor - min) / range) * (H - 6) - 3;
    return [x, y, p];
  });
  const path = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const areaPath = path + ` L${W},${H} L0,${H} Z`;
  const last = pts[pts.length-1];
  const first = pts[0];
  c.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="overflow:visible;">
      <defs>
        <linearGradient id="sp-grad-${containerId}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.4"/>
          <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
        </linearGradient>
      </defs>
      <path d="${areaPath}" fill="url(#sp-grad-${containerId})"/>
      <path d="${path}" fill="none" stroke="${color}" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>
      <circle cx="${last[0].toFixed(1)}" cy="${last[1].toFixed(1)}" r="2.5" fill="${color}"/>
      <title>Série de ${series.length} pontos · ${first[2].data || 'início'} → ${last[2].data || 'fim'} · último valor ${fmtNum(last[2].valor, 2)}</title>
    </svg>`;
}

function renderLineChart(containerId, series, color = '#0eb194', opts = {}) {
  const c = $('#' + containerId);
  if (!c) return;
  if (!series || series.length < 2) {
    c.innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Sem dados disponíveis ainda — agente Python precisa rodar.</div>';
    return;
  }
  // opts: { decimals, prefix, suffix }
  const decimals = opts.decimals != null ? opts.decimals : 2;
  const prefix = opts.prefix || '';
  const suffix = opts.suffix || '';
  const fmtV = v => prefix + Number(v).toLocaleString('pt-BR', {minimumFractionDigits:decimals, maximumFractionDigits:decimals}) + suffix;

  const W = c.clientWidth || 700, H = 300;
  const padding = { top: 24, right: 70, bottom: 38, left: 64 };
  const innerW = W - padding.left - padding.right;
  const innerH = H - padding.top - padding.bottom;
  const values = series.map(p => p.valor);
  const min = Math.min(...values), max = Math.max(...values);
  const range = max - min || 1;
  const pad = range * 0.12;
  const yMin = min - pad, yMax = max + pad;
  const yRange = yMax - yMin;

  // Pontos com coords + dados originais
  const pts = series.map((p, i) => {
    const x = padding.left + (i / (series.length - 1)) * innerW;
    const y = padding.top + (1 - (p.valor - yMin) / yRange) * innerH;
    return { x, y, data: p.data, valor: p.valor };
  });
  const path = pts.map((p, i) => (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ',' + p.y.toFixed(1)).join(' ');
  const areaPath = path + ` L${pts[pts.length-1].x.toFixed(1)},${padding.top + innerH} L${pts[0].x.toFixed(1)},${padding.top + innerH} Z`;

  // Y-ticks (6 níveis)
  const yTicks = [];
  for (let i = 0; i <= 6; i++) {
    const v = yMin + (i / 6) * yRange;
    const y = padding.top + (1 - i / 6) * innerH;
    yTicks.push({ v, y });
  }
  // X-ticks (6 datas)
  const xTicks = [];
  const xCount = 6;
  for (let i = 0; i < xCount; i++) {
    const idx = Math.round((i / (xCount - 1)) * (series.length - 1));
    const p = pts[idx];
    xTicks.push({ x: p.x, date: p.data });
  }

  // Pontos circulares: mostrar todos como bolinhas pequenas se série <= 30, senão somente cada N
  const showDots = pts.length <= 30;
  const dotEvery = pts.length <= 30 ? 1 : Math.ceil(pts.length / 30);

  const first = pts[0];
  const last = pts[pts.length - 1];
  const variacao = ((last.valor - first.valor) / first.valor) * 100;
  const variacaoStr = (variacao >= 0 ? '+' : '') + variacao.toFixed(2) + '%';
  const variacaoCor = variacao >= 0 ? '#55c94f' : '#ff8585';

  c.innerHTML = `
    <div class="line-chart-wrap" style="position:relative;">
      <svg class="line-chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="display:block; width:100%; height:auto; cursor:crosshair;">
        <defs>
          <linearGradient id="lc-grad-${containerId}" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stop-color="${color}" stop-opacity="0.28"/>
            <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
          </linearGradient>
        </defs>

        <!-- Grid horizontal + labels Y -->
        ${yTicks.map(t => `
          <line x1="${padding.left}" x2="${W - padding.right}" y1="${t.y}" y2="${t.y}" stroke="rgba(168,189,201,0.07)" stroke-width="1"/>
          <text x="${padding.left - 10}" y="${t.y + 3.5}" font-family="JetBrains Mono" font-size="10" fill="#5e7382" text-anchor="end">${fmtV(t.v)}</text>
        `).join('')}

        <!-- Datas X -->
        ${xTicks.map(t => `
          <text x="${t.x}" y="${H - padding.bottom + 18}" font-family="JetBrains Mono" font-size="10" fill="#5e7382" text-anchor="middle">${(t.date||'').slice(5)}</text>
        `).join('')}

        <!-- Área e linha -->
        <path d="${areaPath}" fill="url(#lc-grad-${containerId})"/>
        <path d="${path}" fill="none" stroke="${color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>

        <!-- Pontos individuais (clicáveis/hover) -->
        ${pts.map((p, i) => {
          if (i % dotEvery !== 0 && i !== pts.length-1) return '';
          return `<circle class="lc-pt" cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${showDots?2.5:1.8}" fill="${color}" data-i="${i}" style="cursor:pointer;"/>`;
        }).join('')}

        <!-- Label valor inicial -->
        <g>
          <rect x="${first.x - 36}" y="${first.y - 22}" width="68" height="18" rx="3" fill="rgba(8,31,46,0.85)" stroke="${color}" stroke-width="1" stroke-opacity="0.5"/>
          <text x="${first.x + 2}" y="${first.y - 9}" font-family="JetBrains Mono" font-size="10" fill="#a8bdc9" text-anchor="middle">${fmtV(first.valor)}</text>
        </g>

        <!-- Label valor final em destaque -->
        <circle cx="${last.x.toFixed(1)}" cy="${last.y.toFixed(1)}" r="7" fill="${color}" opacity="0.25"/>
        <circle cx="${last.x.toFixed(1)}" cy="${last.y.toFixed(1)}" r="4" fill="${color}"/>
        <g>
          <rect x="${last.x + 8}" y="${last.y - 11}" width="58" height="22" rx="3" fill="${color}" opacity="0.95"/>
          <text x="${last.x + 37}" y="${last.y + 4}" font-family="JetBrains Mono" font-size="11" font-weight="600" fill="#081f2e" text-anchor="middle">${fmtV(last.valor)}</text>
        </g>

        <!-- Crosshair vertical (escondido até hover) -->
        <line class="lc-cross-v" x1="0" x2="0" y1="${padding.top}" y2="${H - padding.bottom}" stroke="${color}" stroke-width="1" stroke-dasharray="3,3" opacity="0" pointer-events="none"/>
        <!-- Bolinha destacada no hover -->
        <circle class="lc-cross-pt" cx="-100" cy="-100" r="5" fill="${color}" stroke="#081f2e" stroke-width="2" opacity="0" pointer-events="none"/>

        <!-- Faixa invisível para capturar mouse -->
        <rect class="lc-hover-area" x="${padding.left}" y="${padding.top}" width="${innerW}" height="${innerH}" fill="transparent"/>
      </svg>

      <!-- Tooltip HTML (mais bonito que <text> SVG) -->
      <div class="lc-tooltip" style="position:absolute; pointer-events:none; opacity:0; background:rgba(5,15,23,0.95); border:1px solid ${color}; border-radius:6px; padding:8px 12px; font-family:var(--font-mono); font-size:11px; color:var(--be8-ice); white-space:nowrap; transition:opacity 0.1s; box-shadow:0 4px 14px rgba(0,0,0,0.5); z-index:10; min-width:130px;">
        <div class="lc-tt-date" style="color:#5e7382; font-size:10px; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:3px;"></div>
        <div class="lc-tt-val" style="font-size:14px; font-weight:600; color:${color};"></div>
        <div class="lc-tt-pct" style="font-size:10px; color:#a8bdc9; margin-top:2px;"></div>
      </div>

      <!-- Footer com primeiro/último/variação -->
      <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px; font-size:11px; font-family:var(--font-mono); color:var(--be8-mist);">
        <div><span style="color:#5e7382;">DESDE ${(first.data||'').slice(5)}:</span> ${fmtV(first.valor)}</div>
        <div><span style="color:#5e7382;">VARIAÇÃO 90D:</span> <strong style="color:${variacaoCor};">${variacaoStr}</strong></div>
        <div><span style="color:#5e7382;">ATUAL:</span> <strong style="color:var(--be8-ice);">${fmtV(last.valor)}</strong></div>
      </div>
    </div>`;

  // Bind interatividade
  const svg = c.querySelector('.line-chart-svg');
  const tooltip = c.querySelector('.lc-tooltip');
  const crossV = c.querySelector('.lc-cross-v');
  const crossPt = c.querySelector('.lc-cross-pt');
  const wrap = c.querySelector('.line-chart-wrap');

  svg.addEventListener('mousemove', (ev) => {
    const rect = svg.getBoundingClientRect();
    // converter clientX para viewBox X
    const xView = ((ev.clientX - rect.left) / rect.width) * W;
    if (xView < padding.left || xView > W - padding.right) {
      tooltip.style.opacity = 0;
      crossV.setAttribute('opacity', 0);
      crossPt.setAttribute('opacity', 0);
      return;
    }
    // achar ponto mais próximo
    let nearest = pts[0], minDist = Infinity;
    for (const p of pts) {
      const d = Math.abs(p.x - xView);
      if (d < minDist) { minDist = d; nearest = p; }
    }
    // posicionar tooltip (precisa converter viewBox para pixel real do wrap)
    const scale = rect.width / W;
    const px = nearest.x * scale;
    const py = nearest.y * scale;
    const ttW = tooltip.offsetWidth, wrapW = wrap.offsetWidth;
    const ttX = px + 12 + ttW > wrapW ? px - ttW - 12 : px + 12;
    const ttY = py - 30;
    tooltip.style.left = ttX + 'px';
    tooltip.style.top = Math.max(0, ttY) + 'px';
    tooltip.style.opacity = 1;
    const pct = ((nearest.valor - first.valor) / first.valor) * 100;
    const pctStr = (pct >= 0 ? '+' : '') + pct.toFixed(2) + '% desde o início';
    c.querySelector('.lc-tt-date').textContent = nearest.data || '';
    c.querySelector('.lc-tt-val').textContent = fmtV(nearest.valor);
    c.querySelector('.lc-tt-pct').textContent = pctStr;
    crossV.setAttribute('x1', nearest.x);
    crossV.setAttribute('x2', nearest.x);
    crossV.setAttribute('opacity', 0.5);
    crossPt.setAttribute('cx', nearest.x);
    crossPt.setAttribute('cy', nearest.y);
    crossPt.setAttribute('opacity', 1);
  });
  svg.addEventListener('mouseleave', () => {
    tooltip.style.opacity = 0;
    crossV.setAttribute('opacity', 0);
    crossPt.setAttribute('opacity', 0);
  });
}

function renderMultiNormalized(containerId, seriesList) {
  const c = $('#' + containerId);
  if (!c) return;
  const valid = seriesList.filter(s => s.data && s.data.length > 5);
  if (valid.length === 0) {
    c.innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Aguardando dados…</div>';
    return;
  }
  const W = c.clientWidth || 700, H = 300;
  const padding = { top: 24, right: 110, bottom: 38, left: 44 };
  const innerW = W - padding.left - padding.right;
  const innerH = H - padding.top - padding.bottom;

  const norm = valid.map(s => {
    const base = s.data[0].valor;
    return {
      ...s,
      norm: s.data.map(p => ({ data: p.data, valor: (p.valor / base) * 100, raw: p.valor })),
    };
  });
  const len = Math.min(...norm.map(s => s.norm.length));
  norm.forEach(s => s.norm = s.norm.slice(-len));

  const allVals = norm.flatMap(s => s.norm.map(p => p.valor));
  const yMin = Math.min(...allVals) * 0.97;
  const yMax = Math.max(...allVals) * 1.03;
  const yRange = yMax - yMin;

  // Pontos por série
  norm.forEach(s => {
    s.pts = s.norm.map((p, i) => {
      const x = padding.left + (i / (s.norm.length - 1)) * innerW;
      const y = padding.top + (1 - (p.valor - yMin) / yRange) * innerH;
      return { x, y, data: p.data, valor: p.valor, raw: p.raw };
    });
  });

  let paths = '';
  norm.forEach(s => {
    const pathD = s.pts.map((p, i) => (i === 0 ? 'M' : 'L') + p.x.toFixed(1) + ',' + p.y.toFixed(1)).join(' ');
    paths += `<path d="${pathD}" fill="none" stroke="${s.color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>`;
    const last = s.pts[s.pts.length-1];
    paths += `<circle cx="${last.x.toFixed(1)}" cy="${last.y.toFixed(1)}" r="3.5" fill="${s.color}"/>`;
    paths += `<rect x="${last.x + 6}" y="${last.y - 10}" width="98" height="20" rx="3" fill="${s.color}" opacity="0.92"/>`;
    paths += `<text x="${last.x + 11}" y="${last.y + 4}" font-family="JetBrains Mono" font-size="10.5" font-weight="600" fill="#081f2e">${s.name} ${last.valor.toFixed(1)}</text>`;
  });

  const yTicks = [];
  for (let i = 0; i <= 5; i++) {
    const v = yMin + (i / 5) * yRange;
    const y = padding.top + (1 - i / 5) * innerH;
    yTicks.push({ v, y });
  }
  // Linha do 100 (base)
  const y100 = padding.top + (1 - (100 - yMin) / yRange) * innerH;

  // X-ticks (datas)
  const refSerie = norm[0];
  const xTicks = [];
  const xCount = 6;
  for (let i = 0; i < xCount; i++) {
    const idx = Math.round((i / (xCount - 1)) * (refSerie.pts.length - 1));
    const p = refSerie.pts[idx];
    xTicks.push({ x: p.x, date: p.data });
  }

  c.innerHTML = `
    <div class="multi-chart-wrap" style="position:relative;">
      <svg class="multi-chart-svg" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="display:block; width:100%; height:auto; cursor:crosshair;">
        <!-- Grid horizontal -->
        ${yTicks.map(t => `
          <line x1="${padding.left}" x2="${W - padding.right}" y1="${t.y}" y2="${t.y}" stroke="rgba(168,189,201,0.06)" stroke-width="1"/>
          <text x="${padding.left - 6}" y="${t.y + 3}" font-family="JetBrains Mono" font-size="9.5" fill="#5e7382" text-anchor="end">${t.v.toFixed(0)}</text>
        `).join('')}

        <!-- Linha base 100 -->
        <line x1="${padding.left}" x2="${W - padding.right}" y1="${y100}" y2="${y100}" stroke="rgba(168,189,201,0.30)" stroke-width="1" stroke-dasharray="3,3"/>
        <text x="${W - padding.right + 4}" y="${y100 + 3.5}" font-family="JetBrains Mono" font-size="10" fill="#a8bdc9" font-weight="600">100</text>

        <!-- X datas -->
        ${xTicks.map(t => `
          <text x="${t.x}" y="${H - padding.bottom + 18}" font-family="JetBrains Mono" font-size="10" fill="#5e7382" text-anchor="middle">${(t.date||'').slice(5)}</text>
        `).join('')}

        <!-- Linhas das séries -->
        ${paths}

        <!-- Crosshair -->
        <line class="mc-cross-v" x1="0" x2="0" y1="${padding.top}" y2="${H - padding.bottom}" stroke="#a8bdc9" stroke-width="1" stroke-dasharray="3,3" opacity="0" pointer-events="none"/>

        <!-- Bolinhas hover por série -->
        ${norm.map((s, idx) => `<circle class="mc-cross-pt mc-cross-${idx}" cx="-100" cy="-100" r="5" fill="${s.color}" stroke="#081f2e" stroke-width="2" opacity="0" pointer-events="none"/>`).join('')}

        <rect class="mc-hover-area" x="${padding.left}" y="${padding.top}" width="${innerW}" height="${innerH}" fill="transparent"/>
      </svg>

      <!-- Tooltip multi-série -->
      <div class="mc-tooltip" style="position:absolute; pointer-events:none; opacity:0; background:rgba(5,15,23,0.95); border:1px solid rgba(168,189,201,0.30); border-radius:6px; padding:8px 12px; font-family:var(--font-mono); font-size:11px; color:var(--be8-ice); transition:opacity 0.1s; box-shadow:0 4px 14px rgba(0,0,0,0.5); z-index:10; min-width:180px;">
        <div class="mc-tt-date" style="color:#5e7382; font-size:10px; letter-spacing:0.05em; text-transform:uppercase; margin-bottom:6px; padding-bottom:5px; border-bottom:1px solid rgba(168,189,201,0.10);"></div>
        <div class="mc-tt-rows"></div>
      </div>
    </div>`;

  const svg = c.querySelector('.multi-chart-svg');
  const tooltip = c.querySelector('.mc-tooltip');
  const crossV = c.querySelector('.mc-cross-v');
  const wrap = c.querySelector('.multi-chart-wrap');
  const ttDate = c.querySelector('.mc-tt-date');
  const ttRows = c.querySelector('.mc-tt-rows');

  svg.addEventListener('mousemove', (ev) => {
    const rect = svg.getBoundingClientRect();
    const xView = ((ev.clientX - rect.left) / rect.width) * W;
    if (xView < padding.left || xView > W - padding.right) {
      tooltip.style.opacity = 0;
      crossV.setAttribute('opacity', 0);
      norm.forEach((_, i) => c.querySelector('.mc-cross-' + i).setAttribute('opacity', 0));
      return;
    }
    // Encontrar índice mais próximo (usando primeira série como referência temporal)
    let bestIdx = 0, minDist = Infinity;
    refSerie.pts.forEach((p, i) => {
      const d = Math.abs(p.x - xView);
      if (d < minDist) { minDist = d; bestIdx = i; }
    });

    const xAt = refSerie.pts[bestIdx].x;
    crossV.setAttribute('x1', xAt);
    crossV.setAttribute('x2', xAt);
    crossV.setAttribute('opacity', 0.55);

    // Tooltip
    ttDate.textContent = refSerie.pts[bestIdx].data || '';
    ttRows.innerHTML = norm.map((s, i) => {
      const p = s.pts[bestIdx];
      const dot = c.querySelector('.mc-cross-' + i);
      if (dot) { dot.setAttribute('cx', p.x); dot.setAttribute('cy', p.y); dot.setAttribute('opacity', 1); }
      const pct = (p.valor - 100).toFixed(2);
      const pctStr = (pct >= 0 ? '+' : '') + pct + '%';
      const pctClr = pct >= 0 ? '#55c94f' : '#ff8585';
      return `<div style="display:flex; justify-content:space-between; gap:14px; padding:2px 0;">
        <span style="color:${s.color}; font-weight:600;">● ${s.name}</span>
        <span style="color:var(--be8-ice); font-weight:600;">${p.valor.toFixed(2)} <span style="color:${pctClr}; font-size:9.5px;">(${pctStr})</span></span>
      </div>`;
    }).join('');

    const scale = rect.width / W;
    const px = xAt * scale;
    const ttW = tooltip.offsetWidth, wrapW = wrap.offsetWidth;
    const ttX = px + 14 + ttW > wrapW ? px - ttW - 14 : px + 14;
    tooltip.style.left = ttX + 'px';
    tooltip.style.top = '12px';
    tooltip.style.opacity = 1;
  });
  svg.addEventListener('mouseleave', () => {
    tooltip.style.opacity = 0;
    crossV.setAttribute('opacity', 0);
    norm.forEach((_, i) => c.querySelector('.mc-cross-' + i).setAttribute('opacity', 0));
  });
}

/* =====================================================================
   STATUS BADGE HELPER
   ===================================================================== */
function setStatusBadge(id, status, label) {
  const el = $('#' + id);
  if (!el) return;
  const cls = status === 'OK' ? 'src-live'
            : status === 'PARCIAL' ? 'src-cached'
            : status === 'PENDENTE' ? 'src-pending'
            : 'src-error';
  el.className = 'src-status ' + cls;
  el.textContent = label || (status === 'OK' ? 'Live' : status === 'PARCIAL' ? 'Parcial' : status === 'PENDENTE' ? 'Pendente' : 'Erro');
}

/* =====================================================================
   RENDER · CÂMBIO
   ===================================================================== */
function renderCambio() {
  const c = STATE.cambio;
  if (!c || c.status === 'PENDENTE' || !c.moedas || Object.keys(c.moedas).length === 0) {
    setStatusBadge('status-usd', 'PENDENTE');
    setStatusBadge('status-eur', 'PENDENTE');
    return;
  }
  const usd = c.moedas.USD;
  const eur = c.moedas.EUR;

  if (usd && usd.cotacao_atual != null) {
    $('#usd-value').innerHTML = fmtBRL(usd.cotacao_atual);
    const d = usd.variacao_pct;
    const dEl = $('#usd-delta');
    dEl.className = 'kpi-delta delta ' + deltaClass(d);
    dEl.textContent = fmtPct(d);
    setStatusBadge('status-usd', 'OK');
    renderSparkline('usd-spark', usd.serie_90d, '#0eb194');
    renderLineChart('usd-90-chart', usd.serie_90d, '#0eb194', { decimals: 4, prefix: 'R$ ' });
  } else {
    setStatusBadge('status-usd', 'PENDENTE');
  }
  if (eur && eur.cotacao_atual != null) {
    $('#eur-value').innerHTML = fmtBRL(eur.cotacao_atual);
    const d = eur.variacao_pct;
    const dEl = $('#eur-delta');
    dEl.className = 'kpi-delta delta ' + deltaClass(d);
    dEl.textContent = fmtPct(d);
    setStatusBadge('status-eur', 'OK');
    renderSparkline('eur-spark', eur.serie_90d, '#55c94f');
  } else {
    setStatusBadge('status-eur', 'PENDENTE');
  }
}

/* =====================================================================
   RENDER · COMMODITIES
   ===================================================================== */
function renderCommodities() {
  const c = STATE.commodities;
  if (!c || !c.commodities || c.commodities.length === 0) {
    setStatusBadge('status-brent', 'PENDENTE');
    setStatusBadge('status-soja', 'PENDENTE');
    $('#commodities-tbody').innerHTML = '<tr><td colspan="8"><div class="empty-state" style="margin:8px 0;"><div class="ic">⊘</div>Agente Python ainda não rodou para commodities.</div></td></tr>';
    return;
  }
  const map = {};
  c.commodities.forEach(x => map[x.id] = x);

  const setKPI = (idKey, item, fmtFn) => {
    if (!item || item.ultimo == null) {
      setStatusBadge('status-' + idKey, 'PENDENTE');
      return;
    }
    const valEl = $('#' + idKey + '-value');
    if (valEl) {
      // Preserva o span de unidade se houver
      const unitMatch = valEl.innerHTML.match(/<span class="unit">.*?<\/span>/);
      valEl.innerHTML = fmtFn(item.ultimo) + (unitMatch ? unitMatch[0] : '');
    }
    const dEl = $('#' + idKey + '-delta');
    if (dEl) {
      dEl.className = 'kpi-delta delta ' + deltaClass(item.var_d_pct);
      dEl.textContent = fmtPct(item.var_d_pct);
    }
    const stEl = $('#status-' + idKey);
    if (stEl) setStatusBadge('status-' + idKey, item.status || 'OK');
  };

  setKPI('brent', map.brent, fmtUSD);
  setKPI('wti', map.wti, fmtUSD);
  setKPI('soja', map.soja, fmtCent);
  setKPI('milho', map.milho, fmtCent);
  setKPI('trigo', map.trigo, fmtCent);
  setKPI('oleo_soja', map.oleo_soja, fmtCent);

  // Sparklines + linecharts adicionais
  if (map.brent && map.brent.serie_90d) {
    renderSparkline('brent-spark', map.brent.serie_90d, '#d4a84b');
    renderLineChart('brent-90-chart', map.brent.serie_90d, '#d4a84b', { decimals: 2, prefix: '$ ', suffix: ' /bbl' });
  }
  if (map.soja && map.soja.serie_90d) {
    renderSparkline('soja-spark', map.soja.serie_90d, '#55c94f');
    renderLineChart('soja-90-chart', map.soja.serie_90d, '#55c94f', { decimals: 2, prefix: '¢ ', suffix: ' /bu' });
  }
  if (map.oleo_soja && map.oleo_soja.serie_90d) {
    renderLineChart('oleo-90-chart', map.oleo_soja.serie_90d, '#0eb194', { decimals: 2, prefix: '¢ ', suffix: ' /lb' });
  }

  // Tabela commodities
  const tb = $('#commodities-tbody');
  const fmtByMercado = (item) => {
    if (item.unidade.includes('US$') || item.unidade.includes('MMBtu')) return fmtUSD;
    if (item.unidade.includes('¢')) return fmtCent;
    return v => fmtNum(v, 2);
  };
  tb.innerHTML = c.commodities.map(item => {
    if (item.status !== 'OK' || item.ultimo == null) {
      return `<tr><td><strong>${item.nome}</strong></td><td>${item.mercado||'—'}</td><td colspan="5"><span class="src-status src-error">Sem dados</span></td><td><span class="src-status src-error">Erro</span></td></tr>`;
    }
    const f = fmtByMercado(item);
    return `<tr>
      <td><strong>${item.nome}</strong></td>
      <td>${item.mercado}</td>
      <td class="num">${f(item.ultimo)}</td>
      <td class="num" style="color: var(--be8-dim);">${f(item.anterior)}</td>
      <td class="num"><span class="kpi-delta delta ${deltaClass(item.var_d_pct)}">${fmtPct(item.var_d_pct)}</span></td>
      <td class="num">${item.var_7d_pct==null?'—':`<span class="kpi-delta delta ${deltaClass(item.var_7d_pct)}">${fmtPct(item.var_7d_pct)}</span>`}</td>
      <td class="num">${item.var_30d_pct==null?'—':`<span class="kpi-delta delta ${deltaClass(item.var_30d_pct)}">${fmtPct(item.var_30d_pct)}</span>`}</td>
      <td><span class="src-status src-live">Live</span></td>
    </tr>`;
  }).join('');

  // Correlação
  renderCorrelation();

  // Tendência normalizada na Visão Executiva
  renderTrendNormalized();
}

function renderTrendNormalized() {
  const usd = STATE.cambio?.moedas?.USD?.serie_90d || [];
  const cmap = {};
  (STATE.commodities?.commodities || []).forEach(c => cmap[c.id] = c);
  const brent = cmap.brent?.serie_90d || [];
  const soja = cmap.soja?.serie_90d || [];

  // Pegar últimos 30 pontos
  const last30 = s => s.slice(-30);

  renderMultiNormalized('trend-chart', [
    { name: 'USD/BRL', color: '#0eb194', data: last30(usd) },
    { name: 'Brent',   color: '#d4a84b', data: last30(brent) },
    { name: 'Soja',    color: '#55c94f', data: last30(soja) },
  ]);
}

function pearson(x, y) {
  const n = Math.min(x.length, y.length);
  if (n < 5) return null;
  const xs = x.slice(-n), ys = y.slice(-n);
  const mx = xs.reduce((a,b)=>a+b,0) / n;
  const my = ys.reduce((a,b)=>a+b,0) / n;
  let num=0, dx=0, dy=0;
  for (let i = 0; i < n; i++) {
    num += (xs[i]-mx)*(ys[i]-my);
    dx += (xs[i]-mx)**2;
    dy += (ys[i]-my)**2;
  }
  if (dx === 0 || dy === 0) return null;
  return num / Math.sqrt(dx * dy);
}

function renderCorrelation() {
  const container = $('#correlation-matrix');
  if (!container) return;
  const usd = (STATE.cambio?.moedas?.USD?.serie_90d || []).map(p=>p.valor);
  const cmap = {};
  (STATE.commodities?.commodities || []).forEach(c => cmap[c.id] = c);

  if (usd.length < 10 || !cmap.brent) {
    container.innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Aguardando dados de câmbio e commodities…</div>';
    return;
  }

  const vars = [
    { name: 'USD/BRL',    data: usd.slice(-60) },
    { name: 'Brent',      data: (cmap.brent?.serie_90d  || []).map(p=>p.valor).slice(-60) },
    { name: 'Óleo Soja',  data: (cmap.oleo_soja?.serie_90d || []).map(p=>p.valor).slice(-60) },
    { name: 'Soja',       data: (cmap.soja?.serie_90d || []).map(p=>p.valor).slice(-60) },
    { name: 'Milho',      data: (cmap.milho?.serie_90d || []).map(p=>p.valor).slice(-60) },
  ];

  let html = '<table class="data" style="margin-top: 4px;"><thead><tr><th></th>';
  vars.forEach(v => html += `<th class="num">${v.name}</th>`);
  html += '</tr></thead><tbody>';
  vars.forEach((vi, i) => {
    html += `<tr><td><strong>${vi.name}</strong></td>`;
    vars.forEach((vj, j) => {
      if (i === j) {
        html += `<td class="num" style="color:var(--be8-dim);">1.00</td>`;
      } else {
        const c = pearson(vi.data, vj.data);
        if (c == null) {
          html += `<td class="num" style="color:var(--be8-dim);">—</td>`;
        } else {
          const intensity = Math.abs(c);
          const color = c > 0 ? `rgba(85,201,79,${0.10 + intensity * 0.35})` : `rgba(232,95,95,${0.10 + intensity * 0.35})`;
          html += `<td class="num" style="background:${color};">${c.toFixed(2)}</td>`;
        }
      }
    });
    html += '</tr>';
  });
  html += '</tbody></table>';
  html += `<div style="margin-top: 12px; font-size: 11px; color: var(--be8-dim); font-family: var(--font-mono); letter-spacing: 0.02em;">CORRELAÇÃO DE PEARSON · ÚLTIMOS 60 PREGÕES · -1 (vermelho) ↔ +1 (verde)</div>`;
  container.innerHTML = html;
}

/* =====================================================================
   RENDER · GRÃOS (CONAB)
   ===================================================================== */
function renderConab() {
  const c = STATE.conab;
  const statusEl = $('#conab-status');
  if (!c || c.status === 'PENDENTE' || !c.safras || c.safras.length === 0) {
    if (statusEl) setStatusBadge('conab-status', 'PENDENTE', 'CONAB · aguardando');
    return;
  }
  if (statusEl) setStatusBadge('conab-status', c.status || 'OK',
    'CONAB · ' + (c.ultima_atualizacao || '').slice(0,10));

  // Agregação por cultura
  const culturas = {};
  c.safras.forEach(s => {
    if (!culturas[s.cultura]) culturas[s.cultura] = { ufs: [], total: 0, total_anterior: 0 };
    culturas[s.cultura].ufs.push(s);
    if (s.producao_mt) culturas[s.cultura].total += s.producao_mt;
    if (s.producao_mt_anterior) culturas[s.cultura].total_anterior += s.producao_mt_anterior;
  });

  const setCultura = (culturaName, prodId, deltaId) => {
    const ck = Object.keys(culturas).find(k => k.toLowerCase().includes(culturaName.toLowerCase()));
    if (!ck) return null;
    const cult = culturas[ck];
    const total = cult.total;
    const prev = cult.total_anterior;
    $('#' + prodId).innerHTML = fmtNum(total, 1) + ' <span class="unit">Mt</span>';
    if (prev && prev > 0) {
      const d = ((total - prev) / prev) * 100;
      const dEl = $('#' + deltaId);
      dEl.className = 'kpi-delta delta ' + deltaClass(d);
      dEl.textContent = fmtPct(d);
    }
    return cult;
  };

  setCultura('soja', 'soja-safra-prod', 'soja-safra-delta');
  setCultura('milho', 'milho-safra-prod', 'milho-safra-delta');
  setCultura('trigo', 'trigo-safra-prod', 'trigo-safra-delta');

  // Tabela top UFs
  const renderTopUFs = (culturaName, tbodyId, metaId) => {
    const ck = Object.keys(culturas).find(k => k.toLowerCase().includes(culturaName.toLowerCase()));
    const tbody = $('#' + tbodyId);
    if (!tbody) return;
    if (!ck) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--be8-dim); padding:24px;">Sem dados para esta cultura.</td></tr>';
      return;
    }
    const cult = culturas[ck];
    const total = cult.total || cult.ufs.reduce((a,b)=>a+(b.producao_mt||0),0);
    const sorted = cult.ufs.slice().sort((a,b) => (b.producao_mt||0) - (a.producao_mt||0)).slice(0, 8);
    tbody.innerHTML = sorted.map((u, i) => `
      <tr>
        <td class="rank">${String(i+1).padStart(2,'0')}</td>
        <td><strong>${u.uf || '—'}</strong></td>
        <td class="num">${fmtNum(u.producao_mt, 2)}</td>
        <td class="num">${total ? fmtNum((u.producao_mt/total)*100, 1) + '%' : '—'}</td>
        <td class="num">${u.area_mha != null ? fmtNum(u.area_mha, 2) : '—'}</td>
      </tr>`).join('');
    const metaEl = $('#' + metaId);
    if (metaEl) metaEl.textContent = (c.safra_atual || ck) + ' · ' + (c.ultima_atualizacao || '').slice(0,10);
  };
  renderTopUFs('soja', 'soja-uf-tbody', 'soja-uf-meta');
  renderTopUFs('milho', 'milho-uf-tbody', 'milho-uf-meta');

  // Composição regional · soja
  renderRegional('soja');

  // Impacto biodiesel
  renderImpactoBiodiesel(culturas);
}

function renderRegional(cultura) {
  const c = STATE.conab;
  if (!c || !c.safras) return;
  const ufs = c.safras.filter(s => s.cultura && s.cultura.toLowerCase().includes(cultura));
  const regioes = { 'CO': 0, 'S': 0, 'SE': 0, 'NE': 0, 'N': 0 };
  const REG = {
    'MT':'CO','MS':'CO','GO':'CO','DF':'CO',
    'PR':'S','RS':'S','SC':'S',
    'SP':'SE','MG':'SE','RJ':'SE','ES':'SE',
    'BA':'NE','MA':'NE','PI':'NE','PE':'NE','CE':'NE','RN':'NE','PB':'NE','AL':'NE','SE':'NE',
    'TO':'N','PA':'N','RO':'N','AM':'N','AC':'N','AP':'N','RR':'N'
  };
  ufs.forEach(u => {
    const reg = REG[u.uf];
    if (reg && u.producao_mt) regioes[reg] += u.producao_mt;
  });
  const total = Object.values(regioes).reduce((a,b)=>a+b,0);
  if (total === 0) {
    $('#regional-soja-viz').innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Sem dados regionais</div>';
    return;
  }
  const labels = { CO: 'Centro-Oeste', S: 'Sul', SE: 'Sudeste', NE: 'Nordeste', N: 'Norte' };
  const colors = { CO: '#0eb194', S: '#55c94f', SE: '#d4a84b', NE: '#7a9bbf', N: '#a8bdc9' };
  const W = 800, H = 60;
  let x = 0; let bars = ''; let legend = '';
  Object.entries(regioes).forEach(([r, v]) => {
    if (v <= 0) return;
    const w = (v / total) * W;
    bars += `<rect x="${x}" y="0" width="${w-1}" height="${H}" fill="${colors[r]}" opacity="0.9"/>`;
    if (w > 60) {
      bars += `<text x="${x + w/2}" y="${H/2}" fill="white" font-family="Inter Tight" font-size="13" font-weight="600" text-anchor="middle" dominant-baseline="middle">${((v/total)*100).toFixed(1)}%</text>`;
    }
    legend += `<div style="display:flex; align-items:center; gap:8px; font-size:12px; color:var(--be8-mist);"><span style="width:12px; height:12px; background:${colors[r]}; border-radius:2px;"></span>${labels[r]} · ${fmtNum(v,1)} Mt</div>`;
    x += w;
  });
  $('#regional-soja-viz').innerHTML = `
    <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
      <div style="font-size:13px; color:var(--be8-mist);">Soja — produção por região (Mt) · safra atual</div>
      <span class="card-meta">${c.fonte || 'CONAB'}</span>
    </div>
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%; height:60px; border-radius:4px;">${bars}</svg>
    <div style="display:flex; gap:24px; flex-wrap:wrap; margin-top:14px;">${legend}</div>`;
}

function renderImpactoBiodiesel(culturas) {
  const el = $('#impacto-biodiesel');
  if (!el) return;
  const soja = culturas['Soja'] || culturas[Object.keys(culturas).find(k=>k.toLowerCase().includes('soja'))];
  if (!soja) { el.innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Sem dados</div>'; return; }
  const totSoja = soja.total;
  const oleoTaxa = 0.18; // 18% da soja vira óleo
  const oleoEstimado = totSoja * oleoTaxa;
  const b100Demanda2026 = 10.5; // bi L = ~9.3 Mt de óleo se 100% soja
  // Suficiência teórica: óleo total disponível vs. demanda B100 (considerando ~70% origem soja)
  const oleoParaB100 = oleoEstimado * 0.35; // ~35% do óleo vai para biodiesel
  el.innerHTML = `
    <div class="grid grid-3" style="gap:14px;">
      <div style="padding: 14px; background: rgba(8,31,46,0.4); border-radius:6px; border: 1px solid var(--be8-border);">
        <div style="font-size: 10.5px; color: var(--be8-mist); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;">Soja · produção total</div>
        <div style="font-family: var(--font-display); font-size: 28px; color: var(--be8-ice); line-height: 1;">${fmtNum(totSoja, 1)} Mt</div>
      </div>
      <div style="padding: 14px; background: rgba(14,177,148,0.06); border-radius:6px; border: 1px solid rgba(14,177,148,0.2);">
        <div style="font-size: 10.5px; color: var(--be8-green-1); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;">Óleo de soja estimado</div>
        <div style="font-family: var(--font-display); font-size: 28px; color: var(--be8-ice); line-height: 1;">${fmtNum(oleoEstimado, 1)} Mt</div>
        <div style="font-size: 11px; color: var(--be8-mist); margin-top: 6px;">≈ 18% da soja (taxa de extração)</div>
      </div>
      <div style="padding: 14px; background: rgba(85,201,79,0.06); border-radius:6px; border: 1px solid rgba(85,201,79,0.2);">
        <div style="font-size: 10.5px; color: var(--be8-green-2); letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 8px;">Direcionado a B100 (est.)</div>
        <div style="font-family: var(--font-display); font-size: 28px; color: var(--be8-ice); line-height: 1;">${fmtNum(oleoParaB100, 1)} Mt</div>
        <div style="font-size: 11px; color: var(--be8-mist); margin-top: 6px;">≈ 35% do óleo · matéria-prima B100</div>
      </div>
    </div>
    <div style="margin-top:18px; padding:14px; background: rgba(212,168,75,0.05); border-left: 2px solid var(--be8-gold); border-radius:4px; font-size:12.5px; color: var(--be8-mist); line-height:1.7;">
      <strong style="color:var(--be8-gold);">Leitura estratégica:</strong> com mistura B15 vigente e ampliação para B20 até 2030 (Lei 14.993/24), a demanda projetada B100 cresce ~7%/ano. A produção de soja no Brasil (~${fmtNum(totSoja,0)} Mt) é folgada para suportar a demanda doméstica de óleo, mas a competição com exportação (Argentina, China, Europa) define o preço de fixação da matéria-prima Be8.
    </div>`;
}

/* =====================================================================
   RENDER · BIODIESEL (ANP B100)
   ===================================================================== */
function renderBiodieselANP() {
  const b = STATE.anp_b100;
  if (!b || b.status === 'PENDENTE' || !b.produtores || b.produtores.length === 0) {
    setStatusBadge('anp-b100-status', 'PENDENTE', 'ANP · aguardando');
    renderRankingFallback();
    renderMateriasPrimas();
    renderBe8Context();
    return;
  }
  setStatusBadge('anp-b100-status', b.status || 'OK',
    'ANP · ' + (b.ultima_atualizacao || '').slice(0,10));

  if (b.producao_total_m3 != null) {
    $('#b100-prod-total').innerHTML = fmtNum(b.producao_total_m3, 0) + ' <span class="unit">m³/mês</span>';
  }
  if (b.capacidade_total_m3_ano != null) {
    $('#b100-cap-total').innerHTML = fmtNum(b.capacidade_total_m3_ano/1e6, 2) + ' <span class="unit">M m³/ano</span>';
    if (b.producao_total_m3) {
      const util = (b.producao_total_m3 * 12) / b.capacidade_total_m3_ano * 100;
      $('#b100-util').textContent = fmtNum(util, 1) + '%';
    }
  }

  // Ranking
  const tb = $('#biodiesel-rank-tbody');
  const sorted = b.produtores.slice().sort((a,b) => (b.market_share_pct||0) - (a.market_share_pct||0));
  tb.innerHTML = sorted.map((p, i) => `
    <tr>
      <td class="rank">${String(i+1).padStart(2,'0')}</td>
      <td><strong style="color:${(p.produtor||'').toLowerCase().includes('be8') ? 'var(--be8-green-2)' : 'var(--be8-ice)'};">${p.produtor || '—'}</strong></td>
      <td style="color:var(--be8-mist); font-size:12px;">${p.uf || ''} ${p.planta ? '· ' + p.planta : ''}</td>
      <td class="num">${p.capacidade_m3_ano ? fmtNum(p.capacidade_m3_ano, 0) : '—'}</td>
      <td class="num">${p.market_share_pct != null ? fmtNum(p.market_share_pct, 1) + '%' : '—'}</td>
    </tr>`).join('');

  renderMateriasPrimas();
  renderBe8Context();
}

function renderRankingFallback() {
  // Lista estrutural dos principais produtores conhecidos publicamente, com Be8 destacada
  const producers = [
    { name: 'Be8 (BSBIOS)',           plants: 'Passo Fundo (RS) · Marialva (PR)', cap: 1080000 },
    { name: 'ADM do Brasil',           plants: 'Rondonópolis (MT) · Joaçaba (SC)', cap: null },
    { name: 'Bunge',                   plants: 'Nova Mutum (MT)',                 cap: null },
    { name: 'Granol',                  plants: 'Cachoeira do Sul (RS) · Anápolis (GO)', cap: null },
    { name: 'Cargill',                 plants: 'Três Lagoas (MS)',                cap: null },
    { name: 'Caramuru',                plants: 'São Simão (GO)',                  cap: null },
    { name: 'Oleoplan',                plants: 'Veranópolis (RS)',                cap: null },
    { name: 'Camera',                  plants: 'Ijuí (RS)',                       cap: null },
    { name: 'Outros',                  plants: 'Diversas',                        cap: null },
  ];
  $('#biodiesel-rank-tbody').innerHTML = producers.map((p, i) => `
    <tr>
      <td class="rank">${String(i+1).padStart(2,'0')}</td>
      <td><strong style="color:${p.name.startsWith('Be8') ? 'var(--be8-green-2)' : 'var(--be8-ice)'};">${p.name}</strong></td>
      <td style="color:var(--be8-mist); font-size:12px;">${p.plants}</td>
      <td class="num">${p.cap ? fmtNum(p.cap, 0) : '<span class="src-status src-pending">ANP</span>'}</td>
      <td class="num"><span class="src-status src-pending">ANP</span></td>
    </tr>`).join('');
}

function renderBe8Context() {
  const profile = STATE.be8_profile;
  const cap = profile?.capacidade_total?.biodiesel_milhoes_l_ano || 1080;
  const shareIndicador = profile?.indicadores_publicos?.find(i => (i.indicador||'').toLowerCase().includes('market share biodiesel brasil (2023)'));
  const shareTxt = shareIndicador?.valor || 'Top 3';
  $('#be8-context-viz').innerHTML = `
    <div style="text-align: center; padding: 8px 0 24px;">
      <div style="font-family: var(--font-display); font-size: 56px; font-weight: 300; line-height: 1; color: var(--be8-ice); letter-spacing: -0.03em;">
        <span style="background: var(--grad-energy); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;">${shareTxt}</span>
      </div>
      <div style="font-size: 12px; color: var(--be8-mist); margin-top: 8px; letter-spacing: 0.02em;">
        Market share Brasil · biodiesel<br>(referência pública O Nacional · 2024)
      </div>
    </div>
    <div style="border-top: 1px solid var(--be8-border); padding-top: 18px; font-size: 12px; color: var(--be8-mist); line-height: 1.7;">
      <div style="display: flex; justify-content: space-between; padding: 4px 0;"><span>Capacidade total</span><strong style="color: var(--be8-ice);">${cap} M L/ano</strong></div>
      <div style="display: flex; justify-content: space-between; padding: 4px 0;"><span>Plantas operacionais</span><strong style="color: var(--be8-ice);">2 (RS + PR)</strong></div>
      <div style="display: flex; justify-content: space-between; padding: 4px 0;"><span>Posicionamento</span><strong style="color: var(--be8-green-2);">Top produtor nacional</strong></div>
      <div style="display: flex; justify-content: space-between; padding: 4px 0;"><span>Diferencial</span><strong style="color: var(--be8-ice);">Integração soja → óleo → B100</strong></div>
    </div>`;
}

function renderMateriasPrimas() {
  // Composição típica histórica ANP (referência pública, não inventada)
  const mp = [
    { name: 'Óleo de soja',      pct: 70, color: '#0eb194' },
    { name: 'Gordura bovina',    pct: 13, color: '#55c94f' },
    { name: 'Óleo de algodão',   pct: 5,  color: '#7ed957' },
    { name: 'Óleos ácidos',      pct: 4,  color: '#a8bdc9' },
    { name: 'Outros',            pct: 8,  color: '#5e7382' },
  ];
  const total = mp.reduce((a,b)=>a+b.pct,0);
  const W = 800, H = 80;
  let x = 0; let bars = ''; let legend = '';
  mp.forEach(m => {
    const w = (m.pct / total) * W;
    bars += `<rect x="${x}" y="0" width="${w-1}" height="${H}" fill="${m.color}" opacity="0.85"/>`;
    if (w > 50) {
      bars += `<text x="${x + w/2}" y="${H/2}" fill="white" font-family="Inter Tight" font-size="13" font-weight="600" text-anchor="middle" dominant-baseline="middle">${m.pct}%</text>`;
    }
    legend += `<div style="display:flex; align-items:center; gap:8px; font-size:12px; color:var(--be8-mist);"><span style="width:12px; height:12px; background:${m.color}; border-radius:2px;"></span>${m.name}</div>`;
    x += w;
  });
  $('#materias-primas-viz').innerHTML = `
    <div style="display:flex; justify-content:space-between; margin-bottom:12px; align-items:baseline;">
      <div style="font-size:13px; color:var(--be8-mist);">Composição típica · benchmark histórico ANP (Anuário Estatístico)</div>
      <span class="src-status src-cached">Anuário ANP · anual</span>
    </div>
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" style="width:100%; height:80px; border-radius:4px;">${bars}</svg>
    <div style="display:flex; gap:24px; flex-wrap:wrap; margin-top:14px;">${legend}</div>
    <div style="margin-top:16px; font-size:11px; color:var(--be8-dim); font-family:var(--font-mono); letter-spacing:0.02em; line-height:1.6;">
      VALORES DE REFERÊNCIA · COMPOSIÇÃO HISTÓRICA. Detalhamento mensal real via planilha “Matérias-primas utilizadas na produção de biodiesel B100” do Anuário Estatístico ANP.
    </div>`;
}

/* =====================================================================
   RENDER · ANP COMBUSTÍVEIS
   ===================================================================== */
function renderANPCombustiveis() {
  const a = STATE.anp_combustiveis;
  if (!a || a.status === 'PENDENTE' || !a.medias_brasil) {
    setStatusBadge('anp-status', 'PENDENTE', 'ANP · aguardando');
    return;
  }
  setStatusBadge('anp-status', a.status || 'OK',
    'ANP · ' + (a.semana_referencia || (a.ultima_atualizacao || '').slice(0,10)));

  const setProduct = (id, deltaId, key) => {
    const v = a.medias_brasil[key];
    if (v == null) return;
    const el = $('#' + id);
    if (el) el.innerHTML = fmtBRL2(v.preco) + ' <span class="unit">/L</span>';
    if (v.var_pct != null) {
      const dEl = $('#' + deltaId);
      dEl.className = 'kpi-delta delta ' + deltaClass(v.var_pct);
      dEl.textContent = fmtPct(v.var_pct);
    }
  };
  setProduct('anp-s10', 'anp-s10-delta', 'diesel_s10');
  setProduct('anp-s500', 'anp-s500-delta', 'diesel_s500');
  setProduct('anp-gasolina', 'anp-gasolina-delta', 'gasolina');
  setProduct('anp-etanol', 'anp-etanol-delta', 'etanol');

  // Rankings UF
  const renderUFTable = (tbodyId, ufs, brMedia) => {
    const tb = $('#' + tbodyId);
    if (!tb) return;
    if (!ufs || ufs.length === 0) {
      tb.innerHTML = '<tr><td colspan="5" style="text-align:center; color:var(--be8-dim); padding:24px;">Sem dados</td></tr>';
      return;
    }
    tb.innerHTML = ufs.slice(0, 8).map((u, i) => {
      const d = brMedia ? ((u.preco - brMedia) / brMedia) * 100 : null;
      return `<tr>
        <td class="rank">${String(i+1).padStart(2,'0')}</td>
        <td><strong>${u.uf}</strong></td>
        <td style="color:var(--be8-mist); font-size:12px;">${u.regiao || '—'}</td>
        <td class="num">${fmtBRL2(u.preco)}</td>
        <td class="num">${d == null ? '—' : `<span class="kpi-delta delta ${deltaClass(d)}">${fmtPct(d)}</span>`}</td>
      </tr>`;
    }).join('');
  };
  if (a.ranking_s10_caras) renderUFTable('anp-s10-caras-tbody', a.ranking_s10_caras, a.medias_brasil?.diesel_s10?.preco);
  if (a.ranking_s10_baratas) renderUFTable('anp-s10-baratas-tbody', a.ranking_s10_baratas, a.medias_brasil?.diesel_s10?.preco);

  // Regiões viz
  if (a.medias_regiao) renderANPRegioes(a.medias_regiao);
}

function renderANPRegioes(regioes) {
  const el = $('#anp-regioes-viz');
  if (!el) return;
  const entries = Object.entries(regioes);
  if (entries.length === 0) { el.innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Sem dados</div>'; return; }
  // Encontrar min/max para escala
  const values = entries.map(([_, v]) => v.diesel_s10 || 0).filter(v => v > 0);
  if (values.length === 0) { el.innerHTML = '<div class="empty-state"><div class="ic">⊘</div>Sem dados de Diesel S10 por região</div>'; return; }
  const min = Math.min(...values), max = Math.max(...values);
  const labels = { 'CO': 'Centro-Oeste', 'S': 'Sul', 'SE': 'Sudeste', 'NE': 'Nordeste', 'N': 'Norte' };
  const colors = { 'CO': '#0eb194', 'S': '#55c94f', 'SE': '#d4a84b', 'NE': '#7a9bbf', 'N': '#a8bdc9' };
  el.innerHTML = `
    <div style="font-size: 13px; color: var(--be8-mist); margin-bottom: 14px;">Preço médio do Diesel S10 por região (R$/L)</div>
    <div style="display:flex; flex-direction:column; gap:10px;">
      ${entries.map(([reg, v]) => {
        const val = v.diesel_s10 || 0;
        const pct = val ? ((val - min) / (max - min)) * 100 : 0;
        const c = colors[reg] || '#5e7382';
        return `
          <div>
            <div style="display:flex; justify-content:space-between; margin-bottom:4px; font-size:12px;">
              <span style="color:var(--be8-ice);">${labels[reg] || reg}</span>
              <span style="font-family:var(--font-mono); color:var(--be8-mist);">${fmtBRL2(val)}</span>
            </div>
            <div style="height:8px; background:rgba(168,189,201,0.08); border-radius:4px; overflow:hidden;">
              <div style="height:100%; width:${pct}%; background:${c}; border-radius:4px;"></div>
            </div>
          </div>`;
      }).join('')}
    </div>`;
}

/* =====================================================================
   RENDER · COMEX
   ===================================================================== */
function renderComex() {
  const c = STATE.comex;
  if (!c || c.status === 'PENDENTE' || !c.fluxos) {
    setStatusBadge('comex-status', 'PENDENTE', 'ComexStat · aguardando');
    return;
  }
  setStatusBadge('comex-status', c.status || 'OK',
    'ComexStat · ' + (c.ultima_atualizacao || '').slice(0,10));

  const fmtComex = (item, tipo) => {
    if (!item || item.status === 'ERRO') {
      return '<span class="src-status src-error">Sem dados</span>';
    }
    if (tipo === 'fob') {
      const fob = item.total_fob_usd || 0;
      if (fob >= 1e9) return fmtNum(fob/1e9, 2) + ' <span class="unit">bi US$</span>';
      if (fob >= 1e6) return fmtNum(fob/1e6, 1) + ' <span class="unit">M US$</span>';
      return fmtNum(fob/1e3, 0) + ' <span class="unit">k US$</span>';
    } else {
      const kg = item.total_kg || 0;
      if (kg >= 1e9) return fmtNum(kg/1e9, 2) + ' <span class="unit">Mt</span>';
      if (kg >= 1e6) return fmtNum(kg/1e6, 1) + ' <span class="unit">kt</span>';
      return fmtNum(kg/1e3, 0) + ' <span class="unit">t</span>';
    }
  };

  const f = c.fluxos;
  const setIfExists = (id, html) => { const el = $('#' + id); if (el) el.innerHTML = html; };

  setIfExists('comex-diesel-vol',    fmtComex(f.diesel_imp, 'fob'));
  setIfExists('comex-oleo-vol',      fmtComex(f.oleo_soja_exp, 'kg'));
  setIfExists('comex-biodiesel-vol', fmtComex(f.biodiesel_exp, 'fob'));
  setIfExists('comex-farelo-vol',    fmtComex(f.farelo_soja_exp, 'kg'));
  setIfExists('comex-soja-vol',      fmtComex(f.soja_grao_exp, 'kg'));
  setIfExists('comex-metanol-vol',   fmtComex(f.metanol_imp, 'kg'));
}

/* =====================================================================
   RENDER · GOVERNANÇA
   ===================================================================== */
function renderGovernance() {
  const s = STATE.status_fontes;
  const tb = $('#governance-tbody');
  if (!tb) return;
  // Tabela mestra das fontes esperadas
  const FONTES = [
    { id: 'bcb_ptax',          nome: 'Banco Central · PTAX',       tipo: 'API REST OData',     atualizacao: 'Diária (4x)',   custo: 'Grátis',      endpoint: 'olinda.bcb.gov.br/PTAX' },
    { id: 'commodities_yahoo', nome: 'Yahoo Finance · Commodities',tipo: 'API JSON',           atualizacao: '15min delay',   custo: 'Grátis',      endpoint: 'query1.finance.yahoo.com' },
    { id: 'comexstat',         nome: 'MDIC · ComexStat',           tipo: 'API REST oficial',   atualizacao: 'Mensal',        custo: 'Grátis',      endpoint: 'api-comexstat.mdic.gov.br' },
    { id: 'anp_combustiveis',  nome: 'ANP · Preços combustíveis',  tipo: 'CSV semanal',        atualizacao: 'Toda 6ª-feira', custo: 'Grátis',      endpoint: 'gov.br/anp/dados-abertos' },
    { id: 'anp_b100',          nome: 'ANP · Produção B100',        tipo: 'XLS/CSV mensal',     atualizacao: 'Mensal',        custo: 'Grátis',      endpoint: 'gov.br/anp/dados-estatisticos' },
    { id: 'conab',             nome: 'CONAB · Safra grãos',        tipo: 'XLS mensal',         atualizacao: 'Mensal',        custo: 'Grátis',      endpoint: 'conab.gov.br/info-agro/safras' },
    { id: 'ibge_sidra',        nome: 'IBGE · SIDRA LSPA',          tipo: 'API REST',           atualizacao: 'Mensal',        custo: 'Grátis',      endpoint: 'apisidra.ibge.gov.br' },
    { id: 'fred_eia',          nome: 'FRED + EIA · Energia/Macro', tipo: 'API REST + chave',   atualizacao: 'Diária',        custo: 'Grátis (key)',endpoint: 'api.stlouisfed.org · api.eia.gov' },
    { id: 'noticias',          nome: 'Newsletter · RSS setorial',  tipo: 'RSS feeds',          atualizacao: 'Diária',        custo: 'Grátis',      endpoint: 'múltiplos RSS' },
    { id: 'be8_profile',       nome: 'Be8 Profile · dados públicos',tipo: 'Curadoria manual',  atualizacao: 'Trimestral',    custo: 'Grátis',      endpoint: 'be8energy.com + imprensa' },
  ];
  const sf = (s && s.fontes) ? s.fontes : {};
  tb.innerHTML = FONTES.map(f => {
    const info = sf[f.id] || {};
    const st = info.status || 'PENDENTE';
    const cls = st === 'OK' ? 'src-live' : st === 'PARCIAL' ? 'src-cached' : st === 'PENDENTE' ? 'src-pending' : 'src-error';
    const label = st === 'OK' ? 'Live' : st === 'PARCIAL' ? 'Parcial' : st === 'PENDENTE' ? 'Pendente' : 'Erro';
    const ultV = info.ultima_verificacao ? info.ultima_verificacao.replace('T', ' ').slice(0, 16) : '—';
    return `<tr>
      <td><strong>${f.nome}</strong></td>
      <td style="color:var(--be8-mist); font-size:12px;">${f.tipo}</td>
      <td style="font-family:var(--font-mono); font-size:11.5px; color:var(--be8-mist);">${f.atualizacao}</td>
      <td style="font-family:var(--font-mono); font-size:11.5px; color:${f.custo.startsWith('Grátis') ? 'var(--be8-green-2)' : 'var(--be8-gold)'};">${f.custo}</td>
      <td style="font-family:var(--font-mono); font-size:10.5px; color:var(--be8-dim);">${f.endpoint}</td>
      <td><span class="src-status ${cls}">${label}</span></td>
      <td class="num" style="color:var(--be8-mist);">${info.linhas || '—'}</td>
      <td style="font-size:11px; color:var(--be8-dim); font-family:var(--font-mono);">${ultV}</td>
    </tr>`;
  }).join('');

  // Resumo no topo da Visão Executiva
  const ok = FONTES.filter(f => (sf[f.id] || {}).status === 'OK').length;
  $('#sources-meta').textContent = `${ok}/${FONTES.length} OK`;
  const summary = $('#sources-summary');
  if (summary) {
    summary.innerHTML = FONTES.map(f => {
      const info = sf[f.id] || {};
      const st = info.status || 'PENDENTE';
      const cls = st === 'OK' ? 'src-live' : st === 'PARCIAL' ? 'src-cached' : st === 'PENDENTE' ? 'src-pending' : 'src-error';
      const label = st === 'OK' ? '✓' : st === 'PARCIAL' ? '~' : st === 'PENDENTE' ? '○' : '✕';
      return `<div style="display:flex; justify-content:space-between; padding:3px 0;">
        <span style="color:var(--be8-mist); font-size:11.5px;">${f.nome.split('·')[0].trim()}</span>
        <span class="src-status ${cls}" style="padding:2px 7px;">${label}</span>
      </div>`;
    }).join('');
  }

  const buildEl = $('#governance-last');
  if (buildEl && s) {
    buildEl.textContent = 'build · ' + (s.ultima_atualizacao_global || '').replace('T',' ').slice(0,16);
  }
}

/* =====================================================================
   RADAR IA · regras determinísticas
   ===================================================================== */
function buildInsights() {
  const bulls = [];
  const bears = [];
  const neutrals = [];
  const cmap = {};
  (STATE.commodities?.commodities || []).forEach(c => cmap[c.id] = c);
  const usd = STATE.cambio?.moedas?.USD;
  const eur = STATE.cambio?.moedas?.EUR;

  // ===== REGRAS DINÂMICAS (baseadas em dados ao vivo) =====

  // Regra 1: dólar diário
  if (usd && usd.variacao_pct != null) {
    if (usd.variacao_pct > 0.2) {
      bulls.push({ type: 'bull', tag: 'CÂMBIO', text: `USD/BRL em alta de ${fmtPct(usd.variacao_pct)} no fechamento (${fmtBRL(usd.cotacao_atual)}) — janela favorável a exportações de óleo e farelo de soja.` });
    } else if (usd.variacao_pct < -0.2) {
      bears.push({ type: 'bear', tag: 'CÂMBIO', text: `USD/BRL em queda de ${fmtPct(usd.variacao_pct)} (${fmtBRL(usd.cotacao_atual)}) — compressão de margem para exportadores; metanol importado fica mais barato.` });
    } else {
      neutrals.push({ type: 'neutral', tag: 'CÂMBIO', text: `USD/BRL estável em ${fmtBRL(usd.cotacao_atual)} (${fmtPct(usd.variacao_pct)}) — ambiente neutro para exportação.` });
    }
  }

  // Regra 2: óleo soja + Brent (combinada — premium pricing biodiesel)
  const oleo = cmap.oleo_soja, brent = cmap.brent;
  if (oleo && brent && oleo.var_d_pct != null && brent.var_d_pct != null) {
    if (oleo.var_d_pct > 0.5 && brent.var_d_pct > 0.5) {
      bulls.push({ type: 'bull', tag: 'BIODIESEL', text: `Alta simultânea óleo soja (${fmtPct(oleo.var_d_pct)}) e Brent (${fmtPct(brent.var_d_pct)}) — pressão de alta no B100; ambiente favorável a repasse.` });
    } else if (oleo.var_d_pct > 1 && brent.var_d_pct < -0.5) {
      bears.push({ type: 'alert', tag: 'MARGEM', text: `Descolamento: óleo soja sobe ${fmtPct(oleo.var_d_pct)} enquanto Brent recua ${fmtPct(brent.var_d_pct)} — atenção à margem biodiesel vs. diesel.` });
    } else if (oleo.var_d_pct < -0.8) {
      bulls.push({ type: 'bull', tag: 'INSUMO', text: `Óleo de soja em queda de ${fmtPct(oleo.var_d_pct)} — oportunidade de melhora de margem do B100.` });
    }
  }

  // Regra 3: óleo soja (qualquer movimento)
  if (oleo && oleo.var_7d_pct != null) {
    if (oleo.var_7d_pct > 2) {
      bears.push({ type: 'alert', tag: 'INSUMO', text: `Óleo de soja acumula ${fmtPct(oleo.var_7d_pct)} em 7 dias — custo principal do B100 sob pressão.` });
    } else if (oleo.var_7d_pct < -2) {
      bulls.push({ type: 'bull', tag: 'INSUMO', text: `Óleo de soja recua ${fmtPct(oleo.var_7d_pct)} em 7 dias — alívio no custo principal do B100.` });
    }
  }

  // Regra 4: soja CBOT trend
  const soja = cmap.soja;
  if (soja && soja.var_30d_pct != null) {
    if (soja.var_30d_pct > 4) {
      bears.push({ type: 'alert', tag: 'ORIGINAÇÃO', text: `Soja CBOT acumula alta de ${fmtPct(soja.var_30d_pct)} em 30d — risco de competição por matéria-prima entre esmagamento e exportação.` });
    } else if (soja.var_30d_pct < -4) {
      bulls.push({ type: 'bull', tag: 'ORIGINAÇÃO', text: `Soja CBOT recua ${fmtPct(soja.var_30d_pct)} em 30d — ambiente favorável para fixação de compras.` });
    }
  }

  // Regra 5: Brent absoluto
  if (brent && brent.ultimo != null) {
    if (brent.ultimo >= 90) {
      bulls.push({ type: 'bull', tag: 'PETRÓLEO', text: `Brent em ${fmtUSD(brent.ultimo)}/bbl (acima de US$ 90) — diesel fóssil caro, janela para precificação premium do B100 nos próximos leilões.` });
    } else if (brent.ultimo < 70) {
      bears.push({ type: 'alert', tag: 'PETRÓLEO', text: `Brent em ${fmtUSD(brent.ultimo)}/bbl (abaixo de US$ 70) — diesel fóssil barato, pressão para baixar preço-teto dos leilões B100.` });
    }
  }

  // Regra 6: Milho (proxy etanol concorrente)
  const milho = cmap.milho;
  if (milho && milho.var_30d_pct != null) {
    if (milho.var_30d_pct > 5) {
      neutrals.push({ type: 'neutral', tag: 'CONCORRÊNCIA', text: `Milho CBOT em alta de ${fmtPct(milho.var_30d_pct)} (30d) — pode reduzir competitividade do etanol de milho vs. biodiesel.` });
    }
  }

  // ===== INSIGHTS ESTRUTURAIS (sempre presentes — base institucional) =====
  bulls.push({ type: 'bull', tag: 'DEMANDA', text: 'Lei 14.993/2024 mantém trajetória B15 → B16 (mar/2026) → B20 (2030). Crescimento estrutural de demanda B100 de ~7% a.a.' });
  bulls.push({ type: 'bull', tag: 'POSICIONAMENTO', text: 'Be8 mantém posição entre os maiores produtores nacionais com capacidade de 1.080 milhões L/ano integrada em 2 plantas (RS+PR).' });
  bears.push({ type: 'alert', tag: 'VOLATILIDADE', text: 'Curva de óleo de soja segue como principal fonte de volatilidade da margem B100. Monitorar variação semanal CBOT.' });

  // ===== GARANTIA DE MÍNIMO 3 + 3 =====
  // Se faltar bulls, completar com positivos estruturais
  while (bulls.length < 3) {
    const extra = [
      { type: 'bull', tag: 'EXPORT', text: 'Be8 Switzerland mantém canal de exportação ativo para EUA e Europa — diversifica risco de demanda interna.' },
      { type: 'bull', tag: 'INTEGRAÇÃO', text: 'Verticalização originação → esmagamento → biodiesel reduz exposição a margens de terceiros.' },
      { type: 'bull', tag: 'CBIO', text: 'Renovabio emite CBIOs por planta certificada — receita adicional não correlacionada com preço B100.' },
    ];
    const e = extra[bulls.length % extra.length];
    if (!bulls.find(b => b.tag === e.tag)) bulls.push(e);
    else break;
  }
  while (bears.length < 3) {
    const extra = [
      { type: 'alert', tag: 'INSUMO', text: 'Exposição estrutural ao preço do óleo de soja (≈70% do custo variável) — risco contínuo.' },
      { type: 'alert', tag: 'REGULATÓRIO', text: 'Decisões CNPE/ANP sobre cronograma e fórmula de leilões podem alterar premissas de margem.' },
      { type: 'alert', tag: 'CONCORRÊNCIA', text: 'Expansão de etanol de milho (Centro-Oeste) compete por share na matriz renovável.' },
    ];
    const e = extra[bears.length % extra.length];
    if (!bears.find(b => b.tag === e.tag)) bears.push(e);
    else break;
  }

  // Concatena: bulls, bears, neutrals
  return [...bulls, ...bears, ...neutrals];
}

function renderRadarIA() {
  const insights = buildInsights();
  STATE.insights = insights;

  // Banner sumário
  const sum = $('#radar-summary');
  if (sum) {
    const tone = insights.filter(i => i.type === 'bull').length - insights.filter(i => i.type === 'bear' || i.type === 'alert').length;
    let mood;
    if (tone >= 2) mood = 'Cenário <strong style="color:var(--be8-green-2);">construtivo</strong> para o biodiesel no curto prazo.';
    else if (tone <= -2) mood = 'Cenário com <strong style="color:#ff8585;">riscos elevados</strong> — atenção a margens e originação.';
    else mood = 'Cenário <strong style="color:var(--be8-gold);">lateral / misto</strong> — monitorar gatilhos.';
    sum.innerHTML = `${mood} Análise consolidada sobre ${insights.length} sinais ao vivo (BCB · Yahoo · ComexStat). Última atualização: ${new Date().toLocaleString('pt-BR')}.`;
  }

  // Bull / Bear
  const renderItem = i => `<div class="insight-row ${i.type}"><span class="ic-pill">${i.tag}</span><div>${i.text}</div></div>`;
  const bulls = insights.filter(i => i.type === 'bull');
  const bears = insights.filter(i => i.type === 'bear' || i.type === 'alert');
  $('#radar-bull').innerHTML = bulls.length ? bulls.map(renderItem).join('') : '<div class="empty-state" style="padding:20px;"><div class="ic">○</div>Nenhum driver positivo destacável.</div>';
  $('#radar-bear').innerHTML = bears.length ? bears.map(renderItem).join('') : '<div class="empty-state" style="padding:20px;"><div class="ic">○</div>Nenhum risco crítico ativo.</div>';

  // Ações recomendadas (gerar a partir dos insights)
  const acoes = [];
  bulls.forEach(b => {
    if (b.tag === 'CÂMBIO') acoes.push({type:'bull', tag:'EXPORT', text:'Avaliar antecipação de embarques de óleo/farelo enquanto câmbio favorece receita em real.'});
    if (b.tag === 'INSUMO') acoes.push({type:'bull', tag:'COMPRAS', text:'Janela para fixação de compras de óleo de soja para os próximos 30-60 dias.'});
    if (b.tag === 'ORIGINAÇÃO') acoes.push({type:'bull', tag:'HEDGE', text:'Aproveitar recuo da soja para fortalecer estoque-pulmão de matéria-prima.'});
  });
  bears.forEach(b => {
    if (b.tag === 'MARGEM') acoes.push({type:'alert', tag:'PRICING', text:'Reavaliar política de pricing B100 — considerar repasse para preservar margem.'});
    if (b.tag === 'ORIGINAÇÃO') acoes.push({type:'alert', tag:'ORIGINAÇÃO', text:'Acelerar fixações antes de nova alta — disputa com exportação se intensifica.'});
    if (b.tag === 'PETRÓLEO') acoes.push({type:'alert', tag:'COMERCIAL', text:'Aproveitar precificação premium do B100 enquanto diesel fóssil estiver caro.'});
  });
  if (acoes.length === 0) acoes.push({type:'neutral', tag:'POSTURA', text:'Manter postura defensiva — sem sinais fortes para ação imediata. Monitorar próximo fechamento.'});

  $('#radar-acoes').innerHTML = acoes.map(renderItem).join('');

  // Alertas na Visão Executiva
  const feed = $('#alerts-feed');
  if (feed) {
    const alerts = insights.filter(i => i.type === 'alert' || i.type === 'bear');
    $('#alerts-count').textContent = alerts.length + ' ativos';
    feed.innerHTML = alerts.length === 0
      ? '<div class="empty-state" style="padding:18px;"><div class="ic">✓</div>Nenhum alerta crítico ativo.</div>'
      : alerts.slice(0,4).map(renderItem).join('');
  }

  // Top 3 oportunidades / riscos na Visão Executiva
  $('#top-opportunities').innerHTML = bulls.length === 0
    ? '<div class="empty-state" style="padding:14px;"><div class="ic">○</div>Sem oportunidades destacadas.</div>'
    : bulls.slice(0,3).map(renderItem).join('');
  $('#top-risks').innerHTML = bears.length === 0
    ? '<div class="empty-state" style="padding:14px;"><div class="ic">✓</div>Sem riscos críticos.</div>'
    : bears.slice(0,3).map(renderItem).join('');

  // Resumo do dia (visão executiva)
  const exec = $('#exec-summary');
  if (exec) {
    const usd = STATE.cambio?.moedas?.USD;
    const cmap = {};
    (STATE.commodities?.commodities || []).forEach(c => cmap[c.id] = c);
    const parts = [];
    if (usd?.cotacao_atual) parts.push(`USD/BRL em ${fmtBRL(usd.cotacao_atual)} (${fmtPct(usd.variacao_pct)})`);
    if (cmap.brent?.ultimo) parts.push(`Brent ${fmtUSD(cmap.brent.ultimo)} (${fmtPct(cmap.brent.var_d_pct)})`);
    if (cmap.soja?.ultimo) parts.push(`soja ${fmtCent(cmap.soja.ultimo)} (${fmtPct(cmap.soja.var_d_pct)})`);
    if (cmap.oleo_soja?.ultimo) parts.push(`óleo soja ${fmtCent(cmap.oleo_soja.ultimo)} (${fmtPct(cmap.oleo_soja.var_d_pct)})`);
    const datelabel = new Date().toLocaleDateString('pt-BR', {day:'numeric', month:'long'});
    exec.innerHTML = parts.length > 0
      ? `<strong>${datelabel}:</strong> ${parts.join(' · ')}. ${insights[0]?.text || ''}`
      : `Aguardando primeira execução do agente para consolidar a leitura. Veja a página de Governança para status.`;
  }
}

/* =====================================================================
   TICKER
   ===================================================================== */
function renderTicker() {
  const items = [];
  const usd = STATE.cambio?.moedas?.USD;
  const eur = STATE.cambio?.moedas?.EUR;
  if (usd?.cotacao_atual) items.push({label:'USD/BRL', val:fmtBRL(usd.cotacao_atual), delta:fmtPct(usd.variacao_pct), cls:deltaClass(usd.variacao_pct)});
  if (eur?.cotacao_atual) items.push({label:'EUR/BRL', val:fmtBRL(eur.cotacao_atual), delta:fmtPct(eur.variacao_pct), cls:deltaClass(eur.variacao_pct)});
  (STATE.commodities?.commodities || []).forEach(c => {
    if (c.ultimo == null) return;
    const fmtF = c.unidade.includes('US$') || c.unidade.includes('MMBtu') ? fmtUSD : c.unidade.includes('¢') ? fmtCent : v => fmtNum(v, 2);
    items.push({label: c.nome.toUpperCase(), val: fmtF(c.ultimo), delta:fmtPct(c.var_d_pct), cls:deltaClass(c.var_d_pct)});
  });
  if (items.length === 0) {
    $('#ticker-track').innerHTML = '<span class="ticker-item"><span class="label">Conectando às fontes…</span></span>'.repeat(8);
    return;
  }
  // Dobra para loop contínuo
  $('#ticker-track').innerHTML = items.concat(items).map(i => `
    <span class="ticker-item">
      <span class="label">${i.label}</span>
      <span class="value">${i.val}</span>
      ${i.delta ? `<span class="delta ${i.cls}">${i.delta}</span>` : ''}
    </span>`).join('');
}

/* =====================================================================
   NEWSLETTER
   ===================================================================== */
function renderNewsletter() {
  const n = STATE.noticias;
  if (!n || n.status === 'PENDENTE' || !n.noticias || n.noticias.length === 0) {
    setStatusBadge('news-status', 'PENDENTE', 'Newsletter · aguardando');
    return;
  }
  setStatusBadge('news-status', n.status || 'OK',
    'Newsletter · ' + (n.ultima_atualizacao || '').slice(0,10));

  $('#news-hero-eyebrow').textContent = 'EDIÇÃO DE ' + new Date().toLocaleDateString('pt-BR', {day:'2-digit', month:'long', year:'numeric'}).toUpperCase() + ' · BE8 MARKET INTELLIGENCE';
  if (n.manchete) {
    $('#news-hero-headline').textContent = n.manchete.titulo || 'Sem manchete principal hoje';
    $('#news-hero-meta').innerHTML = `<a href="${n.manchete.link}" target="_blank" rel="noopener">${n.manchete.fonte || 'Fonte'}</a> · ${n.manchete.data || ''} · ${n.manchete.categoria || ''}`;
  }

  // Top 5
  const top5El = $('#news-top5');
  const top5 = (n.top5 && n.top5.length) ? n.top5 : n.noticias.slice(0, 5);
  top5El.innerHTML = top5.map(it => renderNewsCard(it)).join('');

  // Radares por categoria
  const RADARES = {
    'news-radar-regulatorio':  ['regulação','regulatório','renovabio','cbio','anp','epe','mme','ccee','política'],
    'news-radar-combustiveis': ['combustível','combustíveis','diesel','gasolina','etanol','glp','gnv','petrobras'],
    'news-radar-agro':         ['agro','soja','milho','trigo','grão','grãos','safra','fertilizantes','conab','ibge'],
    'news-radar-commodities':  ['petróleo','brent','wti','commodity','commodities','dólar','câmbio','cme','cbot'],
    'news-radar-concorrentes': ['adm','bunge','cargill','granol','oleoplan','caramuru','camera','biodieselbr'],
    'news-radar-energia':      ['energia','renovável','renováveis','solar','eólica','biocombustível','biocombustíveis','biodiesel','renovavel'],
  };
  Object.entries(RADARES).forEach(([id, keywords]) => {
    const el = $('#' + id);
    if (!el) return;
    const filtered = n.noticias.filter(noticia => {
      const txt = ((noticia.titulo || '') + ' ' + (noticia.categoria || '') + ' ' + (noticia.resumo || '')).toLowerCase();
      return keywords.some(k => txt.includes(k));
    }).slice(0, 3);
    el.innerHTML = filtered.length === 0
      ? '<div style="padding: 12px; color:var(--be8-dim); font-size: 12px;">Sem notícias destacáveis hoje.</div>'
      : filtered.map(it => renderNewsItemMini(it)).join('');
  });

  // Impacto para Be8
  const impactoEl = $('#news-impacto-be8');
  if (impactoEl) {
    if (n.impacto_consolidado_be8) {
      impactoEl.innerHTML = `
        <p>${n.impacto_consolidado_be8}</p>
        ${n.acao_recomendada ? `<div style="margin-top:14px; padding:14px; background:rgba(14,177,148,0.06); border-left:2px solid var(--be8-green-1); border-radius:4px;"><strong style="color:var(--be8-green-1);">Ação recomendada:</strong> ${n.acao_recomendada}</div>` : ''}
      `;
    } else {
      const alto = n.noticias.filter(x => x.impacto === 'alto').length;
      const opo = n.noticias.filter(x => x.tag === 'oportunidade').length;
      const risco = n.noticias.filter(x => x.tag === 'risco').length;
      impactoEl.innerHTML = `
        <p>A edição de hoje traz <strong>${n.noticias.length} notícias</strong> setoriais, das quais <strong style="color:var(--be8-red);">${alto} de alto impacto</strong> para a Be8. Tags registradas: <strong style="color:var(--be8-green-2);">${opo} oportunidades</strong> e <strong style="color:var(--be8-red);">${risco} riscos</strong>.</p>
        <p style="margin-top:14px;">Recomendação automática: monitorar especialmente as manchetes marcadas como <em>regulatório</em> e <em>biodiesel</em>, que historicamente movem o preço do B100 de leilão e impactam diretamente a curva de demanda Be8.</p>`;
    }
  }
}

function renderNewsCard(it) {
  // Mapeamento flexível: o coletor python usa impacto_nivel/tag, mas o frontend pode receber impacto também
  const imp = String(it.impacto || it.impacto_nivel || 'medio').toLowerCase().replace('é', 'e');
  const tagRaw = String(it.tag || 'neutro').toLowerCase();
  // Tag pode vir como 'core', 'regulatorio', 'insumo' (do python) ou 'oportunidade', 'risco'
  const tagMap = {
    'core': { label: 'CORE BIODIESEL', color: 'var(--be8-green-2)', bg: 'rgba(85,201,79,0.12)' },
    'regulatorio': { label: 'REGULATÓRIO', color: 'var(--be8-gold)', bg: 'rgba(212,168,75,0.12)' },
    'insumo': { label: 'INSUMO', color: '#7ed957', bg: 'rgba(126,217,87,0.10)' },
    'macro': { label: 'MACRO', color: 'var(--be8-mist)', bg: 'rgba(168,189,201,0.08)' },
    'oportunidade': { label: 'OPORTUNIDADE', color: 'var(--be8-green-2)', bg: 'rgba(85,201,79,0.12)' },
    'risco': { label: 'RISCO', color: 'var(--be8-red)', bg: 'rgba(232,95,95,0.12)' },
    'neutro': { label: 'NEUTRO', color: 'var(--be8-mist)', bg: 'rgba(168,189,201,0.08)' },
  };
  const t = tagMap[tagRaw] || tagMap['neutro'];
  const impClr = imp === 'alto' ? '#ff8585' : imp === 'medio' ? 'var(--be8-gold)' : 'var(--be8-mist)';
  const impBg = imp === 'alto' ? 'rgba(232,95,95,0.10)' : imp === 'medio' ? 'rgba(212,168,75,0.10)' : 'rgba(168,189,201,0.08)';

  // Inicial da fonte como "thumbnail" visual quando não há imagem
  const fonteInicial = (it.fonte || 'B').charAt(0).toUpperCase();

  return `
    <div class="card news-card" style="display:flex; flex-direction:column; gap:10px; padding:18px;">
      <div style="display:flex; gap:16px; align-items:flex-start;">
        <!-- Thumbnail (placeholder com inicial da fonte) -->
        <div style="flex:0 0 56px; width:56px; height:56px; border-radius:8px; background: var(--grad-energy); display:flex; align-items:center; justify-content:center; font-family:var(--font-display); font-size:24px; font-weight:600; color:#081f2e;">${fonteInicial}</div>

        <div style="flex:1; min-width:0;">
          <div style="display:flex; align-items:center; gap:10px; font-family:var(--font-mono); font-size:10.5px; letter-spacing:0.06em; text-transform:uppercase; margin-bottom:8px; flex-wrap:wrap;">
            <span style="color:var(--be8-green-1);">${(it.categoria || 'geral').toUpperCase()}</span>
            <span style="color:var(--be8-dim);">·</span>
            <span style="color:var(--be8-mist);">${it.fonte || 'Fonte'}</span>
            <span style="color:var(--be8-dim);">·</span>
            <span style="color:var(--be8-dim);">${(it.data || '').replace(/\d+:\d+:\d+.*$/, '').slice(0,16)}</span>
          </div>
          <h3 style="font-family:var(--font-display); font-size:18px; font-weight:500; line-height:1.3; color:var(--be8-ice); margin-bottom:6px;">
            <a href="${it.link || '#'}" target="_blank" rel="noopener" style="color:inherit; text-decoration:none;" onmouseover="this.style.color='var(--be8-green-1)'" onmouseout="this.style.color='var(--be8-ice)'">${it.titulo || '(sem título)'}</a>
          </h3>
          ${it.resumo ? `<p style="font-size:13px; color:var(--be8-mist); line-height:1.6; margin-bottom:8px;">${it.resumo.length > 280 ? it.resumo.slice(0, 280) + '…' : it.resumo}</p>` : ''}

          <!-- Tags -->
          <div style="display:flex; gap:6px; flex-wrap:wrap; margin-top:8px;">
            <span style="font-size:10px; padding:3px 9px; border-radius:3px; font-weight:600; color:${impClr}; background:${impBg}; letter-spacing:0.05em;">IMPACTO ${imp.toUpperCase()}</span>
            <span style="font-size:10px; padding:3px 9px; border-radius:3px; color:${t.color}; background:${t.bg}; letter-spacing:0.05em; font-weight:600;">${t.label}</span>
          </div>
        </div>
      </div>

      ${it.impacto_be8 ? `<div style="margin-top:4px; padding:10px 14px; border-left:3px solid var(--be8-green-1); background:rgba(14,177,148,0.05); border-radius:0 6px 6px 0; font-size:12px; color:var(--be8-mist); line-height:1.55;"><strong style="color:var(--be8-green-1); letter-spacing:0.03em;">▸ Impacto Be8:</strong> ${it.impacto_be8}</div>` : ''}

      ${it.link ? `<a href="${it.link}" target="_blank" rel="noopener" style="display:inline-flex; align-self:flex-start; align-items:center; gap:6px; margin-top:4px; padding:7px 14px; background:rgba(14,177,148,0.08); border:1px solid rgba(14,177,148,0.25); border-radius:4px; font-family:var(--font-mono); font-size:11px; color:var(--be8-green-1); letter-spacing:0.05em; transition:all 0.15s;" onmouseover="this.style.background='rgba(14,177,148,0.18)';this.style.borderColor='var(--be8-green-1)'" onmouseout="this.style.background='rgba(14,177,148,0.08)';this.style.borderColor='rgba(14,177,148,0.25)'">ABRIR NOTÍCIA <span style="font-size:14px;">→</span></a>` : ''}
    </div>`;
}

function renderNewsItemMini(it) {
  const imp = String(it.impacto || it.impacto_nivel || 'medio').toLowerCase();
  const impDot = imp === 'alto' ? '#ff8585' : imp === 'medio' ? 'var(--be8-gold)' : 'var(--be8-green-1)';
  return `<a href="${it.link || '#'}" target="_blank" rel="noopener" style="display:block; padding:12px 14px; border-left:2px solid ${impDot}; background:rgba(8,31,46,0.4); border-radius:0 6px 6px 0; transition: all 0.15s ease; text-decoration:none;" onmouseover="this.style.background='rgba(14,177,148,0.08)';this.style.transform='translateX(2px)';" onmouseout="this.style.background='rgba(8,31,46,0.4)';this.style.transform='translateX(0)';">
    <div style="font-size:13px; color:var(--be8-ice); line-height:1.4; font-weight:500;">${it.titulo || '(sem título)'}</div>
    <div style="margin-top:6px; display:flex; justify-content:space-between; align-items:center;">
      <span style="font-family:var(--font-mono); font-size:10px; color:var(--be8-dim); letter-spacing:0.04em;">${it.fonte || ''} · ${(it.data || '').slice(0,10)}</span>
      <span style="font-family:var(--font-mono); font-size:10px; color:var(--be8-green-1);">abrir →</span>
    </div>
  </a>`;
}

/* =====================================================================
   BE8 PROFILE
   ===================================================================== */
function renderBe8Profile() {
  const p = STATE.be8_profile;
  if (!p || p.status === 'PENDENTE') return;

  $('#profile-tagline').textContent = p.tagline || 'Energia que move o Brasil';
  if (p.identidade) {
    $('#profile-headline').textContent = p.identidade.razao_social_atual || 'Be8';
    $('#profile-summary').innerHTML = `
      A Be8 (anteriormente <strong>BSBIOS</strong>) é uma das principais produtoras de biodiesel do Brasil, fundada em ${p.identidade.data_fundacao || '2005'}, com sede em ${p.identidade.sede || 'Passo Fundo (RS)'}. 
      Controlada pelo ${p.identidade.controlador || 'ECB Group'}, integra esmagamento de soja, produção de B100, comercialização de óleo, farelo e glicerina, com operações de exportação via Be8 Switzerland.
    `;
    $('#profile-fundacao').textContent = p.identidade.ano_fundacao || '2005';
    $('#profile-fundacao-ctx').textContent = 'Início produção: ' + (p.identidade.inicio_producao || '2007');
    $('#profile-sede').textContent = (p.identidade.sede || '').split('·')[0].trim();
  }
  if (p.capacidade_total) {
    $('#profile-capacidade').innerHTML = fmtNum(p.capacidade_total.biodiesel_milhoes_l_ano, 0) + ' <span class="unit">M L/ano</span>';
  }
  const shareInd = p.indicadores_publicos?.find(i => (i.indicador||'').toLowerCase().includes('market share biodiesel brasil (2023)'));
  if (shareInd) {
    $('#profile-share').textContent = shareInd.valor;
    $('#profile-share-ctx').textContent = shareInd.fonte;
  }

  // Plantas
  const plantasEl = $('#profile-plantas');
  if (plantasEl && p.plantas_industriais) {
    plantasEl.innerHTML = p.plantas_industriais.map(pl => `
      <div class="card">
        <div class="card-header">
          <div class="card-label">${pl.unidade}</div>
          <span class="card-meta">desde ${pl.ano_inicio}</span>
        </div>
        <div style="margin-top:10px; font-size:13px; color:var(--be8-mist); line-height:1.6;">
          <div><strong style="color:var(--be8-ice);">Tipo:</strong> ${pl.tipo}</div>
          ${pl.capacidade_biodiesel_litros_ano ? `<div><strong style="color:var(--be8-ice);">Cap. B100:</strong> ${fmtNum(pl.capacidade_biodiesel_litros_ano/1e6, 0)} M L/ano</div>` : ''}
          ${pl.capacidade_esmagamento_t_ano ? `<div><strong style="color:var(--be8-ice);">Cap. esmagamento:</strong> ${fmtNum(pl.capacidade_esmagamento_t_ano/1e6, 2)} M t/ano</div>` : ''}
          ${pl.observacao ? `<div style="margin-top:8px; padding-top:8px; border-top:1px solid var(--be8-border); color:var(--be8-dim); font-size:11.5px;">${pl.observacao}</div>` : ''}
        </div>
      </div>
    `).join('');
  }

  // Cadeia de valor — HERO (imagem) + cards numerados abaixo
  const cadeiaEl = $('#profile-cadeia');
  if (cadeiaEl) {
    const imgHTML = p.cadeia_valor_imagem ? `
      <div style="margin-bottom:24px; border-radius:10px; overflow:hidden; border:1px solid var(--be8-border-2); box-shadow: 0 4px 24px rgba(0,0,0,0.4); background:#0e1a25;">
        <img src="${p.cadeia_valor_imagem}" alt="Cadeia de Valor Be8" style="display:block; width:100%; height:auto;">
        ${p.cadeia_valor_legenda ? `<div style="padding:14px 18px; background: rgba(8,31,46,0.6); font-size:11.5px; color:var(--be8-mist); line-height:1.6; border-top:1px solid var(--be8-border);"><strong style="color:var(--be8-ice);">▸ Leitura visual:</strong> ${p.cadeia_valor_legenda}</div>` : ''}
      </div>` : '';

    let cardsHTML = '';
    if (p.cadeia_valor && Array.isArray(p.cadeia_valor) && p.cadeia_valor.length > 0) {
      cardsHTML = `
        <div style="font-family:var(--font-mono); font-size:11px; color:var(--be8-green-1); letter-spacing:0.1em; margin-bottom:14px; text-transform:uppercase;">Sumário navegável · 10 etapas-chave</div>
        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:10px;">
          ${p.cadeia_valor.map((etapa, i) => `
            <div style="padding:14px; background:linear-gradient(155deg, rgba(14,177,148,0.06) 0%, rgba(8,31,46,0.2) 50%); border:1px solid var(--be8-border-2); border-radius:8px;">
              <div style="font-family:var(--font-mono); font-size:10.5px; color:var(--be8-green-1); letter-spacing:0.12em; margin-bottom:6px;">${String(i+1).padStart(2,'0')}</div>
              <div style="font-size:13px; color:var(--be8-ice); font-weight:500; line-height:1.4;">${etapa}</div>
            </div>
          `).join('')}
        </div>`;
    }
    cadeiaEl.innerHTML = imgHTML + cardsHTML;
  }

  // Timeline
  if (p.linha_do_tempo) {
    $('#profile-timeline').innerHTML = `
      <div style="display:flex; flex-direction:column; gap:14px;">
        ${p.linha_do_tempo.map(item => `
          <div style="display:flex; gap:18px; align-items:flex-start;">
            <div style="font-family:var(--font-display); font-size:22px; color:var(--be8-green-2); font-weight:400; min-width:75px;">${item.ano}</div>
            <div style="flex:1; padding-top:5px; padding-bottom:14px; border-bottom:1px solid var(--be8-border); font-size:13.5px; color:var(--be8-mist); line-height:1.55;">
              ${item.evento}
            </div>
          </div>
        `).join('')}
      </div>`;
  }

  // Sustentabilidade (aceita lista direta ou objeto.destaques)
  const sustent = p.sustentabilidade_inovacao
                || (p.sustentabilidade && p.sustentabilidade.destaques)
                || null;
  if (sustent && Array.isArray(sustent)) {
    $('#profile-sustentabilidade').innerHTML = '<ul style="margin-left:18px;">' +
      sustent.map(s => `<li style="margin-bottom:8px;">${s}</li>`).join('') +
      '</ul>';
  }

  // Posicionamento (aceita lista pronta ou estruturada)
  const posList = p.posicionamento_competitivo_lista
               || (p.posicionamento_competitivo && p.posicionamento_competitivo.vantagens)
               || null;
  if (posList && Array.isArray(posList)) {
    $('#profile-posicionamento').innerHTML = '<ul style="margin-left:18px;">' +
      posList.map(s => `<li style="margin-bottom:8px;">${s}</li>`).join('') +
      '</ul>';
  }

  // Fontes
  if (p.fontes_referencia) {
    $('#profile-fontes').innerHTML = p.fontes_referencia.map(url => `<li><a href="${url}" target="_blank" rel="noopener" style="color:var(--be8-green-1);">${url}</a></li>`).join('');
  }
}

/* =====================================================================
   MODO TV
   ===================================================================== */
const TV_DEFAULT_CONFIG = {
  pages: [
    { id: 'executive',         label: '01 · Visão Executiva',   enabled: true,  duration: 45, scroll: false },
    { id: 'cambio-commodities',label: '02 · Câmbio & Commod.',  enabled: true,  duration: 50, scroll: true  },
    { id: 'graos',             label: '03 · Grãos & Safra',     enabled: true,  duration: 50, scroll: true  },
    { id: 'biodiesel',         label: '04 · Biodiesel',         enabled: true,  duration: 50, scroll: true  },
    { id: 'combustiveis',      label: '05 · Combustíveis ANP',  enabled: true,  duration: 45, scroll: true  },
    { id: 'comex',             label: '06 · Comércio Exterior', enabled: true,  duration: 40, scroll: false },
    { id: 'radar',             label: '07 · Radar IA',          enabled: true,  duration: 45, scroll: false },
    { id: 'governanca',        label: '08 · Governança',        enabled: false, duration: 30, scroll: false },
    { id: 'newsletter',        label: '09 · Newsletter',        enabled: true,  duration: 75, scroll: true  },
    { id: 'be8-profile',       label: '10 · Be8 Profile',       enabled: true,  duration: 50, scroll: true  },
  ]
};

const TV = {
  active: false,
  paused: false,
  config: null,
  cycle: [],
  cycleIdx: 0,
  pageStart: 0,
  pageDuration: 30,
  timer: null,
  scrollTimer: null,
};

function loadTVConfig() {
  try {
    const raw = localStorage.getItem('be8_tv_config');
    if (raw) return JSON.parse(raw);
  } catch (e) {}
  return JSON.parse(JSON.stringify(TV_DEFAULT_CONFIG));
}
function saveTVConfig(cfg) {
  localStorage.setItem('be8_tv_config', JSON.stringify(cfg));
}

function renderTVConfigOverlay() {
  TV.config = loadTVConfig();
  const tbody = $('#tv-config-tbody');
  tbody.innerHTML = TV.config.pages.map((p, i) => `
    <tr data-idx="${i}">
      <td>${p.label}</td>
      <td><input type="checkbox" data-field="enabled" ${p.enabled?'checked':''}></td>
      <td><input type="number" data-field="duration" min="10" max="300" value="${p.duration}"></td>
      <td><input type="checkbox" data-field="scroll" ${p.scroll?'checked':''}></td>
      <td><input type="number" data-field="order" min="1" max="20" value="${i+1}" style="width:50px;"></td>
    </tr>`).join('');
  $('#tv-config-overlay').classList.add('show');
}

function readTVConfigFromOverlay() {
  const rows = $$('#tv-config-tbody tr');
  const items = rows.map(tr => {
    const idx = +tr.dataset.idx;
    const orig = TV.config.pages[idx];
    return {
      ...orig,
      enabled:  tr.querySelector('[data-field="enabled"]').checked,
      duration: +tr.querySelector('[data-field="duration"]').value || 30,
      scroll:   tr.querySelector('[data-field="scroll"]').checked,
      _order:   +tr.querySelector('[data-field="order"]').value || (idx+1),
    };
  });
  items.sort((a,b) => a._order - b._order);
  items.forEach(i => delete i._order);
  return { pages: items };
}

function startTV() {
  TV.config = loadTVConfig();
  TV.cycle = TV.config.pages.filter(p => p.enabled);
  if (TV.cycle.length === 0) {
    alert('Habilite ao menos uma página no Modo TV.');
    return;
  }
  TV.active = true;
  TV.paused = false;
  TV.cycleIdx = 0;
  document.body.classList.add('tv-mode');
  $('#tv-bar').style.display = 'flex';
  // Tentar fullscreen
  if (document.documentElement.requestFullscreen) {
    document.documentElement.requestFullscreen().catch(() => {});
  }
  tvShowCurrent();
}

function stopTV() {
  TV.active = false;
  document.body.classList.remove('tv-mode');
  $('#tv-bar').style.display = 'none';
  if (TV.timer) { clearInterval(TV.timer); TV.timer = null; }
  if (TV.scrollTimer) { clearInterval(TV.scrollTimer); TV.scrollTimer = null; }
  if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
}

function tvShowCurrent() {
  const page = TV.cycle[TV.cycleIdx];
  if (!page) return;
  setActivePage(page.id);
  TV.pageStart = Date.now();
  TV.pageDuration = page.duration * 1000;
  $('#tv-page-label').textContent = 'PÁGINA · ' + page.label;

  if (TV.timer) clearInterval(TV.timer);
  if (TV.scrollTimer) clearInterval(TV.scrollTimer);

  // Tick de progresso + avanço
  TV.timer = setInterval(() => {
    if (TV.paused) return;
    const elapsed = Date.now() - TV.pageStart;
    const pct = Math.min(elapsed / TV.pageDuration, 1) * 100;
    $('#tv-fill').style.width = pct + '%';
    if (elapsed >= TV.pageDuration) tvNext();
  }, 200);

  // Rolagem automática
  if (page.scroll) {
    const docH = document.documentElement.scrollHeight;
    const winH = window.innerHeight;
    const maxScroll = docH - winH;
    if (maxScroll > 50) {
      const stepInterval = 100; // ms
      const totalSteps = Math.floor((TV.pageDuration * 0.85) / stepInterval); // termina rolagem antes do fim
      const scrollStep = maxScroll / totalSteps;
      let stepIdx = 0;
      window.scrollTo({top: 0, behavior: 'instant'});
      TV.scrollTimer = setInterval(() => {
        if (TV.paused) return;
        stepIdx++;
        window.scrollTo({top: stepIdx * scrollStep, behavior: 'instant'});
        if (stepIdx >= totalSteps) clearInterval(TV.scrollTimer);
      }, stepInterval);
    }
  } else {
    window.scrollTo({top: 0, behavior: 'instant'});
  }
}

function tvNext() {
  TV.cycleIdx = (TV.cycleIdx + 1) % TV.cycle.length;
  tvShowCurrent();
}

function tvPause() {
  TV.paused = !TV.paused;
  $('#tv-pause').textContent = TV.paused ? '▶ Retomar' : '⏸ Pausar';
  if (TV.paused) {
    // congela barra
  } else {
    // ao retomar, ajustar pageStart pra continuar de onde parou
    const elapsed = parseFloat($('#tv-fill').style.width) / 100 * TV.pageDuration;
    TV.pageStart = Date.now() - elapsed;
  }
}

function bindTVControls() {
  $('#tv-toggle').addEventListener('click', () => {
    if (TV.active) stopTV();
    else startTV();
  });
  $('#tv-config-btn').addEventListener('click', renderTVConfigOverlay);
  $('#tv-config-cancel').addEventListener('click', () => $('#tv-config-overlay').classList.remove('show'));
  $('#tv-config-save').addEventListener('click', () => {
    const cfg = readTVConfigFromOverlay();
    saveTVConfig(cfg);
    TV.config = cfg;
    $('#tv-config-overlay').classList.remove('show');
    startTV();
  });
  $('#tv-pause').addEventListener('click', tvPause);
  $('#tv-next').addEventListener('click', tvNext);
  $('#tv-exit').addEventListener('click', stopTV);

  // ESC sai do modo TV
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && TV.active) stopTV();
    if (TV.active && e.key === ' ') { e.preventDefault(); tvPause(); }
    if (TV.active && e.key === 'ArrowRight') tvNext();
  });
}

/* =====================================================================
   ORQUESTRAÇÃO
   ===================================================================== */
async function reloadAllData() {
  const btn = $('#refresh-all');
  if (btn) { btn.disabled = true; btn.textContent = '↻ atualizando…'; }
  try {
    const [cambio, commodities, conab, anpComb, anpB100, comex, noticias, profile, status] = await Promise.all([
      loadJSON('data/cambio.json'),
      loadJSON('data/commodities.json'),
      loadJSON('data/conab_graos.json'),
      loadJSON('data/anp_combustiveis.json'),
      loadJSON('data/anp_b100.json'),
      loadJSON('data/comex.json'),
      loadJSON('data/noticias.json'),
      loadJSON('data/be8_profile.json'),
      loadJSON('data/status_fontes.json'),
    ]);
    STATE.cambio = cambio;
    STATE.commodities = commodities;
    STATE.conab = conab;
    STATE.anp_combustiveis = anpComb;
    STATE.anp_b100 = anpB100;
    STATE.comex = comex;
    STATE.noticias = noticias;
    STATE.be8_profile = profile;
    STATE.status_fontes = status;

    renderCambio();
    renderCommodities();
    renderTicker();
    renderConab();
    renderBiodieselANP();
    renderANPCombustiveis();
    renderComex();
    renderGovernance();
    renderNewsletter();
    renderBe8Profile();
    renderRadarIA();
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '↻ Atualizar'; }
  }
}

async function snapshotPNG() {
  const btn = $('#export-snapshot');
  if (btn) { btn.disabled = true; btn.textContent = '↓ capturando…'; }
  try {
    // Encontrar a página ativa
    const page = document.querySelector('.page.active');
    if (!page) {
      alert('Nenhuma página ativa para capturar.');
      return;
    }
    // Estratégia: usar html2canvas via CDN se disponível; caso contrário, fallback para print
    if (!window.html2canvas) {
      // Carregar dinamicamente
      await new Promise((resolve, reject) => {
        const s = document.createElement('script');
        s.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2canvas/1.4.1/html2canvas.min.js';
        s.onload = resolve;
        s.onerror = reject;
        document.head.appendChild(s);
      }).catch(() => null);
    }
    if (window.html2canvas) {
      const canvas = await window.html2canvas(page, {
        backgroundColor: '#050f17',
        scale: 2,
        useCORS: true,
        logging: false,
        windowWidth: document.documentElement.scrollWidth,
      });
      const tabName = (document.querySelector('.nav-tab.active')?.textContent || 'painel').trim().replace(/\s+/g, '_').toLowerCase();
      const date = new Date().toISOString().slice(0,10);
      const link = document.createElement('a');
      link.download = `be8_${tabName}_${date}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
    } else {
      // Fallback: abrir diálogo de impressão (usuário salva como PDF)
      window.print();
    }
  } catch (e) {
    console.error('snapshot falhou:', e);
    alert('Não foi possível gerar snapshot. Use Ctrl+P (imprimir → salvar como PDF) como alternativa.');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '↓ Snapshot'; }
  }
}

async function boot() {
  setSessionClock();
  setInterval(setSessionClock, 1000);

  // Carregar todos os JSONs em paralelo
  await reloadAllData();

  // Bind controles
  bindTVControls();
  $('#refresh-all')?.addEventListener('click', reloadAllData);
  $('#export-snapshot')?.addEventListener('click', snapshotPNG);
}

document.addEventListener('DOMContentLoaded', boot);
