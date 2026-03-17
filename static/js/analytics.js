/* ── Kanbn analytics.js — analytics view with Chart.js ── */

const AnalyticsView = {
  _charts: {},

  async render() {
    if (!state.currentProject) return;
    const pid = state.currentProject.id;

    try {
      const [summary, velocity, cycleTime] = await Promise.all([
        API.getSummary(pid),
        API.getVelocity(pid),
        API.getCycleTime(pid),
      ]);

      this._renderStats(summary);
      this._renderDistribution(summary);
      this._renderVelocity(velocity);
      this._renderCycleTime(cycleTime);
    } catch (e) {
      console.error('Analytics failed:', e);
      toast('Failed to load analytics', 'error');
    }
  },

  _renderStats(summary) {
    const row = document.getElementById('statsRow');
    if (!row) return;

    const done = summary.done || 0;
    const total = summary.total || 0;
    const rate = total > 0 ? Math.round(done / total * 100) : 0;

    row.innerHTML = [
      { value: total, label: 'Total Tasks' },
      { value: done, label: 'Completed' },
      { value: summary.overdue || 0, label: 'Overdue' },
      { value: rate + '%', label: 'Completion' },
    ].map(s =>
      '<div class="stat-card">' +
        '<div class="stat-value">' + s.value + '</div>' +
        '<div class="stat-label">' + s.label + '</div>' +
      '</div>'
    ).join('');
  },

  _renderDistribution(summary) {
    const canvas = document.getElementById('chartDistribution');
    if (!canvas || typeof Chart === 'undefined') return;

    if (this._charts.distribution) this._charts.distribution.destroy();

    const columns = summary.by_column || [];

    this._charts.distribution = new Chart(canvas, {
      type: 'doughnut',
      data: {
        labels: columns.map(c => c.name),
        datasets: [{
          data: columns.map(c => c.task_count || c.count || 0),
          backgroundColor: columns.map(c => c.color || '#7A9090'),
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              color: '#7A9090',
              font: { family: 'DM Sans', size: 12 },
              padding: 12,
              usePointStyle: true,
              pointStyleWidth: 8,
            },
          },
        },
      },
    });
  },

  _renderVelocity(velocity) {
    const canvas = document.getElementById('chartVelocity');
    if (!canvas || typeof Chart === 'undefined') return;

    if (this._charts.velocity) this._charts.velocity.destroy();

    const labels = velocity.map(w => {
      const d = new Date(w.week_start);
      return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    });

    this._charts.velocity = new Chart(canvas, {
      type: 'bar',
      data: {
        labels,
        datasets: [{
          label: 'Tasks completed',
          data: velocity.map(w => w.completed || w.total || 0),
          backgroundColor: 'rgba(13, 115, 119, 0.6)',
          borderColor: '#0D7377',
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              color: '#5a7070',
              font: { family: 'JetBrains Mono', size: 11 },
              stepSize: 1,
            },
            grid: { color: 'rgba(46, 56, 56, 0.5)' },
          },
          x: {
            ticks: { color: '#5a7070', font: { family: 'DM Sans', size: 11 } },
            grid: { display: false },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  },

  _renderCycleTime(cycleTime) {
    const canvas = document.getElementById('chartCycleTime');
    if (!canvas || typeof Chart === 'undefined') return;

    if (this._charts.cycleTime) this._charts.cycleTime.destroy();

    this._charts.cycleTime = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: cycleTime.map(c => c.column_name),
        datasets: [{
          label: 'Avg days',
          data: cycleTime.map(c => c.avg_days || 0),
          backgroundColor: cycleTime.map(c => {
            const col = (state.columns || []).find(sc => sc.id === c.column_id);
            return col ? col.color + 'AA' : 'rgba(122, 144, 144, 0.6)';
          }),
          borderWidth: 0,
          borderRadius: 4,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        indexAxis: 'y',
        scales: {
          x: {
            beginAtZero: true,
            ticks: { color: '#5a7070', font: { family: 'JetBrains Mono', size: 11 } },
            grid: { color: 'rgba(46, 56, 56, 0.5)' },
          },
          y: {
            ticks: { color: '#7A9090', font: { family: 'DM Sans', size: 12 } },
            grid: { display: false },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  },
};
