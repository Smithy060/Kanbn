"""Blueprint: /api/tasks/:id/subtasks and /api/subtasks/:id"""
from flask import Blueprint, g, jsonify, request
import models.subtask as Subtask
import models.task as Task

bp = Blueprint("subtasks", __name__)


def get_db():
    return g.db


@bp.route("/api/tasks/<task_id>/subtasks", methods=["GET"])
def list_subtasks(task_id):
    if not Task.get_by_id(get_db(), task_id):
        return jsonify({"error": "task not found"}), 404
    return jsonify(Subtask.get_for_task(get_db(), task_id))


@bp.route("/api/tasks/<task_id>/subtasks", methods=["POST"])
def create_subtask(task_id):
    if not Task.get_by_id(get_db(), task_id):
        return jsonify({"error": "task not found"}), 404
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400
    subtask = Subtask.create(get_db(), task_id, title)
    return jsonify(subtask), 201


@bp.route("/api/subtasks/<subtask_id>", methods=["PUT"])
def update_subtask(subtask_id):
    data = request.get_json(silent=True) or {}
    # Subtask.update() logs subtask_toggled activity internally if completed changes
    subtask = Subtask.update(
        get_db(), subtask_id,
        title=data.get("title"),
        completed=data.get("completed"),
        position=data.get("position"),
    )
    if not subtask:
        return jsonify({"error": "subtask not found"}), 404
    return jsonify(subtask)


@bp.route("/api/subtasks/<subtask_id>", methods=["DELETE"])
def delete_subtask(subtask_id):
    deleted = Subtask.delete(get_db(), subtask_id)
    if not deleted:
        return jsonify({"error": "subtask not found"}), 404
    return jsonify({"deleted": subtask_id})
