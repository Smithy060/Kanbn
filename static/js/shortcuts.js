/* ── Kanbn shortcuts.js — keyboard shortcuts ── */

const Shortcuts = {
  init() {
    document.addEventListener('keydown', (e) => this._handle(e));
  },

  _handle(e) {
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea' || tag === 'select') {
      if (e.key === 'Escape') e.target.blur();
      return;
    }

    const modalOpen = document.getElementById('taskModal').classList.contains('active');
    const quickAddOpen = document.getElementById('quickAddModal').classList.contains('active');
    const shortcutsOpen = document.getElementById('shortcutsOverlay').classList.contains('active');

    if (e.key === 'Escape') {
      if (shortcutsOpen) { document.getElementById('shortcutsOverlay').classList.remove('active'); return; }
      if (quickAddOpen) { QuickAdd.close(); return; }
      if (modalOpen) { Modal.close(); return; }
      const sr = document.getElementById('searchResults');
      if (sr) sr.classList.remove('active');
      return;
    }

    if (modalOpen || quickAddOpen || shortcutsOpen) return;

    switch (e.key) {
      case 'n':
      case 'N':
        e.preventDefault();
        QuickAdd.open();
        break;
      case '/':
        e.preventDefault();
        var si = document.getElementById('searchInput');
        if (si) si.focus();
        break;
      case 'b':
      case 'B':
        e.preventDefault();
        App.navigate('board');
        break;
      case 'l':
      case 'L':
        e.preventDefault();
        App.navigate('list');
        break;
      case 'c':
      case 'C':
        e.preventDefault();
        App.navigate('calendar');
        break;
      case '[':
        e.preventDefault();
        var sb = document.getElementById('sidebar');
        if (sb) {
          state.sidebarCollapsed = !state.sidebarCollapsed;
          localStorage.setItem('sidebar-collapsed', state.sidebarCollapsed);
          sb.classList.toggle('collapsed', state.sidebarCollapsed);
        }
        break;
      case '?':
        e.preventDefault();
        document.getElementById('shortcutsOverlay').classList.toggle('active');
        break;
    }
  },
};

document.addEventListener('DOMContentLoaded', () => Shortcuts.init());
