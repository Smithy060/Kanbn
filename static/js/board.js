/* ── Kanbn board.js — board view rendering + drag-and-drop ── */

const Board = {
  _draggedId: null,
  _didDrag: false,

  render() {
    const board = document.getElementById('board');
    if (!board) return;

    const columns = this._getFilteredColumns();

    board.innerHTML = columns.map(col => this._columnHTML(col)).join('') + `
      <button class="add-column-btn" onclick="Board.showAddColumn(this)">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        Add column
      </button>
    `;

    // Update topbar task count
    const total = (state.columns || []).reduce((n, c) => n + (c.tasks || []).length, 0);
    const countEl = document.getElementById('topbarCount');
    if (countEl) countEl.textContent = total + ' tasks';
  },

  _getFilteredColumns() {
    if (!state.columns) return [];

    return state.columns.map(col => {
      let tasks = col.tasks || [];

      // Apply filters
      if (state.filters.priority) {
        tasks = tasks.filter(t => t.priority === state.filters.priority);
      }
      if (state.filters.assignee) {
        tasks = tasks.filter(t => t.assignee && t.assignee.toLowerCase().includes(state.filters.assignee.toLowerCase()));
      }
      if (state.filters.label) {
        tasks = tasks.filter(t => {
          const labels = t.labels || [];
          return labels.some(l => l.name === state.filters.label);
        });
      }

      return { ...col, tasks };
    });
  },

  _columnHTML(col) {
    const tasks = col.tasks || [];
    const count = tasks.length;
    const wipLimit = col.wip_limit;
    let wipClass = '';
    let countClass = '';
    if (wipLimit) {
      if (count >= wipLimit) {
        wipClass = ' wip-over';
        countClass = ' wip-over';
      } else if (count >= wipLimit - 1) {
        wipClass = ' wip-warn';
        countClass = ' wip-warn';
      }
    }
    const countText = wipLimit ? `${count}/${wipLimit}` : count;
    const isDone = col.name.toLowerCase() === 'done';

    return `
      <div class="column${wipClass}" data-column-id="${col.id}" ${isDone ? 'data-done="true"' : ''}>
        <div class="column-header">
          <div class="column-dot${col.color === '#0D7377' ? ' pulsing' : ''}" style="background:${esc(col.color || '#7A9090')}"></div>
          <span class="column-title">${esc(col.name)}</span>
          <span class="column-count${countClass}">${countText}</span>
          <button class="column-overflow-btn" onclick="event.stopPropagation(); Board.showColumnMenu(this, '${col.id}')">&#8943;</button>
        </div>
        <div class="column-body"
             data-column-id="${col.id}"
             ondragover="Board.onDragOver(event)"
             ondragenter="Board.onDragEnter(event)"
             ondragleave="Board.onDragLeave(event)"
             ondrop="Board.onDrop(event, '${col.id}')">
          ${tasks.map(t => this._cardHTML(t)).join('')}
        </div>
        <div class="add-card-zone">
          <button class="add-card-btn" id="add-btn-${col.id}" onclick="Board.showAddCard('${col.id}')">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            Add card
          </button>
          <div class="add-card-form" id="add-form-${col.id}">
            <input type="text" placeholder="Task title" id="add-title-${col.id}" autocomplete="off"
                   onkeydown="if(event.key==='Enter')Board.submitAddCard('${col.id}');if(event.key==='Escape')Board.hideAddCard('${col.id}')" />
            <select id="add-priority-${col.id}">
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="low">Low</option>
            </select>
            <div class="add-card-actions">
              <button class="btn btn-primary btn-sm" onclick="Board.submitAddCard('${col.id}')">Add</button>
              <button class="btn btn-ghost btn-sm" onclick="Board.hideAddCard('${col.id}')">Cancel</button>
            </div>
          </div>
        </div>
      </div>`;
  },

  _cardHTML(t) {
    const shortId = t.id.slice(0, 6).toUpperCase();
    const pLabel = { high: 'HIGH', medium: 'MED', low: 'LOW' }[t.priority] || 'MED';
    const labels = t.labels || [];
    const subtasks = t.subtasks || [];
    const commentCount = (t.comments || []).length || t.comment_count || 0;
    const subtaskDone = subtasks.filter(s => s.completed).length;
    const subtaskTotal = subtasks.length;

    // Due date badge
    let dueBadge = '';
    if (t.due_date) {
      const due = new Date(t.due_date);
      const now = new Date();
      now.setHours(0, 0, 0, 0);
      const dueDay = new Date(due);
      dueDay.setHours(0, 0, 0, 0);
      const diff = (dueDay - now) / (1000 * 60 * 60 * 24);

      let dueClass = 'normal';
      if (diff < 0) dueClass = 'overdue';
      else if (diff < 1) dueClass = 'today';

      const dueStr = due.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
      dueBadge = `<span class="due-badge ${dueClass}">
        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <circle cx="12" cy="12" r="10"></circle>
          <polyline points="12 6 12 12 16 14"></polyline>
        </svg>
        ${dueStr}
      </span>`;
    }

    // Label chips (max 3)
    let labelsHTML = '';
    if (labels.length > 0) {
      const visible = labels.slice(0, 3);
      const overflow = labels.length - 3;
      labelsHTML = `<div class="card-labels">
        ${visible.map(l => `<span class="chip" style="background:${esc(l.color)}22;color:${esc(l.color)}"><span class="chip-dot" style="background:${esc(l.color)}"></span>${esc(l.name)}</span>`).join('')}
        ${overflow > 0 ? `<span class="card-label-overflow">+${overflow}</span>` : ''}
      </div>`;
    }

    // Assignee avatar
    let assigneeHTML = '';
    if (t.assignee) {
      const initials = t.assignee.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
      assigneeHTML = `<span class="card-assignee" title="${escAttr(t.assignee)}">${initials}</span>`;
    }

    return `
      <div class="card" data-id="${t.id}" data-priority="${t.priority || 'medium'}" draggable="true"
           ondragstart="Board.onDragStart(event, '${t.id}')"
           ondragend="Board.onDragEnd(event)"
           onclick="if(!Board._didDrag) App.openTask('${t.id}')">
        <div class="card-top">
          <span class="card-id">#${shortId}</span>
          <span class="badge badge-${t.priority || 'medium'}">${pLabel}</span>
        </div>
        <div class="card-title">${esc(t.title)}</div>
        ${labelsHTML}
        <div class="card-footer">
          <div class="card-meta">
            ${dueBadge}
            ${subtaskTotal > 0 ? `<span class="card-meta-item" title="Subtasks"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 11 12 14 22 4"></polyline><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path></svg> ${subtaskDone}/${subtaskTotal}</span>` : ''}
            ${commentCount > 0 ? `<span class="card-meta-item" title="Comments"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg> ${commentCount}</span>` : ''}
          </div>
          ${assigneeHTML}
        </div>
      </div>`;
  },

  // ── Add card ──
  showAddCard(colId) {
    document.getElementById(`add-btn-${colId}`).style.display = 'none';
    const form = document.getElementById(`add-form-${colId}`);
    form.classList.add('active');
    document.getElementById(`add-title-${colId}`).focus();
  },

  hideAddCard(colId) {
    document.getElementById(`add-btn-${colId}`).style.display = '';
    document.getElementById(`add-form-${colId}`).classList.remove('active');
    document.getElementById(`add-title-${colId}`).value = '';
  },

  async submitAddCard(colId) {
    const titleEl = document.getElementById(`add-title-${colId}`);
    const priorityEl = document.getElementById(`add-priority-${colId}`);
    const title = titleEl.value.trim();
    if (!title) { titleEl.focus(); return; }

    try {
      await API.createTask({
        title,
        priority: priorityEl.value,
        column_id: colId,
        project_id: state.currentProject.id,
      });
      this.hideAddCard(colId);
      await App.loadBoard();
      toast('Card added', 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },

  // ── Add column ──
  showAddColumn(btn) {
    const name = prompt('Column name:');
    if (!name || !name.trim()) return;
    this._createColumn(name.trim());
  },

  async _createColumn(name) {
    try {
      await API.createColumn(state.currentProject.id, { name });
      await App.loadBoard();
      toast('Column added', 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },

  // ── Column overflow menu ──
  showColumnMenu(btn, colId) {
    // Remove any existing menu
    document.querySelectorAll('.column-context-menu').forEach(m => m.remove());

    const col = state.columns.find(c => c.id === colId);
    if (!col) return;

    const menu = document.createElement('div');
    menu.className = 'dropdown-menu open column-context-menu';
    menu.style.position = 'absolute';
    menu.style.zIndex = '400';
    menu.innerHTML = `
      <div class="dropdown-item" onclick="Board.renameColumn('${colId}')">Rename</div>
      <div class="dropdown-item" onclick="Board.setWipLimit('${colId}')">Set WIP limit</div>
      <div class="dropdown-divider"></div>
      <div class="dropdown-item" style="color:var(--red)" onclick="Board.deleteColumn('${colId}')">Delete column</div>
    `;

    btn.parentElement.style.position = 'relative';
    btn.parentElement.appendChild(menu);
    menu.style.top = '100%';
    menu.style.right = '0';

    // Close on click outside
    const close = (e) => {
      if (!menu.contains(e.target)) {
        menu.remove();
        document.removeEventListener('click', close);
      }
    };
    setTimeout(() => document.addEventListener('click', close), 0);
  },

  async renameColumn(colId) {
    document.querySelectorAll('.column-context-menu').forEach(m => m.remove());
    const col = state.columns.find(c => c.id === colId);
    const name = prompt('New column name:', col ? col.name : '');
    if (!name || !name.trim()) return;
    try {
      await API.updateColumn(colId, { name: name.trim() });
      await App.loadBoard();
      toast('Column renamed', 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },

  async setWipLimit(colId) {
    document.querySelectorAll('.column-context-menu').forEach(m => m.remove());
    const col = state.columns.find(c => c.id === colId);
    const limit = prompt('WIP limit (leave empty to remove):', col ? (col.wip_limit || '') : '');
    if (limit === null) return;
    const val = limit.trim() === '' ? null : parseInt(limit);
    if (val !== null && isNaN(val)) { toast('Invalid number', 'error'); return; }
    try {
      await API.updateColumn(colId, { wip_limit: val });
      await App.loadBoard();
      toast('WIP limit updated', 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },

  async deleteColumn(colId) {
    document.querySelectorAll('.column-context-menu').forEach(m => m.remove());
    if (!confirm('Delete this column? Tasks must be moved first.')) return;
    try {
      await API.deleteColumn(colId);
      await App.loadBoard();
      toast('Column deleted', 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },

  // ── Drag & drop ──
  onDragStart(e, id) {
    this._draggedId = id;
    this._didDrag = true;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', id);

    // Disable pointer events on other cards to prevent drop interception
    document.querySelectorAll('.card').forEach(c => {
      if (c.dataset.id !== id) c.style.pointerEvents = 'none';
    });
  },

  onDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.column-body').forEach(b => b.classList.remove('drag-over'));
    document.querySelectorAll('.card').forEach(c => c.style.pointerEvents = '');
    this._draggedId = null;
    setTimeout(() => { this._didDrag = false; }, 50);
  },

  onDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  },

  onDragEnter(e) {
    e.preventDefault();
    const body = e.currentTarget;
    body.classList.add('drag-over');
  },

  onDragLeave(e) {
    const body = e.currentTarget;
    if (!body.contains(e.relatedTarget)) {
      body.classList.remove('drag-over');
    }
  },

  async onDrop(e, colId) {
    e.preventDefault();
    const body = e.currentTarget;
    body.classList.remove('drag-over');

    const id = e.dataTransfer.getData('text/plain') || this._draggedId;
    if (!id) return;

    // Determine position within column
    const cards = Array.from(body.querySelectorAll('.card'));
    let position = cards.length;

    // Find the card being dropped on
    const rect = body.getBoundingClientRect();
    const y = e.clientY - rect.top;
    for (let i = 0; i < cards.length; i++) {
      const cardRect = cards[i].getBoundingClientRect();
      const cardMiddle = cardRect.top + cardRect.height / 2 - rect.top;
      if (y < cardMiddle) {
        position = i;
        break;
      }
    }

    try {
      await API.moveTask(id, colId, position);
      await App.loadBoard();

      // Find column name for toast
      const col = state.columns.find(c => c.id === colId);
      toast(`Moved to ${col ? col.name : 'column'}`, 'success');
    } catch (e) {
      toast('Error: ' + e.message, 'error');
    }
  },
};
