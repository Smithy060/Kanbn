"""Comment CRUD operations."""
import uuid
from db import now_iso


def get_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM comments WHERE task_id = ? ORDER BY created_at",
        (task_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(conn, comment_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM comments WHERE id = ?", (comment_id,)
    ).fetchone()
    return dict(row) if row else None


def create(conn, task_id: str, text: str, author: str = "Lewis") -> dict:
    now = now_iso()
    cid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO comments (id, task_id, text, author, created_at) VALUES (?,?,?,?,?)",
        (cid, task_id, text, author, now),
    )
    conn.execute("UPDATE tasks SET updated_at = ? WHERE id = ?", (now, task_id))
    conn.commit()
    return get_by_id(conn, cid)


def update(conn, comment_id: str, text: str) -> dict | None:
    comment = get_by_id(conn, comment_id)
    if not comment:
        return None
    conn.execute(
        "UPDATE comments SET text = ? WHERE id = ?", (text, comment_id)
    )
    conn.execute(
        "UPDATE tasks SET updated_at = ? WHERE id = ?", (now_iso(), comment["task_id"])
    )
    conn.commit()
    return get_by_id(conn, comment_id)


def delete(conn, comment_id: str) -> bool:
    comment = get_by_id(conn, comment_id)
    if not comment:
        return False
    cur = conn.execute("DELETE FROM comments WHERE id = ?", (comment_id,))
    conn.execute(
        "UPDATE tasks SET updated_at = ? WHERE id = ?", (now_iso(), comment["task_id"])
    )
    conn.commit()
    return cur.rowcount > 0
