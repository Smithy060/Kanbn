"""Activity log — write events, query history, and analytics."""
import json
import uuid
from datetime import datetime, timezone, timedelta
from db import now_iso


def log_event(conn, task_id: str, action: str, detail: dict = None,
              actor: str = "User") -> dict:
    now = now_iso()
    eid = str(uuid.uuid4())
    detail_json = json.dumps(detail or {})
    conn.execute(
        "INSERT INTO activity_log (id, task_id, action, detail, actor, created_at) VALUES (?,?,?,?,?,?)",
        (eid, task_id, action, detail_json, actor, now),
    )
    # No commit here — caller commits as part of their transaction
    return {
        "id": eid,
        "task_id": task_id,
        "action": action,
        "detail": detail or {},
        "actor": actor,
        "created_at": now,
    }


def get_for_task(conn, task_id: str) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM activity_log WHERE task_id = ? ORDER BY created_at DESC",
        (task_id,),
    ).fetchall()
    result = []
    for r in rows:
        entry = dict(r)
        try:
            entry["detail"] = json.loads(entry["detail"])
        except (json.JSONDecodeError, TypeError):
            entry["detail"] = {}
        result.append(entry)
    return result


# ── Analytics ────────────────────────────────────────────────────────────────

def get_summary(conn, project_id: str) -> dict:
    """Return {total, by_column, overdue_count, avg_cycle_time}."""
    total_row = conn.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()
    total = total_row[0]

    cols = conn.execute(
        "SELECT c.id, c.name, c.color, COUNT(t.id) as count FROM columns c "
        "LEFT JOIN tasks t ON t.column_id = c.id "
        "WHERE c.project_id = ? GROUP BY c.id ORDER BY c.position",
        (project_id,),
    ).fetchall()
    by_column = [{"id": r["id"], "name": r["name"], "color": r["color"], "count": r["count"]} for r in cols]

    now_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    overdue_row = conn.execute(
        """SELECT COUNT(*) FROM tasks t
           JOIN columns c ON t.column_id = c.id
           WHERE t.project_id = ? AND t.due_date IS NOT NULL
           AND t.due_date < ? AND c.name != 'Done'""",
        (project_id, now_date),
    ).fetchone()
    overdue_count = overdue_row[0]

    # Avg cycle time: average days between creation and moving to Done
    cycle_row = conn.execute(
        """SELECT AVG(
             julianday(a.created_at) - julianday(t.created_at)
           ) as avg_days
           FROM activity_log a
           JOIN tasks t ON a.task_id = t.id
           WHERE t.project_id = ? AND a.action = 'moved'
           AND json_extract(a.detail, '$.to_column_name') = 'Done'""",
        (project_id,),
    ).fetchone()
    avg_cycle_time = round(cycle_row[0], 1) if cycle_row[0] else None

    return {
        "total": total,
        "by_column": by_column,
        "overdue_count": overdue_count,
        "avg_cycle_time": avg_cycle_time,
    }


def get_velocity(conn, project_id: str) -> list[dict]:
    """Tasks completed per week, last 8 weeks."""
    weeks = []
    now = datetime.now(timezone.utc)
    for i in range(7, -1, -1):
        week_end = now - timedelta(weeks=i)
        week_start = week_end - timedelta(weeks=1)
        row = conn.execute(
            """SELECT COUNT(*) as count FROM activity_log a
               JOIN tasks t ON a.task_id = t.id
               WHERE t.project_id = ? AND a.action = 'moved'
               AND json_extract(a.detail, '$.to_column_name') = 'Done'
               AND a.created_at >= ? AND a.created_at < ?""",
            (project_id, week_start.isoformat(), week_end.isoformat()),
        ).fetchone()
        weeks.append({
            "week_start": week_start.strftime("%Y-%m-%d"),
            "week_end": week_end.strftime("%Y-%m-%d"),
            "completed": row[0],
        })
    return weeks


def get_cycle_time(conn, project_id: str) -> list[dict]:
    """Average days per column, computed from consecutive move events."""
    cols = conn.execute(
        "SELECT id, name FROM columns WHERE project_id = ? ORDER BY position",
        (project_id,),
    ).fetchall()

    result = []
    for col in cols:
        row = conn.execute(
            """SELECT AVG(duration) as avg_days FROM (
                SELECT
                  julianday(next_move.created_at) - julianday(a.created_at) as duration
                FROM activity_log a
                JOIN tasks t ON a.task_id = t.id
                LEFT JOIN activity_log next_move ON next_move.task_id = a.task_id
                  AND next_move.action = 'moved'
                  AND next_move.created_at > a.created_at
                  AND next_move.id = (
                    SELECT id FROM activity_log
                    WHERE task_id = a.task_id AND action = 'moved'
                    AND created_at > a.created_at
                    ORDER BY created_at LIMIT 1
                  )
                WHERE t.project_id = ? AND a.action = 'moved'
                AND json_extract(a.detail, '$.to_column_id') = ?
                AND next_move.id IS NOT NULL
            )""",
            (project_id, col["id"]),
        ).fetchone()
        result.append({
            "column_id": col["id"],
            "column_name": col["name"],
            "avg_days": round(row[0], 1) if row[0] else None,
        })
    return result
