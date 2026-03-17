"""Project CRUD operations."""
import uuid
from db import now_iso, DEFAULT_COLUMNS


def get_all(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM projects ORDER BY created_at"
    ).fetchall()
    return [dict(r) for r in rows]


def get_by_id(conn, project_id: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM projects WHERE id = ?", (project_id,)
    ).fetchone()
    return dict(row) if row else None


def get_default(conn) -> dict | None:
    """Return the first project (by created_at) — used as the default project."""
    row = conn.execute(
        "SELECT * FROM projects ORDER BY created_at LIMIT 1"
    ).fetchone()
    return dict(row) if row else None


def create(conn, name: str, description: str = "") -> dict:
    now = now_iso()
    pid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?,?,?,?,?)",
        (pid, name, description, now, now),
    )
    # Create default columns for the new project
    for col in DEFAULT_COLUMNS:
        cid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO columns (id, project_id, name, position, color, created_at, updated_at) VALUES (?,?,?,?,?,?,?)",
            (cid, pid, col["name"], col["position"], col["color"], now, now),
        )
    conn.commit()
    return get_by_id(conn, pid)


def update(conn, project_id: str, name: str = None, description: str = None) -> dict | None:
    project = get_by_id(conn, project_id)
    if not project:
        return None
    new_name = name if name is not None else project["name"]
    new_desc = description if description is not None else project["description"]
    conn.execute(
        "UPDATE projects SET name=?, description=?, updated_at=? WHERE id=?",
        (new_name, new_desc, now_iso(), project_id),
    )
    conn.commit()
    return get_by_id(conn, project_id)


def delete(conn, project_id: str) -> bool:
    cur = conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    return cur.rowcount > 0
