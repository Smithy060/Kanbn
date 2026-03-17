"""Blueprint: /api/projects/:id/columns and /api/columns/:id"""
from flask import Blueprint, g, jsonify, request
import models.column as Column
import models.project as Project

bp = Blueprint("columns", __name__)


def get_db():
    return g.db


# ── Nested under /api/projects/:project_id/columns ───────────────────────────

@bp.route("/api/projects/<project_id>/columns", methods=["GET"])
def list_columns(project_id):
    if not Project.get_by_id(get_db(), project_id):
        return jsonify({"error": "project not found"}), 404
    columns = Column.get_for_project(get_db(), project_id)
    return jsonify(columns)


@bp.route("/api/projects/<project_id>/columns", methods=["POST"])
def create_column(project_id):
    if not Project.get_by_id(get_db(), project_id):
        return jsonify({"error": "project not found"}), 404
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    col = Column.create(
        get_db(), project_id, name,
        color=data.get("color"),
        wip_limit=data.get("wip_limit"),
    )
    return jsonify(col), 201


@bp.route("/api/projects/<project_id>/columns/reorder", methods=["PUT"])
def reorder_columns(project_id):
    if not Project.get_by_id(get_db(), project_id):
        return jsonify({"error": "project not found"}), 404
    data = request.get_json(silent=True) or {}
    order = data.get("order")
    if not isinstance(order, list):
        return jsonify({"error": "order must be a list of column IDs"}), 400
    columns = Column.reorder(get_db(), project_id, order)
    return jsonify(columns)


# ── /api/columns/:id ──────────────────────────────────────────────────────────

@bp.route("/api/columns/<column_id>", methods=["PUT"])
def update_column(column_id):
    data = request.get_json(silent=True) or {}
    col = Column.update(
        get_db(), column_id,
        name=data.get("name"),
        color=data.get("color"),
        wip_limit=data.get("wip_limit"),
    )
    if not col:
        return jsonify({"error": "column not found"}), 404
    return jsonify(col)


@bp.route("/api/columns/<column_id>", methods=["DELETE"])
def delete_column(column_id):
    if not Column.get_by_id(get_db(), column_id):
        return jsonify({"error": "column not found"}), 404
    deleted, reason = Column.delete(get_db(), column_id)
    if not deleted:
        if reason == "has_tasks":
            return jsonify({"error": "column has tasks — move them first"}), 409
        return jsonify({"error": "delete failed"}), 500
    return jsonify({"deleted": column_id})
