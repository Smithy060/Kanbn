"""Column CRUD + reorder operations."""
import uuid
from db import now_iso


def get_for_project(conn, project_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM columns WHERE project_id = ? ORDER BY position, created_at",
        (project_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(conn, column_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM columns WHERE id = ?", (column_id,)
    ).fetchone()
    return dict(row) if row else None


def get_first_for_project(conn, project_id: str) -> dict | None:
    """Return the column with the lowest position for a project."""
    row = conn.execute(
        "SELECT * FROM columns WHERE project_id = ? ORDER BY position LIMIT 1",
        (project_id,),
    ).fetchone()
    return dict(row) if row else None


def create(conn, project_id: str, name: str, color: str = None, wip_limit: int = None) -> dict:
    now = now_iso()
    cid = str(uuid.uuid4())
    # Position = max + 1
    row = conn.execute(
        "SELECT COALESCE(MAX(position), -1) FROM columns WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    position = row[0] + 1
    conn.execute(
        "INSERT INTO columns (id, project_id, name, position, color, wip_limit, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (cid, project_id, name, position, color, wip_limit, now, now),
    )
    conn.commit()
    return get_by_id(conn, cid)


def update(conn, column_id: str, name: str = None, color: str = None, wip_limit=None) -> dict | None:
    col = get_by_id(conn, column_id)
    if not col:
        return None
    new_name = name if name is not None else col["name"]
    new_color = color if color is not None else col["color"]
    new_wip = wip_limit if wip_limit is not None else col["wip_limit"]
    conn.execute(
        "UPDATE columns SET name=?, color=?, wip_limit=?, updated_at=? WHERE id=?",
        (new_name, new_color, new_wip, now_iso(), column_id),
    )
    conn.commit()
    return get_by_id(conn, column_id)


def delete(conn, column_id: str) -> tuple[bool, str | None]:
    """
    Delete a column. Returns (True, None) on success.
    Returns (False, "has_tasks") if the column contains tasks — caller returns 409.
    """
    row = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE column_id = ?", (column_id,)
    ).fetchone()
    if row[0] > 0:
        return False, "has_tasks"
    cur = conn.execute("DELETE FROM columns WHERE id = ?", (column_id,))
    conn.commit()
    return cur.rowcount > 0, None


def reorder(conn, project_id: str, order: list[str]) -> list[dict]:
    """
    Reorder columns for a project. `order` is a list of column IDs in the new order.
    Updates position field for each column.
    """
    for position, column_id in enumerate(order):
        conn.execute(
            "UPDATE columns SET position=?, updated_at=? WHERE id=? AND project_id=?",
            (position, now_iso(), column_id, project_id),
        )
    conn.commit()
    return get_for_project(conn, project_id)


def task_count(conn, column_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE column_id = ?", (column_id,)
    ).fetchone()
    return row[0]
