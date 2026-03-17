"""Subtask CRUD operations."""
import uuid
from db import now_iso


def get_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM subtasks WHERE task_id = ? ORDER BY position",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(conn, subtask_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM subtasks WHERE id = ?", (subtask_id,)).fetchone()
    return dict(row) if row else None


def create(conn, task_id: str, title: str) -> dict:
    now = now_iso()
    sid = str(uuid.uuid4())
    row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) FROM subtasks WHERE task_id = ?",
        (task_id,),
    ).fetchone()
    position = row[0] + 1
    conn.execute(
        "INSERT INTO subtasks (id, task_id, title, completed, position, created_at) VALUES (?,?,?,?,?,?)",
        (sid, task_id, title, 0, position, now),
    )
    conn.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now, task_id))
    conn.commit()
    return get_by_id(conn, sid)


def update(conn, subtask_id: str, title: str = None, completed: bool = None,
           position: int = None) -> dict | None:
    from models.activity import log_event
    sub = get_by_id(conn, subtask_id)
    if not sub:
        return None
    new_title = title if title is not None else sub["title"]
    new_completed = int(completed) if completed is not None else sub["completed"]
    new_position = position if position is not None else sub["position"]

    # Log subtask toggle if completed state changed
    if completed is not None and new_completed != sub["completed"]:
        log_event(conn, sub["task_id"], "subtask_toggled",
                  {"subtask_id": subtask_id, "completed": bool(new_completed)})

    conn.execute(
        "UPDATE subtasks SET title=?, completed=?, position=? WHERE id=?",
        (new_title, new_completed, new_position, subtask_id),
    )
    conn.execute(
        "UPDATE tasks SET updated_at = ? WHERE id = ?", (now_iso(), sub["task_id"])
    )
    conn.commit()
    return get_by_id(conn, subtask_id)


def delete(conn, subtask_id: str) -> bool:
    sub = get_by_id(conn, subtask_id)
    if not sub:
        return False
    cur = conn.execute("DELETE FROM subtasks WHERE id = ?", (subtask_id,))
    conn.execute(
        "UPDATE tasks SET updated_at = ? WHERE id = ?", (now_iso(), sub["task_id"])
    )
    conn.commit()
    return cur.rowcount > 0
