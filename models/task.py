"""Task CRUD, move, search, and board assembly."""
import json
import uuid
from db import now_iso


def _row_to_dict(row) -> dict:
    return dict(row)


# ── Core CRUD ────────────────────────────────────────────────────────────────

def get_by_id(conn, task_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return _row_to_dict(row) if row else None


def get_full(conn, task_id: str) -> dict | None:
    """Return task with labels, subtasks, and comments."""
    task = get_by_id(conn, task_id)
    if not task:
        return None
    task["labels"] = _labels_for_task(conn, task_id)
    task["subtasks"] = _subtasks_for_task(conn, task_id)
    task["comments"] = _comments_for_task(conn, task_id)
    return task


def create(conn, project_id: str, column_id: str, title: str,
           description: str = "", priority: str = "medium",
           assignee: str = None, due_date: str = None) -> dict:
    from models.activity import log_event
    now = now_iso()
    tid = str(uuid.uuid4())
    row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) FROM tasks WHERE column_id = ?",
        (column_id,),
    ).fetchone()
    position = row[0] + 1
    conn.execute(
        """INSERT INTO tasks
           (id, project_id, column_id, title, description, priority,
            assignee, due_date, position, created_at, updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (tid, project_id, column_id, title, description, priority,
         assignee, due_date, position, now, now),
    )
    log_event(conn, tid, "created")
    conn.commit()
    return get_by_id(conn, tid)


def update(conn, task_id: str, **fields) -> dict | None:
    from models.activity import log_event
    task = get_by_id(conn, task_id)
    if not task:
        return None
    allowed = {"title", "description", "priority", "assignee", "due_date", "column_id"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return task

    # Log priority change
    if "priority" in updates and updates["priority"] != task["priority"]:
        log_event(conn, task_id, "priority_changed",
                  {"from": task["priority"], "to": updates["priority"]})

    # Log assignee change
    if "assignee" in updates and updates["assignee"] != task.get("assignee"):
        log_event(conn, task_id, "assignee_changed",
                  {"from": task.get("assignee") or "", "to": updates["assignee"] or ""})

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [now_iso(), task_id]
    conn.execute(
        f"UPDATE tasks SET {set_clause}, updated_at = ? WHERE id = ?", params
    )
    conn.commit()
    return get_by_id(conn, task_id)


def delete(conn, task_id: str) -> bool:
    cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Move ─────────────────────────────────────────────────────────────────────

def move(conn, task_id: str, column_id: str, position: int) -> dict | None:
    """
    Move a task to a new column and/or position.
    Shifts other tasks in the target column to make room.
    Logs 'moved' activity with column names and IDs.
    """
    from models.activity import log_event
    task = get_by_id(conn, task_id)
    if not task:
        return None

    old_col_id = task["column_id"]
    old_col = conn.execute("SELECT name FROM columns WHERE id = ?", (old_col_id,)).fetchone()
    new_col = conn.execute("SELECT name FROM columns WHERE id = ?", (column_id,)).fetchone()
    if not new_col:
        return None

    now = now_iso()
    # Shift tasks at or after the target position in the destination column down
    conn.execute(
        """UPDATE tasks SET position = position + 1, updated_at = ?
           WHERE column_id = ? AND position >= ? AND id != ?""",
        (now, column_id, position, task_id),
    )
    conn.execute(
        "UPDATE tasks SET column_id = ?, position = ?, updated_at = ? WHERE id = ?",
        (column_id, position, now, task_id),
    )

    log_event(conn, task_id, "moved", {
        "from_column_id": old_col_id,
        "to_column_id": column_id,
        "from_column_name": old_col["name"] if old_col else "",
        "to_column_name": new_col["name"],
    })
    conn.commit()
    return get_by_id(conn, task_id)


# ── List / Search ─────────────────────────────────────────────────────────────

def list_tasks(conn, q: str = None, project_id: str = None, column_id: str = None,
               labels: list[str] = None, priority: str = None, assignee: str = None,
               due_before: str = None, due_after: str = None,
               sort: str = "created_at", order: str = "desc") -> list[dict]:
    """
    Flat list of tasks with optional filtering and full-text search.
    Each task includes a `labels` list (lightweight: id + name + color).
    """
    params: list = []

    if q:
        # FTS5 search — join back to tasks via rowid
        base = """
            SELECT t.*
            FROM tasks_fts
            JOIN tasks t ON t.rowid = tasks_fts.rowid
            WHERE tasks_fts MATCH ?
        """
        # Wrap query for FTS prefix match if it doesn't already have operators
        params.append(q if any(c in q for c in ('"', '*', 'AND', 'OR', 'NOT')) else f'"{q}"*')
    else:
        base = "SELECT t.* FROM tasks t WHERE 1=1"

    if project_id:
        base += " AND t.project_id = ?"
        params.append(project_id)
    if column_id:
        base += " AND t.column_id = ?"
        params.append(column_id)
    if priority:
        base += " AND t.priority = ?"
        params.append(priority)
    if assignee:
        base += " AND t.assignee LIKE ?"
        params.append(f"%{assignee}%")
    if due_before:
        base += " AND t.due_date <= ?"
        params.append(due_before)
    if due_after:
        base += " AND t.due_date >= ?"
        params.append(due_after)
    if labels:
        # Filter tasks that have ALL specified labels (by name)
        for label_name in labels:
            base += """
                AND t.id IN (
                    SELECT tl.task_id FROM task_labels tl
                    JOIN labels l ON l.id = tl.label_id
                    WHERE l.name = ?
                )
            """
            params.append(label_name)

    # Sorting
    valid_sorts = {"created_at", "updated_at", "due_date", "priority"}
    sort_col = sort if sort in valid_sorts else "created_at"
    sort_dir = "ASC" if order.lower() == "asc" else "DESC"

    if sort_col == "priority":
        # Custom priority ordering: high > medium > low
        priority_order = "CASE t.priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END"
        base += f" ORDER BY {priority_order} {sort_dir}"
    else:
        base += f" ORDER BY t.{sort_col} {sort_dir}"

    rows = conn.execute(base, params).fetchall()
    tasks = [_row_to_dict(r) for r in rows]

    if tasks:
        _attach_labels_batch(conn, tasks)
        _attach_counts_batch(conn, tasks)

    return tasks


# ── Board assembly ────────────────────────────────────────────────────────────

def get_board(conn, project_id: str) -> dict | None:
    from models.project import get_by_id as get_project
    from models.column import get_for_project

    project = get_project(conn, project_id)
    if not project:
        return None

    columns = get_for_project(conn, project_id)
    col_ids = [c["id"] for c in columns]

    if not col_ids:
        for col in columns:
            col["tasks"] = []
        return {"project": project, "columns": columns}

    placeholders = ",".join("?" * len(col_ids))
    rows = conn.execute(
        f"SELECT * FROM tasks WHERE column_id IN ({placeholders}) ORDER BY position",
        col_ids,
    ).fetchall()
    tasks = [_row_to_dict(r) for r in rows]

    if tasks:
        _attach_labels_batch(conn, tasks)
        _attach_counts_batch(conn, tasks)

    # Group tasks by column_id
    task_map: dict[str, list] = {cid: [] for cid in col_ids}
    for t in tasks:
        task_map[t["column_id"]].append(t)

    for col in columns:
        col["tasks"] = task_map.get(col["id"], [])

    return {"project": project, "columns": columns}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _labels_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        """SELECT l.id, l.name, l.color
           FROM labels l
           JOIN task_labels tl ON tl.label_id = l.id
           WHERE tl.task_id = ?""",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _subtasks_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY position",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _comments_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM comments WHERE task_id = ? ORDER BY created_at",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def _attach_labels_batch(conn, tasks: list[dict]) -> None:
    """Attach labels to a list of task dicts in a single query."""
    task_ids = [t["id"] for t in tasks]
    placeholders = ",".join("?" * len(task_ids))
    rows = conn.execute(
        f"""SELECT tl.task_id, l.id, l.name, l.color
            FROM task_labels tl
            JOIN labels l ON l.id = tl.label_id
            WHERE tl.task_id IN ({placeholders})""",
        task_ids,
    ).fetchall()
    label_map: dict[str, list] = {t["id"]: [] for t in tasks}
    for r in rows:
        label_map[r["task_id"]].append({"id": r["id"], "name": r["name"], "color": r["color"]})
    for t in tasks:
        t["labels"] = label_map[t["id"]]


def _attach_counts_batch(conn, tasks: list[dict]) -> None:
    """Attach subtask_count, subtask_done, and comment_count to a list of task dicts."""
    task_ids = [t["id"] for t in tasks]
    placeholders = ",".join("?" * len(task_ids))

    sub_rows = conn.execute(
        f"SELECT task_id, COUNT(*) as total, SUM(completed) as done FROM subtasks WHERE task_id IN ({placeholders}) GROUP BY task_id",
        task_ids,
    ).fetchall()
    sub_map = {r["task_id"]: (r["total"], r["done"] or 0) for r in sub_rows}

    com_rows = conn.execute(
        f"SELECT task_id, COUNT(*) as cnt FROM comments WHERE task_id IN ({placeholders}) GROUP BY task_id",
        task_ids,
    ).fetchall()
    com_map = {r["task_id"]: r["cnt"] for r in com_rows}

    for t in tasks:
        total, done = sub_map.get(t["id"], (0, 0))
        t["subtask_count"] = total
        t["subtask_done"] = done
        t["comment_count"] = com_map.get(t["id"], 0)
