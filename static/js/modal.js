/* ── Kanbn modal.js — task detail modal ── */

const Modal = {
  _task: null,
  _activityOpen: false,

  async open(taskId) {
    try {
      const task = await API.getTask(taskId);
      if (!task) { toast('Task not found', 'error'); return; }
      this._task = task;
      this._render();
      document.getElementById('taskModal').classList.add('active');
    } catch (e) {
      toast('Error loading task: ' + e.message, 'error');
    }
  },

  close() {
    document.getElementById('taskModal').classList.remove('active');
    this._task = null;
  },

  _render() {
    const t = this._task;
    if (!t) return;

    // Top bar
    document.getElementById('modalTaskId').textContent = '#' + t.id.slice(0, 6).toUpperCase();
    const col = (state.columns || []).find(c => c.id === t.column_id);
    document.getElementById('modalBreadcrumb').textContent = col ? col.name : '';

    this._renderTitle();
    this._renderDescription();
    this._renderSubtasks();
    this._renderComments();
    this._renderActivity();
    this._renderMeta();
    this._bindEvents();
  },

  _renderTitle() {
    const t = this._task;
    const display = document.getElementById('modalTitleDisplay');
    const input = document.getElementById('modalTitleInput');
    display.textContent = t.title;
    display.style.display = '';
    input.style.display = 'none';
    input.value = t.title;
  },

  _renderDescription() {
    const t = this._task;
    const display = document.getElementById('descDisplay');
    const input = document.getElementById('descInput');
    if (t.description) {
      display.textContent = t.description;
      display.classList.remove('empty');
    } else {
      display.textContent = 'Add a description\u2026';
      display.classList.add('empty');
    }
    display.style.display = '';
    input.style.display = 'none';
    input.value = t.description || '';
  },

  _renderSubtasks() {
    const t = this._task;
    const list = document.getElementById('subtasksList');
    const subtasks = t.subtasks || [];
    const done = subtasks.filter(s => s.completed).length;
    const total = subtasks.length;

    const progressText = document.getElementById('subtaskProgress');
    if (progressText) progressText.textContent = total > 0 ? done + '/' + total : '';
    const progressBar = document.getElementById('subtaskProgressBar');
    if (progressBar) progressBar.style.width = total > 0 ? Math.round(done / total * 100) + '%' : '0%';

    list.innerHTML = subtasks.map(s => `
      <div class="subtask-item${s.completed ? ' done' : ''}" data-id="${s.id}">
        <input type="checkbox" class="subtask-check" ${s.completed ? 'checked' : ''}
               onchange="Modal._toggleSubtask('${s.id}', this.checked)">
        <span class="subtask-title">${esc(s.title)}</span>
        <button class="subtask-delete" onclick="Modal._deleteSubtask('${s.id}')">&times;</button>
      </div>
    `).join('');
  },

  _renderComments() {
    const t = this._task;
    const list = document.getElementById('commentsList');
    const comments = t.comments || [];

    list.innerHTML = comments.map(c => `
      <div class="comment" data-id="${c.id}">
        <div class="comment-avatar">${(c.author || 'User')[0].toUpperCase()}</div>
        <div class="comment-body">
          <div class="comment-header">
            <span class="comment-author">${esc(c.author || 'User')}</span>
            <span class="comment-time">${timeAgo(c.created_at)}</span>
            <button class="comment-delete" onclick="Modal._deleteComment('${c.id}')">&times;</button>
          </div>
          <div class="comment-text">${esc(c.text)}</div>
        </div>
      </div>
    `).join('');
  },

  async _renderActivity() {
    const t = this._task;
    const items = document.getElementById('activityItems');
    const toggle = document.getElementById('activityToggle');

    if (this._activityOpen) {
      toggle.classList.add('open');
      items.classList.add('open');
    } else {
      toggle.classList.remove('open');
      items.classList.remove('open');
    }

    try {
      const activity = await API.getActivity(t.id);
      items.innerHTML = activity.map(a => {
        const text = this._activityText(a);
        return `<div class="activity-item">
          <div class="activity-dot"></div>
          <span class="activity-text">${text}</span>
          <span class="activity-time">${timeAgo(a.created_at)}</span>
        </div>`;
      }).join('') || '<div class="activity-item"><span class="activity-text">No activity yet</span></div>';
    } catch (e) {
      items.innerHTML = '<div class="activity-item"><span class="activity-text">Failed to load</span></div>';
    }
  },

  _activityText(a) {
    const d = a.detail || {};
    switch (a.action) {
      case 'created': return '<strong>' + esc(a.actor) + '</strong> created this task';
      case 'moved': return '<strong>' + esc(a.actor) + '</strong> moved from <em>' + esc(d.from_column_name) + '</em> to <em>' + esc(d.to_column_name) + '</em>';
      case 'priority_changed': return '<strong>' + esc(a.actor) + '</strong> changed priority from <em>' + esc(d.from) + '</em> to <em>' + esc(d.to) + '</em>';
      case 'assignee_changed': return '<strong>' + esc(a.actor) + '</strong> changed assignee from <em>' + esc(d.from || 'none') + '</em> to <em>' + esc(d.to || 'none') + '</em>';
      case 'label_added': return '<strong>' + esc(a.actor) + '</strong> added label <em>' + esc(d.label_name) + '</em>';
      case 'label_removed': return '<strong>' + esc(a.actor) + '</strong> removed label <em>' + esc(d.label_name) + '</em>';
      case 'subtask_toggled': return '<strong>' + esc(a.actor) + '</strong> ' + (d.completed ? 'completed' : 'unchecked') + ' a subtask';
      default: return '<strong>' + esc(a.actor) + '</strong> ' + esc(a.action);
    }
  },

  _renderMeta() {
    const t = this._task;

    // Status (column) select
    const statusSel = document.getElementById('metaStatus');
    statusSel.innerHTML = (state.columns || []).map(c =>
      '<option value="' + c.id + '"' + (c.id === t.column_id ? ' selected' : '') + '>' + esc(c.name) + '</option>'
    ).join('');

    document.getElementById('metaPriority').value = t.priority || 'medium';
    document.getElementById('metaAssignee').value = t.assignee || '';
    document.getElementById('metaDueDate').value = t.due_date || '';

    this._renderModalLabels();

    document.getElementById('metaCreated').textContent = t.created_at ? new Date(t.created_at).toLocaleString('en-GB') : '\u2014';
    document.getElementById('metaUpdated').textContent = t.updated_at ? new Date(t.updated_at).toLocaleString('en-GB') : '\u2014';
  },

  _renderModalLabels() {
    const t = this._task;
    const container = document.getElementById('modalLabelsList');
    const taskLabels = t.labels || [];

    container.innerHTML = taskLabels.map(l =>
      '<span class="chip" style="background:' + esc(l.color) + '22;color:' + esc(l.color) + '">' +
        '<span class="chip-dot" style="background:' + esc(l.color) + '"></span>' +
        esc(l.name) +
        '<button class="chip-remove" onclick="Modal._detachLabel(\'' + l.id + '\')">&times;</button>' +
      '</span>'
    ).join('');

    const menu = document.getElementById('addLabelMenu');
    const available = (state.labels || []).filter(l => !taskLabels.some(tl => tl.id === l.id));
    menu.innerHTML = available.map(l =>
      '<div class="dropdown-item" onclick="Modal._attachLabel(\'' + l.id + '\')">' +
        '<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:' + esc(l.color) + ';flex-shrink:0;margin-right:6px;"></span>' +
        esc(l.name) +
      '</div>'
    ).join('') || '<div class="dropdown-item" style="color:var(--text-dim)">No labels available</div>';
  },

  _bindEvents() {
    const overlay = document.getElementById('taskModal');
    const closeBtn = document.getElementById('modalClose');
    const titleDisplay = document.getElementById('modalTitleDisplay');
    const titleInput = document.getElementById('modalTitleInput');
    const descDisplay = document.getElementById('descDisplay');
    const descInput = document.getElementById('descInput');
    const statusSel = document.getElementById('metaStatus');
    const prioritySel = document.getElementById('metaPriority');
    const assigneeInput = document.getElementById('metaAssignee');
    const dueDateInput = document.getElementById('metaDueDate');
    const deleteBtn = document.getElementById('deleteTaskBtn');
    const addSubtaskInput = document.getElementById('addSubtaskInput');
    const addSubtaskBtn = document.getElementById('addSubtaskBtn');
    const commentInput = document.getElementById('commentInput');
    const postCommentBtn = document.getElementById('postCommentBtn');
    const activityToggle = document.getElementById('activityToggle');
    const addLabelBtn = document.getElementById('addLabelToTaskBtn');

    // Clone to remove old listeners
    function clone(el) { const n = el.cloneNode(true); el.parentNode.replaceChild(n, el); return n; }

    const newClose = clone(closeBtn);
    newClose.addEventListener('click', () => this.close());
    overlay.onclick = (e) => { if (e.target === overlay) this.close(); };

    // Title inline edit
    const newTitleDisplay = clone(titleDisplay);
    const newTitleInput = clone(titleInput);
    newTitleDisplay.addEventListener('click', () => {
      newTitleDisplay.style.display = 'none';
      newTitleInput.style.display = '';
      newTitleInput.value = this._task.title;
      newTitleInput.focus();
    });
    newTitleInput.addEventListener('blur', () => this._saveTitle(newTitleInput.value));
    newTitleInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') { e.preventDefault(); newTitleInput.blur(); }
      if (e.key === 'Escape') { newTitleInput.value = this._task.title; newTitleInput.blur(); }
    });

    // Description inline edit
    const newDescDisplay = clone(descDisplay);
    const newDescInput = clone(descInput);
    newDescDisplay.addEventListener('click', () => {
      newDescDisplay.style.display = 'none';
      newDescInput.style.display = '';
      newDescInput.value = this._task.description || '';
      newDescInput.focus();
    });
    newDescInput.addEventListener('blur', () => this._saveDescription(newDescInput.value));
    newDescInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { newDescInput.value = this._task.description || ''; newDescInput.blur(); }
    });

    // Meta fields
    const newStatus = clone(statusSel);
    newStatus.addEventListener('change', () => this._moveTask(newStatus.value));

    const newPriority = clone(prioritySel);
    newPriority.addEventListener('change', () => this._saveMeta({ priority: newPriority.value }));

    const newAssignee = clone(assigneeInput);
    let assigneeTimer;
    newAssignee.addEventListener('input', () => {
      clearTimeout(assigneeTimer);
      assigneeTimer = setTimeout(() => this._saveMeta({ assignee: newAssignee.value }), 600);
    });

    const newDueDate = clone(dueDateInput);
    newDueDate.addEventListener('change', () => this._saveMeta({ due_date: newDueDate.value || null }));

    const newDelete = clone(deleteBtn);
    newDelete.addEventListener('click', () => this._deleteTask());

    // Subtasks
    const newSubInput = clone(addSubtaskInput);
    const newSubBtn = clone(addSubtaskBtn);
    newSubInput.addEventListener('keydown', (e) => { if (e.key === 'Enter') this._addSubtask(newSubInput); });
    newSubBtn.addEventListener('click', () => this._addSubtask(newSubInput));

    // Comments
    const newCommentInput = clone(commentInput);
    const newPostBtn = clone(postCommentBtn);
    newCommentInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) this._addComment(newCommentInput);
    });
    newPostBtn.addEventListener('click', () => this._addComment(newCommentInput));

    // Activity toggle
    const newToggle = clone(activityToggle);
    newToggle.addEventListener('click', () => {
      this._activityOpen = !this._activityOpen;
      newToggle.classList.toggle('open', this._activityOpen);
      document.getElementById('activityItems').classList.toggle('open', this._activityOpen);
    });

    // Add label dropdown
    const newLabelBtn = clone(addLabelBtn);
    newLabelBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      document.getElementById('addLabelMenu').classList.toggle('open');
    });
  },

  /* ── Actions ── */

  async _saveTitle(value) {
    const title = (value || '').trim();
    if (!title || title === this._task.title) { this._renderTitle(); return; }
    try {
      await API.updateTask(this._task.id, { title });
      this._task.title = title;
      this._renderTitle();
      App.loadBoard();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _saveDescription(value) {
    const desc = (value || '').trim();
    if (desc === (this._task.description || '')) { this._renderDescription(); return; }
    try {
      await API.updateTask(this._task.id, { description: desc });
      this._task.description = desc;
      this._renderDescription();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _saveMeta(data) {
    try {
      const updated = await API.updateTask(this._task.id, data);
      Object.assign(this._task, updated);
      App.loadBoard();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _moveTask(columnId) {
    try {
      await API.moveTask(this._task.id, columnId, 0);
      this._task.column_id = columnId;
      const col = (state.columns || []).find(c => c.id === columnId);
      document.getElementById('modalBreadcrumb').textContent = col ? col.name : '';
      App.loadBoard();
      toast('Moved to ' + (col ? col.name : 'column'), 'success');
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _deleteTask() {
    if (!confirm('Delete this task permanently?')) return;
    try {
      await API.deleteTask(this._task.id);
      this.close();
      await App.loadBoard();
      toast('Task deleted', 'success');
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _addSubtask(input) {
    const title = (input.value || '').trim();
    if (!title) return;
    try {
      const sub = await API.createSubtask(this._task.id, title);
      this._task.subtasks = this._task.subtasks || [];
      this._task.subtasks.push(sub);
      input.value = '';
      this._renderSubtasks();
      App.loadBoard();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _toggleSubtask(subtaskId, completed) {
    try {
      await API.updateSubtask(subtaskId, { completed });
      const sub = (this._task.subtasks || []).find(s => s.id === subtaskId);
      if (sub) sub.completed = completed ? 1 : 0;
      this._renderSubtasks();
      App.loadBoard();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _deleteSubtask(subtaskId) {
    try {
      await API.deleteSubtask(subtaskId);
      this._task.subtasks = (this._task.subtasks || []).filter(s => s.id !== subtaskId);
      this._renderSubtasks();
      App.loadBoard();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _addComment(input) {
    const text = (input.value || '').trim();
    if (!text) return;
    try {
      const comment = await API.createComment(this._task.id, text, state.userName);
      this._task.comments = this._task.comments || [];
      this._task.comments.push(comment);
      input.value = '';
      this._renderComments();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _deleteComment(commentId) {
    try {
      await API.deleteComment(commentId);
      this._task.comments = (this._task.comments || []).filter(c => c.id !== commentId);
      this._renderComments();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _attachLabel(labelId) {
    try {
      await API.attachLabel(this._task.id, labelId);
      const task = await API.getTask(this._task.id);
      this._task = task;
      this._renderModalLabels();
      App.loadBoard();
      App.loadLabels();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },

  async _detachLabel(labelId) {
    try {
      await API.detachLabel(this._task.id, labelId);
      this._task.labels = (this._task.labels || []).filter(l => l.id !== labelId);
      this._renderModalLabels();
      App.loadBoard();
    } catch (e) { toast('Error: ' + e.message, 'error'); }
  },
};

// Close label dropdown on outside click
document.addEventListener('click', () => {
  const m = document.getElementById('addLabelMenu');
  if (m) m.classList.remove('open');
});
