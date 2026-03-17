/* ── Kanbn api.js — API client wrapper ── */

const API = {
  _base: '/api',

  async _fetch(method, path, body) {
    const opts = {
      method,
      headers: { 'Content-Type': 'application/json' },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    const res = await fetch(this._base + path, opts);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    if (res.status === 204) return null;
    return res.json();
  },

  // ── Projects ──
  getProjects() {
    return this._fetch('GET', '/projects');
  },

  getProject(projectId) {
    return this._fetch('GET', `/projects/${projectId}`);
  },

  getBoard(projectId) {
    return this._fetch('GET', `/projects/${projectId}/board`);
  },

  // ── Tasks ──
  getTasks(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([k, v]) => {
      if (v != null && v !== '') params.set(k, v);
    });
    const qs = params.toString();
    return this._fetch('GET', '/tasks' + (qs ? '?' + qs : ''));
  },

  getTask(taskId) {
    return this._fetch('GET', `/tasks/${taskId}`);
  },

  createTask(data) {
    return this._fetch('POST', '/tasks', data);
  },

  updateTask(taskId, data) {
    return this._fetch('PUT', `/tasks/${taskId}`, data);
  },

  deleteTask(taskId) {
    return this._fetch('DELETE', `/tasks/${taskId}`);
  },

  moveTask(taskId, columnId, position) {
    return this._fetch('PUT', `/tasks/${taskId}/move`, {
      column_id: columnId,
      position: position,
    });
  },

  // ── Labels ──
  getLabels(projectId) {
    const qs = projectId ? `?project_id=${projectId}` : '';
    return this._fetch('GET', '/labels' + qs);
  },

  createLabel(data) {
    return this._fetch('POST', '/labels', data);
  },

  updateLabel(labelId, data) {
    return this._fetch('PUT', `/labels/${labelId}`, data);
  },

  deleteLabel(labelId) {
    return this._fetch('DELETE', `/labels/${labelId}`);
  },

  attachLabel(taskId, labelId) {
    return this._fetch('POST', `/tasks/${taskId}/labels/${labelId}`);
  },

  detachLabel(taskId, labelId) {
    return this._fetch('DELETE', `/tasks/${taskId}/labels/${labelId}`);
  },

  // ── Subtasks ──
  getSubtasks(taskId) {
    return this._fetch('GET', `/tasks/${taskId}/subtasks`);
  },

  createSubtask(taskId, title) {
    return this._fetch('POST', `/tasks/${taskId}/subtasks`, { title });
  },

  updateSubtask(subtaskId, data) {
    return this._fetch('PUT', `/subtasks/${subtaskId}`, data);
  },

  deleteSubtask(subtaskId) {
    return this._fetch('DELETE', `/subtasks/${subtaskId}`);
  },

  // ── Comments ──
  getComments(taskId) {
    return this._fetch('GET', `/tasks/${taskId}/comments`);
  },

  createComment(taskId, text, author) {
    const body = { text };
    if (author) body.author = author;
    return this._fetch('POST', `/tasks/${taskId}/comments`, body);
  },

  updateComment(commentId, text) {
    return this._fetch('PUT', `/comments/${commentId}`, { text });
  },

  deleteComment(commentId) {
    return this._fetch('DELETE', `/comments/${commentId}`);
  },

  // ── Activity ──
  getActivity(taskId) {
    return this._fetch('GET', `/tasks/${taskId}/activity`);
  },

  // ── Columns ──
  getColumns(projectId) {
    return this._fetch('GET', `/projects/${projectId}/columns`);
  },

  createColumn(projectId, data) {
    return this._fetch('POST', `/projects/${projectId}/columns`, data);
  },

  updateColumn(columnId, data) {
    return this._fetch('PUT', `/columns/${columnId}`, data);
  },

  deleteColumn(columnId) {
    return this._fetch('DELETE', `/columns/${columnId}`);
  },

  reorderColumns(projectId, order) {
    return this._fetch('PUT', `/projects/${projectId}/columns/reorder`, { order });
  },

  // ── Analytics ──
  getSummary(projectId) {
    const qs = projectId ? `?project_id=${projectId}` : '';
    return this._fetch('GET', '/analytics/summary' + qs);
  },

  getVelocity(projectId) {
    const qs = projectId ? `?project_id=${projectId}` : '';
    return this._fetch('GET', '/analytics/velocity' + qs);
  },

  getCycleTime(projectId) {
    const qs = projectId ? `?project_id=${projectId}` : '';
    return this._fetch('GET', '/analytics/cycle-time' + qs);
  },
};
