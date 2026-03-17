/* ── Kanbn sidebar.js — sidebar compatibility shim ──
   All sidebar functionality (search, labels, collapse) is now handled by app.js
   working directly with the index.html DOM. This file provides backward-compatible
   methods in case other modules reference the Sidebar object. */

const Sidebar = {
  renderLabels() {
    App._initSidebarLabels();
  },

  hideSearchResults() {
    const sr = document.getElementById('searchResults');
    if (sr) sr.classList.remove('active');
  },
};
