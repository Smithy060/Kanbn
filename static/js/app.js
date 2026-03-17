/* ── Kanbn app.js — global state, routing, helpers, app controller ── */

/* ── Global state ── */
const state = {
  currentProject: null,
  columns: [],
  labels: [],
  filters: { priority: null, assignee: null, label: null },
  activeView: 'board',
  sidebarCollapsed: localStorage.getItem('sidebar-collapsed') === 'true',
  userName: localStorage.getItem('kanbn-user') || 'User',
};

/* ── Utilities ── */
function esc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

function escAttr(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/"/g,'&quot;').replace(/'/g,'&#39;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

function toast(msg, type) {
  type = type || 'info';
  const container = document.getElementById('toast-container');
  if (!container) return;
  const el = document.createElement('div');
  el.className = 'toast ' + type;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('hiding');
    el.addEventListener('animationend', () => el.remove());
  }, 2800);
}

function timeAgo(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  const now = new Date();
  const diff = (now - d) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
  if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
  if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
  return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
}

/* ── Topbar ── */
const Topbar = {
  renderFilters() {
    const container = document.getElementById('activeFilters');
    if (!container) return;
    const chips = [];
    if (state.filters.priority) {
      chips.push(`<div class="filter-chip active" onclick="Topbar.clearFilter('priority')">
        <span class="badge badge-${state.filters.priority}">${state.filters.priority.toUpperCase()}</span>
        <button class="filter-chip-close">&times;</button>
      </div>`);
    }
    if (state.filters.label) {
      chips.push(`<div class="filter-chip active" onclick="Topbar.clearFilter('label')">
        ${esc(state.filters.label)}
        <button class="filter-chip-close">&times;</button>
      </div>`);
    }
    if (state.filters.assignee) {
      chips.push(`<div class="filter-chip active" onclick="Topbar.clearFilter('assignee')">
        ${esc(state.filters.assignee)}
        <button class="filter-chip-close">&times;</button>
      </div>`);
    }
    container.innerHTML = chips.join('');
  },

  clearFilter(key) {
    state.filters[key] = null;
    this.renderFilters();
    if (typeof Sidebar !== 'undefined') Sidebar.renderLabels();
    Board.render();
  },

  initDropdowns() {
    const btn = document.getElementById('priorityFilterBtn');
    const menu = document.getElementById('priorityFilterMenu');
    if (!btn || !menu) return;

    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      menu.classList.toggle('open');
    });

    menu.querySelectorAll('.dropdown-item').forEach(item => {
      item.addEventListener('click', () => {
        const p = item.dataset.priority;
        state.filters.priority = p || null;
        menu.classList.remove('open');
        if (p) btn.classList.add('active'); else btn.classList.remove('active');
        this.renderFilters();
        Board.render();
      });
    });

    document.addEventListener('click', () => menu.classList.remove('open'));
  },
};

/* ── Quick-add modal ── */
const QuickAdd = {
  open() {
    const overlay = document.getElementById('quickAddModal');
    if (!overlay) return;
    overlay.classList.add('active');
    const sel = document.getElementById('quickAddColumn');
    if (sel && state.columns) {
      sel.innerHTML = state.columns.map(c =>
        `<option value="${c.id}">${esc(c.name)}</option>`
      ).join('');
    }
    const input = document.getElementById('quickAddTitle');
    if (input) { input.value = ''; input.focus(); }
  },

  close() {
    const overlay = document.getElementById('quickAddModal');
    if (overlay) overlay.classList.remove('active');
  },

  async submit() {
    const title = (document.getElementById('quickAddTitle').value || '').trim();
    if (!title) return;
    const columnId = document.getElementById('quickAddColumn').value;
    const priority = document.getElementById('quickAddPriority').value;
    try {
      await API.createTask({
        title, priority, column_id: columnId,
        project_id: state.currentProject.id,
      });
      this.close();
      await App.loadBoard();
      toast('Task created', 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },

  init() {
    const cancelBtn = document.getElementById('quickAddCancel');
    const submitBtn = document.getElementById('quickAddSubmit');
    const titleInput = document.getElementById('quickAddTitle');
    const overlay = document.getElementById('quickAddModal');

    if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());
    if (submitBtn) submitBtn.addEventListener('click', () => this.submit());
    if (titleInput) titleInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') this.submit();
      if (e.key === 'Escape') this.close();
    });
    if (overlay) overlay.addEventListener('click', (e) => {
      if (e.target === overlay) this.close();
    });
  },
};

/* ── App controller ── */
const App = {
  async init() {
    try {
      const projects = await API.getProjects();
      if (projects.length === 0) {
        toast('No project found', 'error');
        return;
      }
      state.currentProject = projects[0];

      const [board, labels] = await Promise.all([
        API.getBoard(state.currentProject.id),
        API.getLabels(state.currentProject.id),
      ]);

      state.columns = board.columns || [];
      state.labels = labels || [];

      // Sidebar collapse state
      const sidebar = document.getElementById('sidebar');
      if (sidebar && state.sidebarCollapsed) {
        sidebar.classList.add('collapsed');
      }

      // Sidebar collapse button
      const collapseBtn = document.getElementById('sidebarCollapseBtn');
      if (collapseBtn) {
        collapseBtn.addEventListener('click', () => {
          state.sidebarCollapsed = !state.sidebarCollapsed;
          localStorage.setItem('sidebar-collapsed', state.sidebarCollapsed);
          sidebar.classList.toggle('collapsed', state.sidebarCollapsed);
        });
      }

      // Sidebar labels + search + add-label + user profile
      this._initSidebarLabels();
      this._initSidebarSearch();
      this._initSidebarAddLabel();
      this._initUserProfile();

      // Topbar
      Topbar.initDropdowns();
      Topbar.renderFilters();

      // New task button
      const newBtn = document.getElementById('newTaskBtn');
      if (newBtn) newBtn.addEventListener('click', () => QuickAdd.open());
      QuickAdd.init();

      // Nav click handlers
      document.querySelectorAll('.nav-item[data-view]').forEach(n => {
        n.addEventListener('click', (e) => {
          e.preventDefault();
          App.navigate(n.dataset.view);
        });
      });

      // Route from hash
      this._applyRoute();

      // Render active view
      this._renderActiveView();
    } catch (e) {
      console.error('Init failed:', e);
      toast('Failed to load: ' + e.message, 'error');
    }
  },

  async loadBoard() {
    try {
      const board = await API.getBoard(state.currentProject.id);
      state.columns = board.columns || [];
      Board.render();
    } catch (e) {
      toast('Error loading board: ' + e.message, 'error');
    }
  },

  async loadLabels() {
    try {
      state.labels = await API.getLabels(state.currentProject.id);
      this._initSidebarLabels();
    } catch (e) {
      console.error('Failed to load labels:', e);
    }
  },

  navigate(view) {
    if (state.activeView === view) return;
    state.activeView = view;
    window.location.hash = '#/' + view;

    document.querySelectorAll('.nav-item').forEach(n => {
      n.classList.toggle('active', n.dataset.view === view);
    });
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    const target = document.getElementById('view-' + view);
    if (target) target.classList.add('active');

    const titles = { board: 'Board', list: 'List', calendar: 'Calendar', analytics: 'Analytics' };
    const titleEl = document.getElementById('topbarTitle');
    if (titleEl) titleEl.textContent = titles[view] || 'Kanbn';

    this._renderActiveView();
  },

  openTask(taskId) {
    if (typeof Modal !== 'undefined') Modal.open(taskId);
  },

  closeTask() {
    if (typeof Modal !== 'undefined') Modal.close();
  },

  _applyRoute() {
    const hash = window.location.hash || '#/board';
    const parts = hash.replace('#/', '').split('/');
    const view = parts[0] || 'board';
    const validViews = ['board', 'list', 'calendar', 'analytics'];
    if (validViews.includes(view)) {
      state.activeView = view;
      document.querySelectorAll('.nav-item').forEach(n => {
        n.classList.toggle('active', n.dataset.view === view);
      });
      document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
      const target = document.getElementById('view-' + view);
      if (target) target.classList.add('active');

      const titles = { board: 'Board', list: 'List', calendar: 'Calendar', analytics: 'Analytics' };
      const titleEl = document.getElementById('topbarTitle');
      if (titleEl) titleEl.textContent = titles[view] || 'Kanbn';

      this._renderActiveView();
    }
    if (parts[0] === 'task' && parts[1]) {
      this.openTask(parts[1]);
    }
  },

  _renderActiveView() {
    switch (state.activeView) {
      case 'board': Board.render(); break;
      case 'list': if (typeof ListView !== 'undefined') ListView.render(); break;
      case 'calendar': if (typeof CalendarView !== 'undefined') CalendarView.render(); break;
      case 'analytics': if (typeof AnalyticsView !== 'undefined') AnalyticsView.render(); break;
    }
  },

  /* ── Sidebar helpers (work with index.html's existing sidebar DOM) ── */

  _initSidebarLabels() {
    const container = document.getElementById('labelList');
    if (!container) return;
    if (!state.labels || state.labels.length === 0) {
      container.innerHTML = '<div style="font-size:12px;color:var(--text-dim);padding:6px 8px;font-style:italic;">No labels yet</div>';
      return;
    }
    container.innerHTML = state.labels.map(label => {
      const active = state.filters.label === label.name ? ' active' : '';
      return `<div class="label-item${active}" onclick="App._filterByLabel('${escAttr(label.name)}')">
        <span class="label-dot" style="background:${esc(label.color)}"></span>
        <span class="label-name">${esc(label.name)}</span>
      </div>`;
    }).join('');
  },

  _filterByLabel(name) {
    state.filters.label = state.filters.label === name ? null : name;
    this._initSidebarLabels();
    Topbar.renderFilters();
    Board.render();
  },

  _searchTimer: null,

  _initSidebarSearch() {
    const input = document.getElementById('searchInput');
    const results = document.getElementById('searchResults');
    if (!input || !results) return;

    input.addEventListener('input', () => {
      clearTimeout(this._searchTimer);
      const q = input.value.trim();
      if (!q) { results.classList.remove('active'); return; }
      this._searchTimer = setTimeout(async () => {
        try {
          const tasks = await API.getTasks({ q });
          if (tasks.length === 0) {
            results.innerHTML = '<div style="padding:12px;font-size:13px;color:var(--text-dim);text-align:center;">No results</div>';
          } else {
            results.innerHTML = tasks.slice(0, 8).map(t => {
              const shortId = t.id.slice(0, 6).toUpperCase();
              return `<div class="search-result-item" onclick="document.getElementById('searchResults').classList.remove('active'); App.openTask('${t.id}')">
                <div class="search-result-title">${esc(t.title)}</div>
                <div class="search-result-meta">#${shortId} &middot; ${esc(t.priority || 'medium')}</div>
              </div>`;
            }).join('');
          }
          results.classList.add('active');
        } catch (e) { console.error('Search failed:', e); }
      }, 300);
    });

    input.addEventListener('focus', () => {
      if (input.value.trim()) input.dispatchEvent(new Event('input'));
    });

    // Close search results on click outside
    document.addEventListener('click', (e) => {
      if (!input.contains(e.target) && !results.contains(e.target)) {
        results.classList.remove('active');
      }
    });
  },

  _initSidebarAddLabel() {
    const btn = document.getElementById('addLabelBtn');
    if (!btn) return;

    // Create inline form if not present
    let form = document.getElementById('sidebarAddLabelForm');
    if (!form) {
      form = document.createElement('div');
      form.id = 'sidebarAddLabelForm';
      form.style.display = 'none';
      form.style.padding = '6px 8px';
      form.innerHTML = `
        <div style="display:flex;gap:6px;flex-direction:column;">
          <input type="text" id="sidebarLabelName" class="input-base" placeholder="Label name"
                 style="padding:5px 8px;font-size:12px;">
          <div style="display:flex;gap:6px;align-items:center;">
            <input type="color" id="sidebarLabelColor" value="#0D7377"
                   style="width:28px;height:28px;padding:0;border:none;cursor:pointer;background:none;">
            <button class="btn btn-primary btn-xs" id="sidebarLabelSubmit">Add</button>
            <button class="btn btn-ghost btn-xs" id="sidebarLabelCancel">Cancel</button>
          </div>
        </div>`;
      btn.parentElement.appendChild(form);
    }

    btn.addEventListener('click', () => {
      form.style.display = 'block';
      document.getElementById('sidebarLabelName').focus();
    });

    const submit = async () => {
      const nameEl = document.getElementById('sidebarLabelName');
      const colorEl = document.getElementById('sidebarLabelColor');
      const name = (nameEl.value || '').trim();
      if (!name) { nameEl.focus(); return; }
      try {
        await API.createLabel({ project_id: state.currentProject.id, name, color: colorEl.value });
        form.style.display = 'none';
        nameEl.value = '';
        await App.loadLabels();
        toast('Label created', 'success');
      } catch (e) { toast('Error: ' + e.message, 'error'); }
    };

    document.getElementById('sidebarLabelSubmit').addEventListener('click', submit);
    document.getElementById('sidebarLabelCancel').addEventListener('click', () => {
      form.style.display = 'none';
      document.getElementById('sidebarLabelName').value = '';
    });
    document.getElementById('sidebarLabelName').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') submit();
      if (e.key === 'Escape') { form.style.display = 'none'; document.getElementById('sidebarLabelName').value = ''; }
    });
  },

  _initUserProfile() {
    const nameEl = document.getElementById('userName');
    const avatarEl = document.getElementById('userAvatar');
    if (!nameEl) return;

    // Apply stored name
    nameEl.textContent = state.userName;
    if (avatarEl) avatarEl.textContent = state.userName[0].toUpperCase();

    // Click to edit
    nameEl.addEventListener('click', () => {
      const input = document.createElement('input');
      input.type = 'text';
      input.className = 'input-base';
      input.value = state.userName;
      input.style.cssText = 'width:100%;padding:4px 8px;font-size:13px;';
      nameEl.replaceWith(input);
      input.focus();
      input.select();

      const save = () => {
        const name = (input.value || '').trim() || 'User';
        state.userName = name;
        localStorage.setItem('kanbn-user', name);
        nameEl.textContent = name;
        if (avatarEl) avatarEl.textContent = name[0].toUpperCase();
        input.replaceWith(nameEl);
      };
      input.addEventListener('blur', save);
      input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') save();
        if (e.key === 'Escape') { input.value = state.userName; save(); }
      });
    });
  },
};

/* ── Hash routing ── */
window.addEventListener('hashchange', () => App._applyRoute());

/* ── Boot ── */
document.addEventListener('DOMContentLoaded', () => App.init());
