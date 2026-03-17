"""Blueprint: /api/tasks/:id/comments and /api/comments/:id"""
from flask import Blueprint, g, jsonify, request
import models.comment as Comment
import models.task as Task

bp = Blueprint("comments", __name__)


def get_db():
    return g.db


@bp.route("/api/tasks/<task_id>/comments", methods=["GET"])
def list_comments(task_id):
    if not Task.get_by_id(get_db(), task_id):
        return jsonify({"error": "task not found"}), 404
    return jsonify(Comment.get_for_task(get_db(), task_id))


@bp.route("/api/tasks/<task_id>/comments", methods=["POST"])
def add_comment(task_id):
    if not Task.get_by_id(get_db(), task_id):
        return jsonify({"error": "task not found"}), 404
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    author = data.get("author", "User")
    comment = Comment.create(get_db(), task_id, text, author=author)
    return jsonify(comment), 201


@bp.route("/api/comments/<comment_id>", methods=["PUT"])
def update_comment(comment_id):
    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400
    comment = Comment.update(get_db(), comment_id, text)
    if not comment:
        return jsonify({"error": "comment not found"}), 404
    return jsonify(comment)


@bp.route("/api/comments/<comment_id>", methods=["DELETE"])
def delete_comment(comment_id):
    deleted = Comment.delete(get_db(), comment_id)
    if not deleted:
        return jsonify({"error": "comment not found"}), 404
    return jsonify({"deleted": comment_id})
