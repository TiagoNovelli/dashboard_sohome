/* ══════════════════════════════════════════════════════════════════════════════
   SoHome Dashboard — Main JavaScript
   Vanilla JS · sem dependências do framework Odoo
   ══════════════════════════════════════════════════════════════════════════════ */
'use strict';

// ─── Config de cores por esquema ──────────────────────────────────────────────
const COLOR_PALETTES = {
  violet: { main: '#a78bfa', light: 'rgba(167,139,250,0.15)', border: 'rgba(167,139,250,0.6)', stops: ['#8b5cf6','#a78bfa','#c4b5fd','#ddd6fe','#ede9fe'] },
  blue:   { main: '#60a5fa', light: 'rgba(96,165,250,0.15)',  border: 'rgba(96,165,250,0.6)',  stops: ['#3b82f6','#60a5fa','#93c5fd','#bfdbfe','#dbeafe'] },
  cyan:   { main: '#22d3ee', light: 'rgba(34,211,238,0.15)',  border: 'rgba(34,211,238,0.6)',  stops: ['#06b6d4','#22d3ee','#67e8f9','#a5f3fc','#cffafe'] },
  green:  { main: '#4ade80', light: 'rgba(74,222,128,0.15)',  border: 'rgba(74,222,128,0.6)',  stops: ['#22c55e','#4ade80','#86efac','#bbf7d0','#dcfce7'] },
  amber:  { main: '#fbbf24', light: 'rgba(251,191,36,0.15)',  border: 'rgba(251,191,36,0.6)',  stops: ['#f59e0b','#fbbf24','#fcd34d','#fde68a','#fef3c7'] },
  rose:   { main: '#fb7185', light: 'rgba(251,113,133,0.15)', border: 'rgba(251,113,133,0.6)', stops: ['#f43f5e','#fb7185','#fda4af','#fecdd3','#ffe4e6'] },
  slate:  { main: '#94a3b8', light: 'rgba(148,163,184,0.15)', border: 'rgba(148,163,184,0.6)', stops: ['#64748b','#94a3b8','#cbd5e1','#e2e8f0','#f1f5f9'] },
};

// ─── Chart.js defaults ────────────────────────────────────────────────────────
function applyChartDefaults(theme = 'dark') {
  if (typeof Chart === 'undefined') return;
  const isDark = theme === 'dark';
  Chart.defaults.color         = isDark ? '#9898bb' : '#44445a';
  Chart.defaults.borderColor   = isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.07)';
  Chart.defaults.font.family   = "'Inter', system-ui, sans-serif";
  Chart.defaults.font.size     = 11;
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.padding  = 16;
  Chart.defaults.plugins.tooltip.backgroundColor = isDark ? '#1a1a2e' : '#ffffff';
  Chart.defaults.plugins.tooltip.borderColor     = isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)';
  Chart.defaults.plugins.tooltip.borderWidth     = 1;
  Chart.defaults.plugins.tooltip.titleColor      = isDark ? '#eeeef8' : '#18182a';
  Chart.defaults.plugins.tooltip.bodyColor       = isDark ? '#9898bb' : '#3d3d5c';
  Chart.defaults.plugins.tooltip.padding         = 10;
  Chart.defaults.plugins.tooltip.cornerRadius    = 8;
}

// ─── API helper (JSON-RPC Odoo) ───────────────────────────────────────────────
async function apiCall(url, params = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest',
    },
    body: JSON.stringify({ jsonrpc: '2.0', method: 'call', id: Date.now(), params }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const json = await res.json();
  if (json.error) throw new Error(json.error.data?.message || json.error.message || 'Erro desconhecido');
  return json.result;
}

// ─── Toast ────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || 'ℹ️'}</span><span>${msg}</span>`;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => {
    el.classList.add('toast-out');
    el.addEventListener('animationend', () => el.remove());
  }, 3500);
}

// ─── Formatação de número ─────────────────────────────────────────────────────
function formatNumber(val) {
  if (val === null || val === undefined || val === '') return '—';
  const num = parseFloat(val);
  if (isNaN(num)) return String(val);
  if (Math.abs(num) >= 1_000_000) return (num / 1_000_000).toFixed(1).replace('.0', '') + 'M';
  if (Math.abs(num) >= 1_000) return (num / 1_000).toFixed(1).replace('.0', '') + 'K';
  if (Number.isInteger(num)) return num.toLocaleString('pt-BR');
  return num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// ══════════════════════════════════════════════════════════════════════════════
//  APP
// ══════════════════════════════════════════════════════════════════════════════
class SoHomeDashboard {
  constructor() {
    this.boards          = [];
    this.activeBoardId   = window.__SOHOME__?.active_board_id || null;
    this.canEdit         = window.__SOHOME__?.can_edit || false;
    this.charts          = {};   // widgetId → Chart instance
    this.refreshTimers   = {};   // widgetId → setInterval id
    this.editingWidgetId = null;
    this.widgetDataCache = {};   // widgetId → {columns, rows, meta}
  }

  // ─── Init ────────────────────────────────────────────────────────────────
  async init() {
    const theme = this.initTheme();
    applyChartDefaults(theme);
    this._bindStaticEvents();
    requestAnimationFrame(() => {
      setTimeout(() => document.documentElement.classList.add('theme-ready'), 100);
    });
    document.getElementById('userBadge').textContent = window.__SOHOME__?.user_name || '';

    // Esconde controles de edição para visualizadores
    if (!this.canEdit) {
      document.getElementById('btnNewBoard')?.remove();
      document.getElementById('btnAddWidget')?.remove();
    }

    await this.loadBoards();
  }

  // ─── Tema ─────────────────────────────────────────────────────────────────
  initTheme() {
    const saved = localStorage.getItem('sohome-theme') || 'dark';
    this._syncThemeButton(saved);
    return saved;
  }

  toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme') || 'dark';
    const next    = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('sohome-theme', next);
    this._syncThemeButton(next);
    applyChartDefaults(next);
    this._recreateChartsFromCache(next);
  }

  _syncThemeButton(theme) {
    const btn = document.getElementById('btnThemeToggle');
    if (!btn) return;
    btn.title = theme === 'dark' ? 'Mudar para tema claro' : 'Mudar para tema escuro';
  }

  _recreateChartsFromCache(theme) {
    Object.entries(this.widgetDataCache).forEach(([widgetId, cached]) => {
      const body = document.getElementById(`wbody-${widgetId}`);
      if (!body) return;
      const type = cached.meta.chart_type;
      if (type === 'number' || type === 'table') return;
      this._renderWidgetContent(body, cached.meta, cached);
    });
  }

  // ─── Carrega dashboards ──────────────────────────────────────────────────
  async loadBoards() {
    try {
      const res = await apiCall('/sohome/api/boards');
      this.boards  = res.boards || [];
      this.canEdit = res.can_edit || false;

      this._renderSidebar();

      if (this.activeBoardId) {
        const found = this.boards.find(b => b.id === this.activeBoardId);
        if (found) { this.openBoard(found); return; }
      }
      if (this.boards.length > 0) {
        this.openBoard(this.boards[0]);
      } else {
        this._showEmptyBoard();
      }
    } catch (e) {
      toast('Erro ao carregar dashboards: ' + e.message, 'error');
    }
  }

  // ─── Sidebar ─────────────────────────────────────────────────────────────
  _renderSidebar() {
    const list = document.getElementById('boardList');
    if (this.boards.length === 0) {
      list.innerHTML = '<li class="board-item" style="opacity:.4;pointer-events:none"><span class="board-name">Nenhum dashboard</span></li>';
      return;
    }
    list.innerHTML = this.boards.map(b => `
      <li class="board-item${b.id === this.activeBoardId ? ' active' : ''}"
          data-board-id="${b.id}" title="${b.name}">
        <span class="board-icon">${b.icon || '📊'}</span>
        <span class="board-name">${b.name}</span>
        ${this.canEdit ? `
          <button class="board-delete-btn" title="Excluir dashboard"
                  onclick="event.stopPropagation(); app.deleteBoard(${b.id})">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
              <path d="M10 11v6"/><path d="M14 11v6"/>
            </svg>
          </button>
        ` : ''}
      </li>
    `).join('');

    list.querySelectorAll('.board-item').forEach(el => {
      el.addEventListener('click', () => {
        const id = parseInt(el.dataset.boardId);
        const board = this.boards.find(b => b.id === id);
        if (board) this.openBoard(board);
      });
    });
  }

  _setActiveBoardInSidebar(boardId) {
    document.querySelectorAll('.board-item').forEach(el => {
      el.classList.toggle('active', parseInt(el.dataset.boardId) === boardId);
    });
  }

  // ─── Abre um dashboard ───────────────────────────────────────────────────
  openBoard(board) {
    this.activeBoardId = board.id;
    this._setActiveBoardInSidebar(board.id);

    document.getElementById('boardTitle').textContent = `${board.icon || '📊'}  ${board.name}`;
    document.getElementById('boardSubtitle').textContent = board.description || '';

    history.replaceState({}, '', `/sohome/dashboard?board_id=${board.id}`);

    // Limpa timers e gráficos anteriores
    Object.values(this.refreshTimers).forEach(t => clearInterval(t));
    this.refreshTimers = {};
    Object.values(this.charts).forEach(c => { try { c.destroy(); } catch (_) {} });
    this.charts = {};

    // Renderiza barra de filtros (se houver filtros)
    this._renderFilterBar(board);

    // Renderiza widgets usando filtros padrão
    this._renderWidgets(board.widgets || []);
  }

  _showEmptyBoard() {
    document.getElementById('boardTitle').textContent = 'Dashboards';
    document.getElementById('boardSubtitle').textContent = 'Crie um dashboard para começar';
    document.getElementById('filterBar').innerHTML = '';
    document.getElementById('widgetGrid').innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📊</div>
        <h3>Nenhum dashboard ainda</h3>
        <p>Clique em "Novo Dashboard" para começar</p>
        ${this.canEdit ? '<button class="btn-primary-sm" id="btnAddWidgetEmpty">+ Novo Dashboard</button>' : ''}
      </div>`;
    document.getElementById('btnAddWidgetEmpty')?.addEventListener('click', () => {
      this.openModal('modalNewBoard');
    });
  }

  // ─── Barra de filtros ─────────────────────────────────────────────────────
  _renderFilterBar(board) {
    const bar = document.getElementById('filterBar');
    const filters = board.filters || [];

    if (!filters.length) {
      bar.innerHTML = '';
      return;
    }

    const inputsHtml = filters.map(f => {
      const inputType = { date: 'date', integer: 'number', char: 'text' }[f.filter_type] || 'text';
      return `
        <div class="filter-item">
          <label class="filter-label">${f.name}</label>
          <input type="${inputType}"
                 class="filter-input form-input"
                 id="filter-${f.param_key}"
                 data-key="${f.param_key}"
                 value="${f.default_value || ''}"/>
        </div>`;
    }).join('');

    bar.innerHTML = `
      <div class="filter-bar">
        <span class="filter-bar-label">🔍 Filtros</span>
        ${inputsHtml}
        <button class="btn-apply-filters" onclick="app.applyFilters()">Aplicar</button>
      </div>`;
  }

  _getFilterValues() {
    const board = this.boards.find(b => b.id === this.activeBoardId);
    if (!board) return {};
    const values = {};
    (board.filters || []).forEach(f => {
      const input = document.getElementById(`filter-${f.param_key}`);
      values[f.param_key] = (input?.value ?? f.default_value) || '';
    });
    return values;
  }

  async applyFilters() {
    const board = this.boards.find(b => b.id === this.activeBoardId);
    if (!board) return;
    const filterValues = this._getFilterValues();
    await Promise.all(board.widgets.map(w => this._loadWidgetData(w, filterValues)));
    toast('Filtros aplicados!', 'success');
  }

  // ─── Renderiza widgets ───────────────────────────────────────────────────
  _renderWidgets(widgets) {
    const grid = document.getElementById('widgetGrid');
    if (widgets.length === 0) {
      grid.innerHTML = `
        <div class="empty-state" id="emptyState">
          <div class="empty-icon">📈</div>
          <h3>Nenhum widget ainda</h3>
          <p>Adicione um widget com uma query SQL para visualizar seus dados</p>
          ${this.canEdit ? '<button class="btn-primary-sm" id="btnAddWidgetEmpty">+ Adicionar Widget</button>' : ''}
        </div>`;
      document.getElementById('btnAddWidgetEmpty')?.addEventListener('click', () => {
        this.openWidgetModal();
      });
      return;
    }

    grid.innerHTML = widgets.map(w => this._buildWidgetCard(w)).join('');

    const filterValues = this._getFilterValues();
    widgets.forEach(w => this._loadWidgetData(w, filterValues));
  }

  _buildWidgetCard(w) {
    const actionsHtml = this.canEdit ? `
      <div class="widget-actions">
        <button class="widget-action-btn" title="Editar" onclick="app.editWidget(${w.id})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
          </svg>
        </button>
        <button class="widget-action-btn" title="Atualizar" onclick="app.refreshWidget(${w.id})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
        </button>
        <button class="widget-action-btn delete" title="Remover" onclick="app.deleteWidget(${w.id})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/>
            <path d="M10 11v6"/><path d="M14 11v6"/>
          </svg>
        </button>
      </div>` : `
      <div class="widget-actions">
        <button class="widget-action-btn" title="Atualizar" onclick="app.refreshWidget(${w.id})">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
          </svg>
        </button>
      </div>`;

    return `
      <div class="widget-card" id="wcard-${w.id}"
           data-widget-id="${w.id}"
           data-size="${w.size || 2}"
           data-color="${w.color_scheme || 'violet'}">
        <div class="widget-header">
          <div class="widget-header-left">
            <div class="widget-icon">${w.icon || '📈'}</div>
            <div class="widget-meta">
              <div class="widget-title">${w.name}</div>
              ${w.description ? `<div class="widget-subtitle">${w.description}</div>` : ''}
            </div>
          </div>
          ${actionsHtml}
        </div>
        <div class="widget-body" id="wbody-${w.id}">
          <div class="widget-loading">
            <div class="spinner"></div>
            <span>Carregando...</span>
          </div>
        </div>
      </div>`;
  }

  // ─── Carrega dados de um widget ──────────────────────────────────────────
  async _loadWidgetData(widgetMeta, filterParams = {}) {
    const body = document.getElementById(`wbody-${widgetMeta.id}`);
    if (!body) return;
    try {
      const res = await apiCall(`/sohome/api/widget/${widgetMeta.id}/data`, {
        filter_params: filterParams,
      });
      if (!res.success) {
        body.innerHTML = `<div class="widget-error"><div class="widget-error-icon">⚠️</div><span>${res.error || 'Erro ao executar query'}</span></div>`;
        return;
      }
      this._renderWidgetContent(body, widgetMeta, res);

      if (widgetMeta.refresh_interval && widgetMeta.refresh_interval >= 30) {
        this.refreshTimers[widgetMeta.id] = setInterval(() => {
          this._loadWidgetData(widgetMeta, this._getFilterValues());
        }, widgetMeta.refresh_interval * 1000);
      }
    } catch (e) {
      body.innerHTML = `<div class="widget-error"><div class="widget-error-icon">⚠️</div><span>${e.message}</span></div>`;
    }
  }

  _renderWidgetContent(body, meta, res) {
    const { columns, rows } = res;
    const type    = meta.chart_type;
    const color   = meta.color_scheme || 'violet';
    const palette = COLOR_PALETTES[color] || COLOR_PALETTES.violet;

    if (this.charts[meta.id]) {
      try { this.charts[meta.id].destroy(); } catch (_) {}
      delete this.charts[meta.id];
    }

    this.widgetDataCache[meta.id] = { columns, rows, meta };

    // ── KPI / Número ─────────────────────────────────────────────────────
    if (type === 'number') {
      const val   = rows.length > 0 ? rows[0][0] : null;
      const label = columns.length > 1 ? String(rows[0][1] || '') : '';

      let linkHtml = '';
      if (meta.odoo_model) {
        const domain = meta.odoo_domain || '[]';
        const url = `/web#model=${encodeURIComponent(meta.odoo_model)}&view_type=list&domain=${encodeURIComponent(domain)}`;
        linkHtml = `
          <a href="${url}" class="kpi-odoo-link" target="_blank" title="Ver registros no Odoo">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
              <polyline points="15 3 21 3 21 9"/>
              <line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            Ver no Odoo
          </a>`;
      }

      body.innerHTML = `
        <div class="widget-kpi">
          <div class="kpi-value">${meta.prefix || ''}${formatNumber(val)}${meta.suffix || ''}</div>
          ${label ? `<div class="kpi-label">${label}</div>` : ''}
          ${linkHtml}
        </div>`;
      return;
    }

    // ── Tabela ────────────────────────────────────────────────────────────
    if (type === 'table') {
      if (!rows.length) { body.innerHTML = '<div class="widget-loading"><span>Sem dados</span></div>'; return; }
      const headers = columns.map(c => `<th>${c}</th>`).join('');
      const trows   = rows.map(r =>
        `<tr>${r.map(c => `<td>${c === null ? '—' : c}</td>`).join('')}</tr>`
      ).join('');
      body.innerHTML = `
        <div class="widget-table-wrap">
          <table class="widget-table">
            <thead><tr>${headers}</tr></thead>
            <tbody>${trows}</tbody>
          </table>
        </div>`;
      return;
    }

    // ── Gráficos Chart.js ─────────────────────────────────────────────────
    if (!rows.length) { body.innerHTML = '<div class="widget-loading"><span>Sem dados</span></div>'; return; }
    const labels = rows.map(r => String(r[0] ?? ''));
    const values = rows.map(r => parseFloat(r[1]) || 0);

    body.innerHTML = `<div class="widget-chart-wrap"><canvas id="chart-${meta.id}"></canvas></div>`;
    const canvas = document.getElementById(`chart-${meta.id}`);
    if (!canvas || typeof Chart === 'undefined') return;

    let chartType, datasets, options = {};

    if (type === 'bar' || type === 'bar_horizontal') {
      chartType = 'bar';
      datasets  = [{
        data: values,
        backgroundColor: palette.stops.slice(0, values.length).concat(
          Array(Math.max(0, values.length - 5)).fill(palette.main)
        ),
        borderRadius: 6,
        borderSkipped: false,
      }];
      options = {
        indexAxis: type === 'bar_horizontal' ? 'y' : 'x',
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: Chart.defaults.borderColor }, ticks: { maxRotation: 35 } },
          y: { grid: { color: Chart.defaults.borderColor }, beginAtZero: true },
        },
      };
    } else if (type === 'line') {
      chartType = 'line';
      datasets  = [{
        data: values,
        borderColor: palette.main,
        backgroundColor: 'transparent',
        borderWidth: 2.5,
        pointBackgroundColor: palette.main,
        pointRadius: 3,
        pointHoverRadius: 5,
        tension: 0.4,
      }];
      options = {
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
        },
      };
    } else if (type === 'area') {
      chartType = 'line';
      datasets  = [{
        data: values,
        borderColor: palette.main,
        backgroundColor: palette.light,
        borderWidth: 2.5,
        fill: true,
        pointBackgroundColor: palette.main,
        pointRadius: 3,
        tension: 0.4,
      }];
      options = {
        plugins: { legend: { display: false } },
        scales: {
          x: { grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { grid: { color: 'rgba(255,255,255,0.04)' }, beginAtZero: true },
        },
      };
    } else if (type === 'pie' || type === 'donut') {
      chartType = 'doughnut';
      const isDark = (document.documentElement.getAttribute('data-theme') || 'dark') === 'dark';
      datasets  = [{
        data: values,
        backgroundColor: palette.stops,
        borderColor: isDark ? '#0d0d18' : '#ffffff',
        borderWidth: 3,
        hoverOffset: 6,
      }];
      options = {
        cutout: type === 'donut' ? '65%' : '0%',
        plugins: {
          legend: {
            display: true,
            position: 'right',
            labels: { generateLabels: (chart) => {
              return labels.map((l, i) => ({
                text: l.length > 14 ? l.substring(0, 13) + '…' : l,
                fillStyle: palette.stops[i % palette.stops.length],
                strokeStyle: 'transparent',
                index: i,
              }));
            }},
          },
        },
      };
    }

    const chart = new Chart(canvas, {
      type: chartType,
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 600, easing: 'easeOutQuart' },
        ...options,
      },
    });
    this.charts[meta.id] = chart;
  }

  // ─── Refresh ─────────────────────────────────────────────────────────────
  async refreshWidget(widgetId) {
    const board = this.boards.find(b => b.id === this.activeBoardId);
    if (!board) return;
    const w = board.widgets.find(w => w.id === widgetId);
    if (!w) return;
    const body = document.getElementById(`wbody-${widgetId}`);
    if (body) body.innerHTML = '<div class="widget-loading"><div class="spinner"></div><span>Atualizando...</span></div>';
    await this._loadWidgetData(w, this._getFilterValues());
  }

  async refreshAll() {
    const btn = document.getElementById('btnRefreshAll');
    if (btn) btn.classList.add('spinning');
    const board = this.boards.find(b => b.id === this.activeBoardId);
    if (board) {
      const filterValues = this._getFilterValues();
      await Promise.all(board.widgets.map(w => this._loadWidgetData(w, filterValues)));
    }
    if (btn) btn.classList.remove('spinning');
    toast('Dashboard atualizado!', 'success');
  }

  // ─── Board CRUD ───────────────────────────────────────────────────────────
  async saveBoard() {
    const btn  = document.getElementById('btnSaveBoard');
    const name = document.getElementById('newBoardName').value.trim();
    if (!name) { toast('Informe o nome do dashboard', 'error'); return; }

    const icon        = document.querySelector('#boardIconPicker .emoji-opt.selected')?.dataset.val || '📊';
    const description = document.getElementById('newBoardDesc').value.trim();

    btn.disabled    = true;
    btn.textContent = 'Criando...';
    try {
      const res = await apiCall('/sohome/api/board/create', { name, icon, description });
      if (!res.success) throw new Error(res.error);
      toast(`Dashboard "${name}" criado!`, 'success');
      this.closeModal('modalNewBoard');
      document.getElementById('newBoardName').value = '';
      document.getElementById('newBoardDesc').value = '';
      await this.loadBoards();
      const newBoard = this.boards.find(b => b.id === res.id);
      if (newBoard) this.openBoard(newBoard);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      btn.disabled    = false;
      btn.textContent = 'Criar Dashboard';
    }
  }

  async deleteBoard(boardId) {
    if (!confirm('Excluir este dashboard e todos os seus widgets? Esta ação não pode ser desfeita.')) return;
    try {
      const res = await apiCall(`/sohome/api/board/${boardId}/delete`);
      if (!res.success) throw new Error(res.error);
      toast('Dashboard excluído', 'info');
      this.activeBoardId = null;
      await this.loadBoards();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  // ─── Widget CRUD ──────────────────────────────────────────────────────────
  openWidgetModal(widgetId = null) {
    if (!this.activeBoardId) { toast('Selecione um dashboard primeiro', 'info'); return; }

    this.editingWidgetId = widgetId;
    const modal = document.getElementById('modalWidget');
    document.getElementById('modalWidgetTitle').textContent = widgetId ? 'Editar Widget' : 'Novo Widget';
    document.getElementById('widgetId').value = widgetId || '';

    if (!widgetId) {
      document.getElementById('widgetName').value      = '';
      document.getElementById('widgetDesc').value      = '';
      document.getElementById('widgetSql').value       = '';
      document.getElementById('widgetPrefix').value    = '';
      document.getElementById('widgetSuffix').value    = '';
      document.getElementById('widgetOdooModel').value = '';
      document.getElementById('widgetOdooDomain').value= '[]';
      document.getElementById('widgetChartType').value = 'number';
      document.getElementById('widgetColor').value     = 'violet';
      document.getElementById('widgetSize').value      = '2';
      document.getElementById('sqlResultMsg').textContent = '';
      this._setEmojiPicker('widgetIconPicker', '📈');
      this._toggleOdooLinkFields('number');
    } else {
      const board = this.boards.find(b => b.id === this.activeBoardId);
      const w     = board?.widgets.find(w => w.id === widgetId);
      if (w) {
        document.getElementById('widgetName').value       = w.name;
        document.getElementById('widgetDesc').value       = w.description;
        document.getElementById('widgetChartType').value  = w.chart_type;
        document.getElementById('widgetColor').value      = w.color_scheme;
        document.getElementById('widgetSize').value       = w.size;
        document.getElementById('widgetPrefix').value     = w.prefix || '';
        document.getElementById('widgetSuffix').value     = w.suffix || '';
        document.getElementById('widgetOdooModel').value  = w.odoo_model || '';
        document.getElementById('widgetOdooDomain').value = w.odoo_domain || '[]';
        this._setEmojiPicker('widgetIconPicker', w.icon || '📈');
        this._toggleOdooLinkFields(w.chart_type);
      }
    }
    this.openModal('modalWidget');
  }

  _toggleOdooLinkFields(chartType) {
    const wrap = document.getElementById('odooLinkWrap');
    if (wrap) wrap.style.display = chartType === 'number' ? '' : 'none';
  }

  async editWidget(widgetId) {
    this.openWidgetModal(widgetId);
  }

  async saveWidget() {
    const btn  = document.getElementById('btnSaveWidget');
    const name = document.getElementById('widgetName').value.trim();
    const sql  = document.getElementById('widgetSql').value.trim();

    if (!name) { toast('Informe o título do widget', 'error'); return; }
    if (!sql && !this.editingWidgetId) { toast('Informe a query SQL', 'error'); return; }

    const icon   = document.querySelector('#widgetIconPicker .emoji-opt.selected')?.dataset.val || '📈';
    const params = {
      name,
      description:  document.getElementById('widgetDesc').value.trim(),
      icon,
      chart_type:   document.getElementById('widgetChartType').value,
      color_scheme: document.getElementById('widgetColor').value,
      size:         document.getElementById('widgetSize').value,
      prefix:       document.getElementById('widgetPrefix').value.trim(),
      suffix:       document.getElementById('widgetSuffix').value.trim(),
      odoo_model:   document.getElementById('widgetOdooModel').value.trim(),
      odoo_domain:  document.getElementById('widgetOdooDomain').value.trim() || '[]',
    };
    if (sql) params.sql_query = sql;

    btn.disabled    = true;
    btn.textContent = 'Salvando...';
    try {
      let res;
      if (this.editingWidgetId) {
        res = await apiCall(`/sohome/api/widget/${this.editingWidgetId}/update`, params);
      } else {
        params.board_id = this.activeBoardId;
        res = await apiCall('/sohome/api/widget/create', params);
      }
      if (!res.success) throw new Error(res.error || 'Erro ao salvar');

      toast(this.editingWidgetId ? 'Widget atualizado!' : 'Widget criado!', 'success');
      this.closeModal('modalWidget');
      await this.loadBoards();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      btn.disabled    = false;
      btn.textContent = 'Salvar Widget';
    }
  }

  async deleteWidget(widgetId) {
    if (!confirm('Remover este widget?')) return;
    try {
      const res = await apiCall(`/sohome/api/widget/${widgetId}/delete`);
      if (!res.success) throw new Error(res.error);
      toast('Widget removido', 'info');
      await this.loadBoards();
    } catch (e) {
      toast(e.message, 'error');
    }
  }

  async testSql() {
    const sql = document.getElementById('widgetSql').value.trim();
    const msg = document.getElementById('sqlResultMsg');
    if (!sql) { msg.textContent = 'Digite uma query antes de executar'; msg.className = 'sql-result-msg error'; return; }

    if (!sql.trim().toUpperCase().startsWith('SELECT')) {
      msg.textContent = '❌ Apenas SELECT é permitido';
      msg.className   = 'sql-result-msg error';
      return;
    }

    msg.textContent = '⏳ Executando...';
    msg.className   = 'sql-result-msg';

    if (this.editingWidgetId) {
      try {
        await apiCall(`/sohome/api/widget/${this.editingWidgetId}/update`, { sql_query: sql });
        const res = await apiCall(`/sohome/api/widget/${this.editingWidgetId}/data`);
        if (res.success) {
          msg.textContent = `✅ ${res.row_count} linha(s) · Colunas: ${res.columns.join(', ')}`;
          msg.className   = 'sql-result-msg success';
        } else {
          msg.textContent = '❌ ' + (res.error || 'Erro');
          msg.className   = 'sql-result-msg error';
        }
      } catch (e) {
        msg.textContent = '❌ ' + e.message;
        msg.className   = 'sql-result-msg error';
      }
    } else {
      msg.textContent = '💡 Salve o widget para testar a query';
      msg.className   = 'sql-result-msg';
    }
  }

  // ─── Modal helpers ────────────────────────────────────────────────────────
  openModal(id)  { document.getElementById(id)?.classList.add('open'); }
  closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

  _setEmojiPicker(pickerId, val) {
    document.querySelectorAll(`#${pickerId} .emoji-opt`).forEach(el => {
      el.classList.toggle('selected', el.dataset.val === val);
    });
  }

  // ─── Event bindings ───────────────────────────────────────────────────────
  _bindStaticEvents() {
    document.getElementById('sidebarToggle')?.addEventListener('click', () => {
      document.getElementById('sidebar').classList.toggle('collapsed');
    });

    document.getElementById('btnNewBoard')?.addEventListener('click', () => this.openModal('modalNewBoard'));
    document.getElementById('btnSaveBoard')?.addEventListener('click', () => this.saveBoard());

    document.getElementById('btnAddWidget')?.addEventListener('click', () => this.openWidgetModal());
    document.getElementById('btnSaveWidget')?.addEventListener('click', () => this.saveWidget());
    document.getElementById('btnTestSql')?.addEventListener('click', () => this.testSql());

    document.getElementById('btnRefreshAll')?.addEventListener('click', () => this.refreshAll());
    document.getElementById('btnThemeToggle')?.addEventListener('click', () => this.toggleTheme());

    // Esconde campos de link Odoo quando tipo não é KPI
    document.getElementById('widgetChartType')?.addEventListener('change', (e) => {
      this._toggleOdooLinkFields(e.target.value);
    });

    document.querySelectorAll('[data-modal]').forEach(btn => {
      btn.addEventListener('click', () => this.closeModal(btn.dataset.modal));
    });

    document.querySelectorAll('.modal-overlay').forEach(overlay => {
      overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.classList.remove('open');
      });
    });

    document.querySelectorAll('.emoji-picker-row').forEach(picker => {
      picker.addEventListener('click', (e) => {
        const opt = e.target.closest('.emoji-opt');
        if (!opt) return;
        picker.querySelectorAll('.emoji-opt').forEach(o => o.classList.remove('selected'));
        opt.classList.add('selected');
      });
    });

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
      }
    });
  }
}

// ─── Bootstrap ────────────────────────────────────────────────────────────────
let app;
document.addEventListener('DOMContentLoaded', () => {
  app = new SoHomeDashboard();
  app.init().catch(e => console.error('SoHome init error:', e));
});
