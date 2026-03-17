/* ── Kanbn list.js — list/table view ── */

const ListView = {
  _sortCol: 'updated_at',
  _sortDir: 'desc',
  _selected: new Set(),

  async render() {
    const body = document.getElementById('listBody');
    if (!body) return;

    try {
      const tasks = await API.getTasks({
        project_id: state.currentProject ? state.currentProject.id : undefined,
        sort: this._sortCol,
        order: this._sortDir,
        priority: state.filters.priority || undefined,
        label: state.filters.label || undefined,
      });

      // Build column lookup
      const colMap = {};
      (state.columns || []).forEach(c => { colMap[c.id] = c; });

      if (tasks.length === 0) {
        body.innerHTML = '<tr><td colspan="8" class="empty-state">No tasks yet</td></tr>';
      } else {
        body.innerHTML = tasks.map(t => {
          const col = colMap[t.column_id] || {};
          const shortId = t.id.slice(0, 6).toUpperCase();
          const selected = this._selected.has(t.id) ? ' selected' : '';
          const dueClass = this._dueClass(t.due_date);
          const dueStr = t.due_date ? new Date(t.due_date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) : '\u2014';
          const updatedStr = t.updated_at ? timeAgo(t.updated_at) : '\u2014';

          return '<tr class="' + selected + '" data-id="' + t.id + '" onclick="ListView._onRowClick(event, \'' + t.id + '\')">' +
            '<td><input type="checkbox" ' + (this._selected.has(t.id) ? 'checked' : '') + ' onclick="event.stopPropagation(); ListView._toggleSelect(\'' + t.id + '\', this.checked)"></td>' +
            '<td class="list-id-cell">#' + shortId + '</td>' +
            '<td class="list-title-cell">' + esc(t.title) + '</td>' +
            '<td class="list-status-cell"><span class="column-dot" style="background:' + esc(col.color || '#7A9090') + '"></span>' + esc(col.name || '') + '</td>' +
            '<td><span class="badge badge-' + (t.priority || 'medium') + '">' + (t.priority || 'medium').toUpperCase() + '</span></td>' +
            '<td>' + esc(t.assignee || '\u2014') + '</td>' +
            '<td class="list-due-cell ' + dueClass + '">' + dueStr + '</td>' +
            '<td>' + updatedStr + '</td>' +
          '</tr>';
        }).join('');
      }

      // Sort indicators
      document.querySelectorAll('.list-table th[data-sort]').forEach(th => {
        th.classList.remove('sort-asc', 'sort-desc');
        if (th.dataset.sort === this._sortCol) {
          th.classList.add(this._sortDir === 'asc' ? 'sort-asc' : 'sort-desc');
        }
      });

      this._updateBulkActions();
    } catch (e) {
      body.innerHTML = '<tr><td colspan="8" class="empty-state">Failed to load tasks</td></tr>';
    }
  },

  _dueClass(dueDate) {
    if (!dueDate) return '';
    const due = new Date(dueDate);
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    due.setHours(0, 0, 0, 0);
    const diff = (due - now) / (1000 * 60 * 60 * 24);
    if (diff < 0) return 'overdue';
    if (diff < 1) return 'today';
    return '';
  },

  _onRowClick(e, taskId) {
    App.openTask(taskId);
  },

  _toggleSelect(taskId, checked) {
    if (checked) this._selected.add(taskId);
    else this._selected.delete(taskId);
    this._updateBulkActions();
    // Update row styling
    const row = document.querySelector('tr[data-id="' + taskId + '"]');
    if (row) row.classList.toggle('selected', checked);
  },

  _updateBulkActions() {
    const bar = document.getElementById('bulkActions');
    const count = document.getElementById('bulkCount');
    if (!bar) return;
    if (this._selected.size > 0) {
      bar.classList.add('active');
      count.textContent = this._selected.size + ' selected';
    } else {
      bar.classList.remove('active');
    }
  },
};

// Sort header click handlers
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.list-table th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
      const col = th.dataset.sort;
      if (ListView._sortCol === col) {
        ListView._sortDir = ListView._sortDir === 'asc' ? 'desc' : 'asc';
      } else {
        ListView._sortCol = col;
        ListView._sortDir = 'desc';
      }
      ListView.render();
    });
  });

  // Select all checkbox
  const selectAll = document.getElementById('selectAllCheck');
  if (selectAll) {
    selectAll.addEventListener('change', () => {
      const rows = document.querySelectorAll('#listBody tr');
      rows.forEach(row => {
        const id = row.dataset.id;
        if (!id) return;
        const cb = row.querySelector('input[type="checkbox"]');
        if (selectAll.checked) {
          ListView._selected.add(id);
          if (cb) cb.checked = true;
          row.classList.add('selected');
        } else {
          ListView._selected.delete(id);
          if (cb) cb.checked = false;
          row.classList.remove('selected');
        }
      });
      ListView._updateBulkActions();
    });
  }
});
