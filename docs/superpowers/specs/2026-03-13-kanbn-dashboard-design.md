# Kanbn — Task Dashboard Design Spec

## Overview

Evolve the existing Smithy todo dashboard into **Kanbn**, a feature-rich Jira-like task management system with a web dashboard, multiple views, and a native macOS menu bar widget.

**Primary use cases:** Personal productivity tool, team/client-visible project tracking, capability showcase.

**Tech stack:** Flask + SQLite (backend), vanilla HTML/CSS/JS (frontend), SwiftUI (macOS menu bar widget).

**Design philosophy:** Build on the existing codebase. SQLite schema designed for future PostgreSQL migration. No auth in v1 — single-user local app.

---

## 1. Branding

**Name:** Kanbn

**Logo:** Outlined monogram — teal `K` (DM Sans 800) inside a rounded square border (`border: 3px solid #0D7377`, `border-radius: 16px`). Used as sidebar logo, favicon, and menu bar icon.

**Wordmark:** "Kanbn" in DM Sans 700, 22px, `letter-spacing: -0.5px`, colour `#E8EEEE`.

**Colour palette** (carried from current design):
| Token | Hex | Usage |
|-------|-----|-------|
| `--teal` | `#0D7377` | Primary, logo, active states |
| `--teal-dim` | `#0a5c5f` | Hover states |
| `--coral` | `#E07A5F` | High priority, bugs |
| `--gold` | `#D4A843` | Medium priority, warnings |
| `--green` | `#2D8B6F` | Done, success |
| `--red` | `#C44536` | Error, delete |
| `--bg` | `#161A1A` | Page background |
| `--surface` | `#1E2424` | Cards, sidebar |
| `--surface-2` | `#272E2E` | Elevated surfaces |
| `--surface-3` | `#303939` | Hover surfaces |
| `--border` | `#2E3838` | Borders |
| `--text` | `#E8EEEE` | Primary text |
| `--text-muted` | `#7A9090` | Secondary text |
| `--text-dim` | `#5a7070` | Tertiary text |

**Typography:**
- Primary: DM Sans (loaded from Google Fonts)
- Monospace: JetBrains Mono (task IDs, column counts, code blocks)

---

## 2. Data Model (SQLite)

### 2.1 Tables

**`projects`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `name` | TEXT | Not null |
| `description` | TEXT | |
| `created_at` | TEXT (ISO8601) | |
| `updated_at` | TEXT (ISO8601) | |

V1 ships with a single default project. Multi-project support is structural but not exposed in the UI.

**SQLite connection setup:** `db.py` must execute `PRAGMA foreign_keys = ON` on every connection. All foreign key columns use `ON DELETE CASCADE` so that deleting a project cascades to its columns, tasks, labels; deleting a task cascades to its subtasks, comments, task_labels, and activity_log entries; deleting a column cascades to its tasks (but the API blocks this with a 409 — the CASCADE is a safety net).

**`columns`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `project_id` | TEXT | FK → projects.id |
| `name` | TEXT | Not null |
| `position` | INTEGER | Ordering within project |
| `color` | TEXT | Dot colour hex |
| `wip_limit` | INTEGER | Nullable; max cards in column |
| `created_at` | TEXT (ISO8601) | |
| `updated_at` | TEXT (ISO8601) | |

Default columns created with new project: Backlog, In Progress, Review, Done.

**`tasks`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `project_id` | TEXT | FK → projects.id |
| `column_id` | TEXT | FK → columns.id |
| `title` | TEXT | Not null, FTS5-indexed |
| `description` | TEXT | FTS5-indexed |
| `priority` | TEXT | high / medium / low |
| `assignee` | TEXT | Nullable, free-text name |
| `due_date` | TEXT | Nullable, ISO8601 date |
| `position` | INTEGER | Ordering within column |
| `created_at` | TEXT (ISO8601) | |
| `updated_at` | TEXT (ISO8601) | |

**`labels`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `project_id` | TEXT | FK → projects.id |
| `name` | TEXT | Not null |
| `color` | TEXT | Hex colour |

**`task_labels`**
| Column | Type | Notes |
|--------|------|-------|
| `task_id` | TEXT | FK → tasks.id |
| `label_id` | TEXT | FK → labels.id |
| | | Composite PK |

**`subtasks`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `task_id` | TEXT | FK → tasks.id |
| `title` | TEXT | Not null |
| `completed` | INTEGER | 0 or 1 |
| `position` | INTEGER | Ordering |
| `created_at` | TEXT (ISO8601) | |

**`comments`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `task_id` | TEXT | FK → tasks.id |
| `text` | TEXT | Not null |
| `author` | TEXT | Default "Lewis" |
| `created_at` | TEXT (ISO8601) | |

**`activity_log`**
| Column | Type | Notes |
|--------|------|-------|
| `id` | TEXT (UUID) | PK |
| `task_id` | TEXT | FK → tasks.id |
| `action` | TEXT | e.g. "moved", "priority_changed", "label_added" |
| `detail` | TEXT | JSON — see below |
| `actor` | TEXT | Default "Lewis" |
| `created_at` | TEXT (ISO8601) | |

**Activity log `detail` JSON formats by action:**
- `moved`: `{"from_column_id": "...", "to_column_id": "...", "from_column_name": "...", "to_column_name": "..."}`
- `priority_changed`: `{"from": "medium", "to": "high"}`
- `label_added` / `label_removed`: `{"label_id": "...", "label_name": "..."}`
- `created`: `{}`
- `assignee_changed`: `{"from": "...", "to": "..."}`
- `subtask_toggled`: `{"subtask_id": "...", "completed": true}`

Column IDs (not just names) are stored in move events so cycle time calculations survive column renames. Cycle time per column is calculated by finding consecutive "moved" events per task and computing the time delta between them.

### 2.2 Full-Text Search

SQLite FTS5 virtual table on `tasks.title` and `tasks.description`:
```sql
CREATE VIRTUAL TABLE tasks_fts USING fts5(title, description, content=tasks, content_rowid=rowid);
```
Note: `tasks` uses a TEXT UUID as its PK, but SQLite still maintains an implicit integer `rowid`. The FTS content sync and triggers must reference `tasks.rowid` (the implicit integer), not the UUID `id` column.

Required FTS sync triggers (created in `db.py`):
```sql
-- After INSERT on tasks
CREATE TRIGGER tasks_fts_insert AFTER INSERT ON tasks BEGIN
  INSERT INTO tasks_fts(rowid, title, description) VALUES (new.rowid, new.title, new.description);
END;

-- Before UPDATE on tasks (delete old entry)
CREATE TRIGGER tasks_fts_update_before BEFORE UPDATE ON tasks BEGIN
  DELETE FROM tasks_fts WHERE rowid = old.rowid;
END;

-- After UPDATE on tasks (insert new entry)
CREATE TRIGGER tasks_fts_update_after AFTER UPDATE ON tasks BEGIN
  INSERT INTO tasks_fts(rowid, title, description) VALUES (new.rowid, new.title, new.description);
END;

-- Before DELETE on tasks
CREATE TRIGGER tasks_fts_delete BEFORE DELETE ON tasks BEGIN
  DELETE FROM tasks_fts WHERE rowid = old.rowid;
END;
```

### 2.3 Migration from tasks.json

One-time migration script: reads `tasks.json`, creates the default project and columns, inserts tasks into the correct column based on their `status` field, migrates existing comments. Run automatically on first startup if `tasks.json` exists and the SQLite DB doesn't.

---

## 3. API Layer

Base path: `/api`. Server runs on **port 5051** (macOS port 5000 is used by AirPlay Receiver). The port is set in `app.py` and configurable via `KANBN_PORT` environment variable.

### 3.1 Projects
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/projects` | List all projects |
| POST | `/api/projects` | Create project |
| GET | `/api/projects/:id` | Get project detail |
| PUT | `/api/projects/:id` | Update project |
| DELETE | `/api/projects/:id` | Delete project + cascade |

### 3.2 Columns
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/projects/:id/columns` | List columns for project |
| POST | `/api/projects/:id/columns` | Create column |
| PUT | `/api/columns/:id` | Update column (name, color, wip_limit) |
| DELETE | `/api/columns/:id` | Delete column — returns 409 if column has tasks; client must move them first |
| PUT | `/api/projects/:id/columns/reorder` | Body: `{"order": ["id1","id2",...]}` |

### 3.3 Tasks
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/projects/:id/board` | Board data: columns with nested tasks, ordered |
| GET | `/api/tasks` | List/search/filter tasks (flat list) |
| POST | `/api/tasks` | Create task (see body spec below) |
| GET | `/api/tasks/:id` | Get task with subtasks, labels, comments |
| PUT | `/api/tasks/:id` | Update task fields |
| DELETE | `/api/tasks/:id` | Delete task + cascade |
| PUT | `/api/tasks/:id/move` | Body: `{"column_id": "...", "position": 2}` |

**Query params for `GET /api/tasks`:**
- `q` — full-text search (FTS5)
- `project_id` — filter by project
- `column_id` — filter by column
- `label` — comma-separated label names
- `priority` — high, medium, low
- `assignee` — name match
- `due_before` / `due_after` — date range
- `sort` — `created_at`, `due_date`, `priority`, `updated_at`
- `order` — `asc` / `desc`

**`POST /api/tasks` request body:**
- `title` (required) — string
- `column_id` (optional) — UUID; defaults to first column of the project
- `project_id` (optional) — UUID; defaults to the default project
- `description` (optional) — string
- `priority` (optional) — "high" / "medium" / "low"; defaults to "medium"
- `assignee` (optional) — string
- `due_date` (optional) — ISO8601 date string

**`GET /api/projects/:id/board` response:**
Returns columns in position order, each with its tasks in position order:
```json
{
  "project": { "id": "...", "name": "..." },
  "columns": [
    {
      "id": "...", "name": "Backlog", "position": 0, "color": "#7A9090", "wip_limit": null,
      "tasks": [ { "id": "...", "title": "...", ... }, ... ]
    },
    ...
  ]
}
```
The board view uses this single endpoint. The flat `GET /api/tasks` is used by list view, search, calendar, and the menu bar widget.

### 3.4 Labels
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/labels` | List labels (optional `?project_id=`) |
| POST | `/api/labels` | Create label |
| PUT | `/api/labels/:id` | Update label |
| DELETE | `/api/labels/:id` | Delete label (detaches from tasks) |
| POST | `/api/tasks/:id/labels/:label_id` | Attach label to task |
| DELETE | `/api/tasks/:id/labels/:label_id` | Detach label from task |

### 3.5 Subtasks
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tasks/:id/subtasks` | List subtasks |
| POST | `/api/tasks/:id/subtasks` | Create subtask |
| PUT | `/api/subtasks/:id` | Update (title, completed, position) |
| DELETE | `/api/subtasks/:id` | Delete subtask |

### 3.6 Comments
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tasks/:id/comments` | List comments |
| POST | `/api/tasks/:id/comments` | Add comment |
| PUT | `/api/comments/:id` | Edit comment text |
| DELETE | `/api/comments/:id` | Delete comment |

### 3.7 Activity & Analytics
| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/tasks/:id/activity` | Activity log for task |
| GET | `/api/analytics/summary` | Counts by status, overdue, avg cycle time. Query: `?project_id=` (defaults to default project) |
| GET | `/api/analytics/velocity` | Tasks completed per week, last 8 weeks. Query: `?project_id=` |
| GET | `/api/analytics/cycle-time` | Avg time per column. Query: `?project_id=` |

### 3.8 Auto-generated activity

All mutation endpoints (create, update, move, delete on tasks; label attach/detach; subtask toggle) automatically write to `activity_log`. No separate API to write activity — it's a side effect of other operations.

---

## 4. Web UI

### 4.1 Application Shell

**Sidebar (left, 220px, collapsible to 56px icon rail):**
- Logo (Kanbn monogram + wordmark)
- Search bar — triggers `GET /api/tasks?q=...`, results in a dropdown
- View nav: Board, List, Calendar, Analytics (icons + labels)
- Labels section: colour dots + names, click to filter board by label, "+ Add label" at bottom
- User avatar + name at bottom (hardcoded "Lewis" in v1)
- Collapse toggle: chevron button at top, remembers state in localStorage

**Top bar (above content area):**
- Current project name + task count
- Filter chips: Priority, Assignee, Label — dropdown selectors, active filters shown as removable chips
- "New Task" button (teal, opens quick-add modal)

**Content area:** Renders the active view (Board, List, Calendar, Analytics).

**Routing:** Hash-based routing (`#/board`, `#/list`, `#/calendar`, `#/analytics`, `#/task/{id}`). The Flask catch-all route serves `index.html` for all paths; `app.js` reads `location.hash` to determine the active view. Hash routing is chosen over History API because it requires no server-side routing logic and works with vanilla JS (no bundler). Canonical hash format uses leading slash: `#/board`, `#/list`, `#/calendar`, `#/analytics`, `#/task/{id}`. The menu bar widget deep-links to `http://localhost:5051/#/task/{id}`.

### 4.2 Board View (enhanced Kanban)

Evolution of the current board:
- Columns from the `columns` table, not hardcoded
- Column headers: coloured dot, name, count badge, overflow menu (rename, set WIP limit, delete)
- Drag-and-drop columns to reorder (drag by header)
- Drag-and-drop cards between columns and within columns (reposition)
- "+ Add column" placeholder at the end
- WIP limit: column header shows "2/3" and border turns gold when at limit, red when exceeded
- **Drag-and-drop:** HTML5 Drag and Drop API (same as current implementation). `draggable="true"` on cards and column headers, `ondragstart`/`ondragover`/`ondrop` handlers. Card drag uses `pointer-events: none` on siblings during drag to prevent drop interception (proven fix from current codebase). Column drag distinguished by a `data-drag-type="column"` attribute.

**Card enhancements:**
- Label chips (coloured pills below the title, max 3 visible + "+2" overflow)
- Due date badge (grey normally, coral if overdue, gold if due today)
- Subtask progress: `☑ 3/7` indicator
- Assignee avatar (small circle, bottom-right)
- Comment count icon
- All existing hover animations and micro-interactions preserved

### 4.3 List View

Dense table layout:
| Checkbox | ID | Title | Status | Priority | Assignee | Labels | Due Date | Updated |
|----------|-----|-------|--------|----------|----------|--------|----------|---------|

- Click column headers to sort
- Click a row to open the task detail modal
- Checkboxes for bulk select → bulk actions bar appears at top (move to column, set priority, add label, delete)
- Inline edit: double-click title to edit in place
- Same filter bar as board view applies here

### 4.4 Calendar View

Monthly grid:
- Tasks placed on their due date cell
- Colour-coded by priority (coral/gold/teal left border)
- Click a task to open detail modal
- Drag a task to a different date to change due date
- Nav: month/year selector, today button
- Right sidebar: "Unscheduled" panel listing tasks without due dates — drag from here onto a date to assign

### 4.5 Analytics View

Dashboard with four chart widgets:

**Task Distribution** (donut chart)
- Segments by column (using column colours)
- Centre: total task count

**Velocity** (bar chart)
- Tasks completed per week, last 8 weeks
- Stacked by priority colour

**Cycle Time** (horizontal bar chart)
- Average days spent in each column
- Helps identify bottlenecks

**Overdue & Summary** (stats cards)
- Total tasks, in-progress count, overdue count, completion rate %
- Overdue tasks listed below with links to open them

Charts rendered with `<canvas>` — using Chart.js (loaded via CDN, no build step). Alternatives: vanilla SVG if we want zero dependencies.

### 4.6 Task Detail Modal (enhanced)

Two-panel layout inside the existing modal overlay:

**Left panel (main content, ~65% width):**
- Task ID (JetBrains Mono) + editable title
- Description with basic Markdown rendering (bold, italic, lists, code blocks via a lightweight parser — no external lib, simple regex replacements)
- Subtasks checklist: toggleable checkboxes, drag to reorder, progress bar, "+ Add subtask" input
- Comments section: same as current, with edit button on own comments
- Activity log: collapsible section, auto-generated entries with timestamps

**Right panel (metadata sidebar, ~35% width):**
- Status dropdown (column selector)
- Priority dropdown
- Assignee text input with autocomplete from existing assignees
- Due date picker (native `<input type="date">` styled to match theme)
- Labels: attached labels as removable chips + dropdown to add more
- Created / Updated timestamps
- Delete button at bottom

### 4.7 Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `N` | Open new task modal |
| `/` | Focus search bar |
| `B` | Switch to board view |
| `L` | Switch to list view |
| `C` | Switch to calendar view |
| `Escape` | Close modal / deselect |
| `[` | Collapse/expand sidebar |
| `?` | Show shortcuts help overlay |

Only active when no input is focused.

---

## 5. macOS Menu Bar Widget (SwiftUI)

### 5.1 Architecture

Standalone SwiftUI macOS app. Ships as a `.app` bundle. Communicates with the Flask backend via HTTP to `http://localhost:5051/api/*`.

### 5.2 Menu Bar Presence

- System tray icon: Kanbn "K" monogram, 18x18pt
- Teal when connected to the API, grey when server is unreachable
- Click to open a popover (not a window), ~320px wide × 480px tall

### 5.3 Popover Contents

**Quick-add bar (top):**
- Text field + Enter to create a task in the default column (first column of default project)
- Priority picker (segmented control: H / M / L)

**Today's Focus (main section):**
- Tasks that are: assigned to user AND (in progress OR high priority OR due today)
- Max 5 shown, "View all in dashboard" link
- Each task row: priority dot, title (truncated), due date if set
- Checkbox to mark done (moves to last column)
- Click task title → opens `http://localhost:5051/#/task/{id}` in default browser

**Overdue (section, shown only if > 0):**
- Red header with count
- Same task row format

**Quick stats (bottom bar):**
- "3 active · 2 overdue · 14 total"

### 5.4 Server Detection

- Polls `GET /api/tasks` every 30 seconds
- If request fails: icon turns grey, popover shows "Server offline" banner with "Start Server" button
- "Start Server" runs `python3 {app_path}/app.py &` as a detached process
- On first launch, user configures the path to `app.py` and the server port (default 5051) in preferences

### 5.5 Global Hotkey

`⌥⇧K` — toggles the popover from any app. Registered via `NSEvent.addGlobalMonitorForEvents`.

### 5.6 Launch on Login

Optional LaunchAgent plist installed to `~/Library/LaunchAgents/`. Toggled in a minimal preferences view.

---

## 6. File Structure

```
todo-dashboard/
├── app.py                  # Flask app entry point, route registration
├── db.py                   # SQLite connection, schema init, migration
├── models/
│   ├── project.py          # Project CRUD
│   ├── column.py           # Column CRUD + reorder
│   ├── task.py             # Task CRUD, move, search
│   ├── label.py            # Label CRUD, attach/detach
│   ├── subtask.py          # Subtask CRUD
│   ├── comment.py          # Comment CRUD
│   └── activity.py         # Activity log write + query
├── routes/
│   ├── projects.py         # /api/projects/* blueprints
│   ├── columns.py          # /api/columns/* blueprints
│   ├── tasks.py            # /api/tasks/* blueprints
│   ├── labels.py           # /api/labels/* blueprints
│   ├── subtasks.py         # /api/subtasks/* blueprints
│   ├── comments.py         # /api/comments/* blueprints
│   └── analytics.py        # /api/analytics/* blueprints
├── static/
│   ├── index.html          # Main SPA shell
│   ├── css/
│   │   ├── base.css        # Reset, tokens, typography
│   │   ├── layout.css      # Sidebar, topbar, shell
│   │   ├── board.css       # Board view styles
│   │   ├── list.css        # List view styles
│   │   ├── calendar.css    # Calendar view styles
│   │   ├── analytics.css   # Analytics view styles
│   │   ├── modal.css       # Task detail modal
│   │   └── components.css  # Buttons, badges, cards, toasts
│   └── js/
│       ├── app.js          # Init, routing, state management
│       ├── api.js          # API client wrapper
│       ├── board.js        # Board view rendering + drag-drop
│       ├── list.js         # List view rendering + sorting
│       ├── calendar.js     # Calendar view rendering
│       ├── analytics.js    # Analytics charts (Chart.js)
│       ├── modal.js        # Task detail modal
│       ├── sidebar.js      # Sidebar, search, label management
│       └── shortcuts.js    # Keyboard shortcut handler
├── kanbn.db                # SQLite database (gitignored)
├── tasks.json              # Legacy data (migrated on first run)
├── tasks.log               # App log
├── kanbn-menubar/          # SwiftUI menu bar app (Xcode project)
│   ├── KanbnMenuBar.xcodeproj
│   ├── KanbnMenuBar/
│   │   ├── KanbnMenuBarApp.swift
│   │   ├── MenuBarView.swift
│   │   ├── TaskRow.swift
│   │   ├── QuickAddView.swift
│   │   ├── APIClient.swift
│   │   ├── Models.swift
│   │   └── Preferences.swift
│   └── Assets.xcassets/
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-03-13-kanbn-dashboard-design.md
```

### 6.1 Why split the monolith

The current `app.py` (219 lines) and `index.html` (~1270 lines) are manageable now but won't be at 3-4x the feature surface. Splitting into:
- **`models/`** — one file per entity, pure data logic, no Flask imports
- **`routes/`** — one file per resource, thin Flask blueprints that call models
- **`static/css/`** — one file per view/concern
- **`static/js/`** — one file per view/concern, loaded by `index.html` as `<script>` tags (no bundler)

Each file stays under 200-300 lines. Easy to reason about, easy for agents to edit.

---

## 7. Implementation Tiers

### Tier 1: Foundation (build first)
- SQLite schema + migration from tasks.json
- Model layer (all CRUD operations)
- Route layer (all API endpoints)
- Full-text search
- Web UI: sidebar, board view with custom columns, enhanced cards, filter bar, search
- Enhanced task detail modal (subtasks, labels, activity log)
- Logo + rebranding from Smithy to Kanbn
- Keyboard shortcuts

### Tier 2: Power Features
- List view
- Calendar view
- Mac menu bar widget (SwiftUI)
- Column drag-and-drop reorder
- WIP limits

### Tier 3: Advanced
- Analytics view (Chart.js)
- Velocity / cycle time calculations
- Bulk operations in list view
- Saved filter presets

---

## 8. Migration Strategy

On first startup, if `tasks.json` exists and `kanbn.db` does not:
1. Create the database and schema
2. Create default project "Kanbn"
3. Create default columns: Backlog (from `todo`), In Progress (from `in_progress`), Review (new, empty), Done (from `done`)
4. Insert each task from `tasks.json` into the correct column, preserving IDs, comments, timestamps. Fields not present in the legacy data (`assignee`, `due_date`, labels, subtasks) are set to null/empty.
5. Rename `tasks.json` → `tasks.json.migrated`
6. Log the migration

After migration, `tasks.json` is no longer used. All reads/writes go through SQLite.
