"""Blueprint: /api/labels and /api/tasks/:id/labels/:label_id"""
from flask import Blueprint, g, jsonify, request
import models.label as Label
import models.task as Task
import models.project as Project
import models.activity as Activity

bp = Blueprint("labels", __name__)


def get_db():
    return g.db


@bp.route("/api/labels", methods=["GET"])
def list_labels():
    labels = Label.get_all(get_db(), project_id=request.args.get("project_id"))
    return jsonify(labels)


@bp.route("/api/labels", methods=["POST"])
def create_label():
    db = get_db()
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    project_id = data.get("project_id")
    if not project_id:
        project = Project.get_default(db)
        if not project:
            return jsonify({"error": "no project found"}), 400
        project_id = project["id"]
    label = Label.create(db, project_id, name, color=data.get("color", "#7A9090"))
    return jsonify(label), 201


@bp.route("/api/labels/<label_id>", methods=["PUT"])
def update_label(label_id):
    data = request.get_json(silent=True) or {}
    label = Label.update(get_db(), label_id, name=data.get("name"), color=data.get("color"))
    if not label:
        return jsonify({"error": "label not found"}), 404
    return jsonify(label)


@bp.route("/api/labels/<label_id>", methods=["DELETE"])
def delete_label(label_id):
    deleted = Label.delete(get_db(), label_id)
    if not deleted:
        return jsonify({"error": "label not found"}), 404
    return jsonify({"deleted": label_id})


# ── Task-label attach / detach ────────────────────────────────────────────────

@bp.route("/api/tasks/<task_id>/labels/<label_id>", methods=["POST"])
def attach_label(task_id, label_id):
    db = get_db()
    if not Task.get_by_id(db, task_id):
        return jsonify({"error": "task not found"}), 404
    if not Label.get_by_id(db, label_id):
        return jsonify({"error": "label not found"}), 404
    # Activity logged + committed inside Label.attach()
    Label.attach(db, task_id, label_id)
    return jsonify({"task_id": task_id, "label_id": label_id}), 201


@bp.route("/api/tasks/<task_id>/labels/<label_id>", methods=["DELETE"])
def detach_label(task_id, label_id):
    db = get_db()
    if not Task.get_by_id(db, task_id):
        return jsonify({"error": "task not found"}), 404
    if not Label.get_by_id(db, label_id):
        return jsonify({"error": "label not found"}), 404
    # Activity logged + committed inside Label.detach()
    Label.detach(db, task_id, label_id)
    return jsonify({"deleted": True})
