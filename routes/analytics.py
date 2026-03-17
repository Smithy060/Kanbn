"""Blueprint: /api/analytics/* and /api/tasks/:id/activity"""
import json
from datetime import datetime, timezone, timedelta
from flask import Blueprint, g, jsonify, request
import models.activity as Activity
import models.project as Project
import models.task as Task

bp = Blueprint("analytics", __name__)


def get_db():
    return g.db


def _resolve_project_id(db) -> str | None:
    project_id = request.args.get("project_id")
    if not project_id:
        p = Project.get_default(db)
        return p["id"] if p else None
    return project_id


# ── Activity log for a task ───────────────────────────────────────────────────

@bp.route("/api/tasks/<task_id>/activity", methods=["GET"])
def get_task_activity(task_id):
    if not Task.get_by_id(get_db(), task_id):
        return jsonify({"error": "task not found"}), 404
    return jsonify(Activity.get_for_task(get_db(), task_id))


# ── Analytics ─────────────────────────────────────────────────────────────────

@bp.route("/api/analytics/summary", methods=["GET"])
def summary():
    db = get_db()
    project_id = _resolve_project_id(db)
    if not project_id:
        return jsonify({"error": "no project found"}), 404

    now = datetime.now(timezone.utc).isoformat()[:10]  # date only

    # Task counts per column
    rows = conn_exec(db,
        """SELECT c.id, c.name, c.color, c.position, COUNT(t.id) as task_count
           FROM columns c
           LEFT JOIN tasks t ON t.column_id = c.id
           WHERE c.project_id = ?
           GROUP BY c.id
           ORDER BY c.position""",
        (project_id,),
    )
    by_column = [dict(r) for r in rows]

    # Overdue count (has due_date in past, not in the last column)
    last_col = db.execute(
        "SELECT id FROM columns WHERE project_id = ? ORDER BY position DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    last_col_id = last_col["id"] if last_col else None

    overdue_count = db.execute(
        """SELECT COUNT(*) FROM tasks
           WHERE project_id = ? AND due_date IS NOT NULL AND due_date < ?
           AND column_id != ?""",
        (project_id, now, last_col_id or ""),
    ).fetchone()[0]

    total = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE project_id = ?", (project_id,)
    ).fetchone()[0]

    done_count = db.execute(
        "SELECT COUNT(*) FROM tasks WHERE column_id = ?", (last_col_id or "",)
    ).fetchone()[0]

    completion_rate = round(done_count / total * 100) if total > 0 else 0

    return jsonify({
        "project_id": project_id,
        "total": total,
        "done": done_count,
        "overdue": overdue_count,
        "completion_rate": completion_rate,
        "by_column": by_column,
    })


@bp.route("/api/analytics/velocity", methods=["GET"])
def velocity():
    db = get_db()
    project_id = _resolve_project_id(db)
    if not project_id:
        return jsonify({"error": "no project found"}), 404

    # Last column = "Done"
    last_col = db.execute(
        "SELECT id FROM columns WHERE project_id = ? ORDER BY position DESC LIMIT 1",
        (project_id,),
    ).fetchone()
    if not last_col:
        return jsonify([])
    last_col_id = last_col["id"]

    # Find all "moved" events to the Done column, group by ISO week
    rows = db.execute(
        """SELECT al.created_at, al.detail, al.task_id
           FROM activity_log al
           JOIN tasks t ON t.id = al.task_id
           WHERE t.project_id = ? AND al.action = 'moved'
           ORDER BY al.created_at""",
        (project_id,),
    ).fetchall()

    # Build week buckets for last 8 weeks
    now = datetime.now(timezone.utc)
    weeks: list[dict] = []
    for i in range(7, -1, -1):
        week_start = now - timedelta(weeks=i)
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        # Align to Monday
        week_start -= timedelta(days=week_start.weekday())
        weeks.append({
            "week": week_start.strftime("%Y-W%W"),
            "week_start": week_start.isoformat(),
            "high": 0,
            "medium": 0,
            "low": 0,
            "total": 0,
        })

    # Cache task priorities
    task_priorities: dict[str, str] = {}

    for row in rows:
        try:
            detail = json.loads(row["detail"])
        except Exception:
            continue
        if detail.get("to_column_id") != last_col_id:
            continue
        try:
            ts = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        # Find the right week bucket
        for week in weeks:
            ws = datetime.fromisoformat(week["week_start"])
            we = ws + timedelta(weeks=1)
            if ws <= ts < we:
                task_id = row["task_id"]
                if task_id not in task_priorities:
                    t = db.execute("SELECT priority FROM tasks WHERE id = ?", (task_id,)).fetchone()
                    task_priorities[task_id] = t["priority"] if t else "medium"
                pri = task_priorities[task_id]
                week[pri] = week.get(pri, 0) + 1
                week["total"] += 1
                break

    return jsonify(weeks)


@bp.route("/api/analytics/cycle-time", methods=["GET"])
def cycle_time():
    db = get_db()
    project_id = _resolve_project_id(db)
    if not project_id:
        return jsonify({"error": "no project found"}), 404

    columns = db.execute(
        "SELECT id, name FROM columns WHERE project_id = ? ORDER BY position",
        (project_id,),
    ).fetchall()
    col_map = {r["id"]: r["name"] for r in columns}

    # Load all "moved" events for this project, sorted by task + time
    rows = db.execute(
        """SELECT al.task_id, al.created_at, al.detail
           FROM activity_log al
           JOIN tasks t ON t.id = al.task_id
           WHERE t.project_id = ? AND al.action = 'moved'
           ORDER BY al.task_id, al.created_at""",
        (project_id,),
    ).fetchall()

    # Accumulate total time and event count per from_column_id
    col_durations: dict[str, list[float]] = {}  # col_id → [hours, ...]

    prev: dict[str, tuple[str, datetime]] = {}  # task_id → (from_col_id, moved_at)

    for row in rows:
        try:
            detail = json.loads(row["detail"])
            ts = datetime.fromisoformat(row["created_at"].replace("Z", "+00:00"))
        except Exception:
            continue
        from_col = detail.get("from_column_id")
        task_id = row["task_id"]

        if task_id in prev and prev[task_id][0] == from_col:
            _, prev_ts = prev[task_id]
            delta_hours = (ts - prev_ts).total_seconds() / 3600
            col_durations.setdefault(from_col, []).append(delta_hours)

        prev[task_id] = (detail.get("to_column_id"), ts)

    result = []
    for col_id, name in col_map.items():
        durations = col_durations.get(col_id, [])
        avg_hours = sum(durations) / len(durations) if durations else 0
        result.append({
            "column_id": col_id,
            "column_name": name,
            "avg_hours": round(avg_hours, 2),
            "avg_days": round(avg_hours / 24, 2),
            "sample_count": len(durations),
        })

    return jsonify(result)


# ── Helper ────────────────────────────────────────────────────────────────────

def conn_exec(db, sql: str, params: tuple):
    return db.execute(sql, params).fetchall()
