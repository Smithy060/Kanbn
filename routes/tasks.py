"""Blueprint: /api/tasks and /api/projects/:id/board"""
import json
from flask import Blueprint, g, jsonify, request
import models.column as Column
import models.project as Project
import models.task as Task
import models.activity as Activity

bp = Blueprint("tasks", __name__)

VALID_PRIORITIES = {"high", "medium", "low"}


def get_db():
    return g.db


# ── Board ─────────────────────────────────────────────────────────────────────

@bp.route("/api/projects/<project_id>/board", methods=["GET"])
def get_board(project_id):
    board = Task.get_board(get_db(), project_id)
    if not board:
        return jsonify({"error": "project not found"}), 404
    return jsonify(board)


# ── Task list / search ────────────────────────────────────────────────────────

@bp.route("/api/tasks", methods=["GET"])
def list_tasks():
    args = request.args
    label_param = args.get("label")
    labels = [l.strip() for l in label_param.split(",")] if label_param else None

    tasks = Task.list_tasks(
        get_db(),
        q=args.get("q"),
        project_id=args.get("project_id"),
        column_id=args.get("column_id"),
        labels=labels,
        priority=args.get("priority"),
        assignee=args.get("assignee"),
        due_before=args.get("due_before"),
        due_after=args.get("due_after"),
        sort=args.get("sort", "created_at"),
        order=args.get("order", "desc"),
    )
    return jsonify(tasks)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@bp.route("/api/tasks", methods=["POST"])
def create_task():
    db = get_db()
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    priority = data.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {sorted(VALID_PRIORITIES)}"}), 400

    # Resolve project
    project_id = data.get("project_id")
    if not project_id:
        project = Project.get_default(db)
        if not project:
            return jsonify({"error": "no project found"}), 400
        project_id = project["id"]

    # Resolve column
    column_id = data.get("column_id")
    if not column_id:
        col = Column.get_first_for_project(db, project_id)
        if not col:
            return jsonify({"error": "no columns found for project"}), 400
        column_id = col["id"]

    task = Task.create(
        db, project_id, column_id, title,
        description=data.get("description", ""),
        priority=priority,
        assignee=data.get("assignee"),
        due_date=data.get("due_date"),
    )
    # Activity "created" is logged inside Task.create()
    return jsonify(task), 201


@bp.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    task = Task.get_full(get_db(), task_id)
    if not task:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task)


@bp.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    db = get_db()
    existing = Task.get_by_id(db, task_id)
    if not existing:
        return jsonify({"error": "task not found"}), 404

    data = request.get_json(silent=True) or {}

    # Validate priority if present
    if "priority" in data and data["priority"] not in VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {sorted(VALID_PRIORITIES)}"}), 400

    # Validate title if present
    if "title" in data and not (data["title"] or "").strip():
        return jsonify({"error": "title cannot be empty"}), 400

    updatable = {k: v for k, v in data.items()
                 if k in {"title", "description", "priority", "assignee", "due_date"}}
    # Activity logging (priority/assignee changes) happens inside Task.update()
    task = Task.update(db, task_id, **updatable)
    return jsonify(task)


@bp.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    db = get_db()
    if not Task.get_by_id(db, task_id):
        return jsonify({"error": "task not found"}), 404
    Task.delete(db, task_id)
    return jsonify({"deleted": task_id})


# ── Move ──────────────────────────────────────────────────────────────────────

@bp.route("/api/tasks/<task_id>/move", methods=["PUT"])
def move_task(task_id):
    db = get_db()
    existing = Task.get_by_id(db, task_id)
    if not existing:
        return jsonify({"error": "task not found"}), 404

    data = request.get_json(silent=True) or {}
    column_id = data.get("column_id")
    if not column_id:
        return jsonify({"error": "column_id is required"}), 400

    target_col = Column.get_by_id(db, column_id)
    if not target_col:
        return jsonify({"error": "column not found"}), 404

    position = data.get("position", 0)
    # Activity logging (moved) happens inside Task.move()
    task = Task.move(db, task_id, column_id, position)
    return jsonify(task)
