"""
db.py — SQLite connection, schema initialisation, FTS5 triggers, and migration
from tasks.json to kanbn.db.
"""
import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone

log = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "kanbn.db")
TASKS_JSON = os.path.join(BASE_DIR, "tasks.json")


# ── Connection factory ────────────────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a new SQLite connection with foreign keys enabled and Row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS columns (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    color       TEXT,
    wip_limit   INTEGER,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    column_id   TEXT NOT NULL REFERENCES columns(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    description TEXT,
    priority    TEXT NOT NULL DEFAULT 'medium',
    assignee    TEXT,
    due_date    TEXT,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labels (
    id          TEXT PRIMARY KEY,
    project_id  TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    color       TEXT
);

CREATE TABLE IF NOT EXISTS task_labels (
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    label_id    TEXT NOT NULL REFERENCES labels(id) ON DELETE CASCADE,
    PRIMARY KEY (task_id, label_id)
);

CREATE TABLE IF NOT EXISTS subtasks (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    title       TEXT NOT NULL,
    completed   INTEGER NOT NULL DEFAULT 0,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS comments (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    text        TEXT NOT NULL,
    author      TEXT NOT NULL DEFAULT 'User',
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id          TEXT PRIMARY KEY,
    task_id     TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    action      TEXT NOT NULL,
    detail      TEXT NOT NULL DEFAULT '{}',
    actor       TEXT NOT NULL DEFAULT 'User',
    created_at  TEXT NOT NULL
);

-- FTS5 virtual table (content-backed by tasks)
CREATE VIRTUAL TABLE IF NOT EXISTS tasks_fts USING fts5(
    title, description, content=tasks, content_rowid=rowid
);

-- FTS sync triggers
CREATE TRIGGER IF NOT EXISTS tasks_fts_insert
AFTER INSERT ON tasks BEGIN
    INSERT INTO tasks_fts(rowid, title, description)
    VALUES (new.rowid, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS tasks_fts_update_before
BEFORE UPDATE ON tasks BEGIN
    DELETE FROM tasks_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS tasks_fts_update_after
AFTER UPDATE ON tasks BEGIN
    INSERT INTO tasks_fts(rowid, title, description)
    VALUES (new.rowid, new.title, new.description);
END;

CREATE TRIGGER IF NOT EXISTS tasks_fts_delete
BEFORE DELETE ON tasks BEGIN
    DELETE FROM tasks_fts WHERE rowid = old.rowid;
END;
"""

# Default columns for a new project
DEFAULT_COLUMNS = [
    {"name": "Backlog",     "color": "#7A9090", "position": 0},
    {"name": "In Progress", "color": "#0D7377", "position": 1},
    {"name": "Review",      "color": "#D4A843", "position": 2},
    {"name": "Done",        "color": "#2D8B6F", "position": 3},
]


def init_db() -> None:
    """Create schema (idempotent). Run on every startup."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        log.info("Database schema initialised at %s", DB_PATH)
    finally:
        conn.close()


# ── Migration from tasks.json ─────────────────────────────────────────────────

# tasks.json status → default column name
STATUS_MAP = {
    "todo":        "Backlog",
    "in_progress": "In Progress",
    "done":        "Done",
}


def migrate_from_json() -> None:
    """
    One-time migration: if tasks.json exists and kanbn.db has no projects yet,
    create the default project + columns and import tasks/comments.
    Renames tasks.json → tasks.json.migrated on success.
    """
    if not os.path.exists(TASKS_JSON):
        return

    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) FROM projects").fetchone()
        if row[0] > 0:
            log.info("Migration skipped — projects already exist in DB")
            return

        with open(TASKS_JSON) as f:
            legacy_tasks = json.load(f)

        now = now_iso()
        project_id = str(uuid.uuid4())

        # Create default project
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?,?,?,?,?)",
            (project_id, "Kanbn", "Imported from tasks.json", now, now),
        )

        # Create default columns, build name→id map
        col_id_map: dict[str, str] = {}
        for col in DEFAULT_COLUMNS:
            cid = str(uuid.uuid4())
            col_id_map[col["name"]] = cid
            conn.execute(
                "INSERT INTO columns (id, project_id, name, position, color, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (cid, project_id, col["name"], col["position"], col["color"], now, now),
            )

        # Import tasks
        for pos, task in enumerate(legacy_tasks):
            status = task.get("status", "todo")
            col_name = STATUS_MAP.get(status, "Backlog")
            col_id = col_id_map[col_name]
            task_id = task.get("id") or str(uuid.uuid4())
            created = task.get("created_at", now)
            updated = task.get("updated_at", now)

            conn.execute(
                """INSERT INTO tasks
                   (id, project_id, column_id, title, description, priority,
                    position, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (
                    task_id,
                    project_id,
                    col_id,
                    task.get("title", "Untitled"),
                    task.get("description", ""),
                    task.get("priority", "medium"),
                    pos,
                    created,
                    updated,
                ),
            )

            # Log creation event
            conn.execute(
                "INSERT INTO activity_log (id, task_id, action, detail, actor, created_at) VALUES (?,?,?,?,?,?)",
                (str(uuid.uuid4()), task_id, "created", "{}", "User", created),
            )

            # Import comments
            for comment in task.get("comments", []):
                cid = comment.get("id") or str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO comments (id, task_id, text, author, created_at) VALUES (?,?,?,?,?)",
                    (cid, task_id, comment.get("text", ""), "User", comment.get("created_at", now)),
                )

        conn.commit()
        migrated_path = TASKS_JSON + ".migrated"
        os.rename(TASKS_JSON, migrated_path)
        log.info(
            "Migration complete: %d tasks imported, tasks.json → %s",
            len(legacy_tasks),
            migrated_path,
        )

    except Exception as exc:
        conn.rollback()
        log.error("Migration failed: %s", exc)
        raise
    finally:
        conn.close()


def ensure_default_project() -> None:
    """If DB has no projects at all, create the default project with default columns."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT COUNT(*) FROM projects").fetchone()
        if row[0] > 0:
            return
        now = now_iso()
        project_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?,?,?,?,?)",
            (project_id, "Kanbn", "", now, now),
        )
        for col in DEFAULT_COLUMNS:
            cid = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO columns (id, project_id, name, position, color, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
                (cid, project_id, col["name"], col["position"], col["color"], now, now),
            )
        conn.commit()
        log.info("Created default project id=%s", project_id)
    finally:
        conn.close()
