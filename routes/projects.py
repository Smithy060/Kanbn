"""Blueprint: /api/projects"""
from flask import Blueprint, g, jsonify, request
import models.project as Project

bp = Blueprint("projects", __name__, url_prefix="/api/projects")


def get_db():
    return g.db


@bp.route("", methods=["GET"])
def list_projects():
    projects = Project.get_all(get_db())
    return jsonify(projects)


@bp.route("", methods=["POST"])
def create_project():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    project = Project.create(get_db(), name, data.get("description", ""))
    return jsonify(project), 201


@bp.route("/<project_id>", methods=["GET"])
def get_project(project_id):
    project = Project.get_by_id(get_db(), project_id)
    if not project:
        return jsonify({"error": "project not found"}), 404
    return jsonify(project)


@bp.route("/<project_id>", methods=["PUT"])
def update_project(project_id):
    data = request.get_json(silent=True) or {}
    project = Project.update(
        get_db(), project_id,
        name=data.get("name"),
        description=data.get("description"),
    )
    if not project:
        return jsonify({"error": "project not found"}), 404
    return jsonify(project)


@bp.route("/<project_id>", methods=["DELETE"])
def delete_project(project_id):
    deleted = Project.delete(get_db(), project_id)
    if not deleted:
        return jsonify({"error": "project not found"}), 404
    return jsonify({"deleted": project_id})
