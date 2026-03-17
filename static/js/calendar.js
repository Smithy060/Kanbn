/* ── Kanbn calendar.js — calendar view ── */

const CalendarView = {
  _currentDate: new Date(),
  _tasks: [],

  async render() {
    const grid = document.getElementById('calendarGrid');
    const title = document.getElementById('calTitle');
    if (!grid || !title) return;

    // Load tasks with due dates
    try {
      const year = this._currentDate.getFullYear();
      const month = this._currentDate.getMonth();
      const firstDay = new Date(year, month, 1);
      const lastDay = new Date(year, month + 1, 0);

      // Load all tasks for this project (filter by due_date range)
      this._tasks = await API.getTasks({
        project_id: state.currentProject ? state.currentProject.id : undefined,
        due_after: firstDay.toISOString().slice(0, 10),
        due_before: new Date(year, month + 1, 7).toISOString().slice(0, 10),
      });
    } catch (e) {
      this._tasks = [];
    }

    const year = this._currentDate.getFullYear();
    const month = this._currentDate.getMonth();
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
                        'July', 'August', 'September', 'October', 'November', 'December'];
    title.textContent = monthNames[month] + ' ' + year;

    // Build calendar grid
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDow = firstDay.getDay() || 7; // Monday = 1
    const daysInMonth = lastDay.getDate();

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    // Day headers
    const dayHeaders = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
    let html = dayHeaders.map(d =>
      '<div class="calendar-day-header">' + d + '</div>'
    ).join('');

    // Pad start (previous month days)
    const prevMonth = new Date(year, month, 0);
    const padStart = startDow - 1;
    for (let i = padStart; i > 0; i--) {
      const day = prevMonth.getDate() - i + 1;
      html += '<div class="calendar-day other-month"><span class="calendar-day-num">' + day + '</span></div>';
    }

    // Current month days
    for (let d = 1; d <= daysInMonth; d++) {
      const date = new Date(year, month, d);
      date.setHours(0, 0, 0, 0);
      const dateStr = date.toISOString().slice(0, 10);
      const isToday = date.getTime() === today.getTime();
      const dayTasks = this._tasks.filter(t => t.due_date === dateStr);

      html += '<div class="calendar-day' + (isToday ? ' today' : '') + '" data-date="' + dateStr + '">';
      html += '<span class="calendar-day-num">' + d + '</span>';
      dayTasks.slice(0, 3).forEach(t => {
        html += '<div class="calendar-task-chip ' + (t.priority || 'medium') + '" onclick="event.stopPropagation(); App.openTask(\'' + t.id + '\')" title="' + escAttr(t.title) + '">';
        html += esc(t.title);
        html += '</div>';
      });
      if (dayTasks.length > 3) {
        html += '<div style="font-size:10px;color:var(--text-dim);padding:1px 6px;">+' + (dayTasks.length - 3) + ' more</div>';
      }
      html += '</div>';
    }

    // Pad end (next month days)
    const totalCells = padStart + daysInMonth;
    const remaining = totalCells % 7 === 0 ? 0 : 7 - (totalCells % 7);
    for (let i = 1; i <= remaining; i++) {
      html += '<div class="calendar-day other-month"><span class="calendar-day-num">' + i + '</span></div>';
    }

    grid.innerHTML = html;
  },

  prev() {
    this._currentDate.setMonth(this._currentDate.getMonth() - 1);
    this.render();
  },

  next() {
    this._currentDate.setMonth(this._currentDate.getMonth() + 1);
    this.render();
  },

  goToday() {
    this._currentDate = new Date();
    this.render();
  },
};

// Nav button handlers
document.addEventListener('DOMContentLoaded', () => {
  const prevBtn = document.getElementById('calPrev');
  const nextBtn = document.getElementById('calNext');
  const todayBtn = document.getElementById('calToday');
  if (prevBtn) prevBtn.addEventListener('click', () => CalendarView.prev());
  if (nextBtn) nextBtn.addEventListener('click', () => CalendarView.next());
  if (todayBtn) todayBtn.addEventListener('click', () => CalendarView.goToday());
});
