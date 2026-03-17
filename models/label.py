"""Label CRUD and task-label attach/detach operations."""
import uuid
from db import now_iso


def get_all(conn, project_id: str = None) -> list[dict]:
    if project_id:
        rows = conn.execute(
            "SELECT * FROM labels WHERE project_id = ? ORDER BY name",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM labels ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_by_id(conn, label_id: str) -> dict | None:
    row = conn.execute("SELECT * FROM labels WHERE id = ?", (label_id,)).fetchone()
    return dict(row) if row else None


def create(conn, project_id: str, name: str, color: str = "#7A9090") -> dict:
    lid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO labels (id, project_id, name, color) VALUES (?,?,?,?)",
        (lid, project_id, name, color),
    )
    conn.commit()
    return get_by_id(conn, lid)


def update(conn, label_id: str, name: str = None, color: str = None) -> dict | None:
    label = get_by_id(conn, label_id)
    if not label:
        return None
    new_name = name if name is not None else label["name"]
    new_color = color if color is not None else label["color"]
    conn.execute(
        "UPDATE labels SET name=?, color=? WHERE id=?",
        (new_name, new_color, label_id),
    )
    conn.commit()
    return get_by_id(conn, label_id)


def delete(conn, label_id: str) -> bool:
    cur = conn.execute("DELETE FROM labels WHERE id = ?", (label_id,))
    conn.commit()
    return cur.rowcount > 0


# ── Attach / detach ───────────────────────────────────────────────────────────

def attach(conn, task_id: str, label_id: str) -> bool:
    """Attach label to task. Returns False if already attached. Logs activity."""
    from models.activity import log_event
    existing = conn.execute(
        "SELECT 1 FROM task_labels WHERE task_id = ? AND label_id = ?",
        (task_id, label_id),
    ).fetchone()
    if existing:
        return False
    conn.execute(
        "INSERT INTO task_labels (task_id, label_id) VALUES (?,?)",
        (task_id, label_id),
    )
    label = get_by_id(conn, label_id)
    log_event(conn, task_id, "label_added",
              {"label_id": label_id, "label_name": label["name"] if label else ""})
    conn.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now_iso(), task_id))
    conn.commit()
    return True


def detach(conn, task_id: str, label_id: str) -> bool:
    """Detach label from task. Logs activity."""
    from models.activity import log_event
    label = get_by_id(conn, label_id)
    cur = conn.execute(
        "DELETE FROM task_labels WHERE task_id = ? AND label_id = ?",
        (task_id, label_id),
    )
    if cur.rowcount == 0:
        return False
    log_event(conn, task_id, "label_removed",
              {"label_id": label_id, "label_name": label["name"] if label else ""})
    conn.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now_iso(), task_id))
    conn.commit()
    return True
