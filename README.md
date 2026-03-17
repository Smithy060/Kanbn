# Kanbn

A lightweight Kanban task management board with multiple views, built with Flask and vanilla JavaScript.

![Board View](https://img.shields.io/badge/views-board%20%7C%20list%20%7C%20calendar%20%7C%20analytics-0D7377)

## Features

- **Board view** — drag-and-drop Kanban columns with customisable colours
- **List view** — sortable table with bulk select and priority badges
- **Calendar view** — month grid showing tasks by due date
- **Analytics view** — task distribution, velocity, and cycle time charts (Chart.js)
- **Task detail modal** — inline editing, subtasks with progress, comments, activity log
- **Full-text search** — SQLite FTS5 powered instant search
- **Labels** — colour-coded labels with sidebar filtering
- **Keyboard shortcuts** — `N` new task, `/` search, `B` `L` `C` switch views, `?` help
- **Quick-add modal** — fast task creation with column and priority selection
- **Dark theme** — teal and coral accent palette

## Tech Stack

- **Backend:** Python / Flask, SQLite with FTS5
- **Frontend:** Vanilla HTML, CSS, JavaScript (no build step, no frameworks)
- **Charts:** Chart.js 4 via CDN

## Getting Started

### Prerequisites

- Python 3.9+
- Flask (`pip install flask`)

### Run

```bash
cd todo-dashboard
pip install flask
python app.py
```

Open `http://localhost:5051` in your browser.

The port can be changed with the `KANBN_PORT` environment variable:

```bash
KANBN_PORT=8080 python app.py
```

### First Run

On first launch, Kanbn creates a SQLite database (`kanbn.db`) with a default project and four columns: Backlog, In Progress, Review, and Done. If a `tasks.json` file exists from a previous version, tasks are automatically migrated.

## Project Structure

```
todo-dashboard/
  app.py              # Flask entry point, blueprint registration
  db.py               # SQLite schema, migrations, FTS5 triggers
  models/             # Data access layer (task, column, label, etc.)
  routes/             # API blueprints (tasks, columns, labels, etc.)
  static/
    index.html        # SPA shell
    css/              # 8 CSS modules (base, layout, board, modal, etc.)
    js/               # 9 JS modules (api, app, board, list, calendar, etc.)
```

## API

All endpoints are under `/api/`. Key routes:

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/projects` | List projects |
| GET | `/api/projects/:id/board` | Board with columns and tasks |
| GET/POST | `/api/tasks` | List or create tasks |
| PUT | `/api/tasks/:id` | Update a task |
| PUT | `/api/tasks/:id/move` | Move task to column/position |
| GET/POST | `/api/tasks/:id/comments` | Task comments |
| GET/POST | `/api/tasks/:id/subtasks` | Task subtasks |
| GET | `/api/tasks/:id/activity` | Activity log |
| GET/POST | `/api/labels` | Project labels |
| GET | `/api/analytics/summary` | Task distribution stats |
| GET | `/api/analytics/velocity` | Completion velocity (8 weeks) |
| GET | `/api/analytics/cycle-time` | Average days per column |

## User Profile

Your display name is stored in the browser's localStorage. Click your name in the bottom-left of the sidebar to change it. The name is used for comment attribution and activity logging.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `N` | New task |
| `/` | Focus search |
| `B` | Board view |
| `L` | List view |
| `C` | Calendar view |
| `[` | Toggle sidebar |
| `?` | Show shortcuts |
| `Esc` | Close modal / clear search |

## License

MIT
