import json
import logging
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory

# ── Paths ────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_FILE = os.path.join(BASE_DIR, "tasks.json")
LOG_FILE = os.path.join(BASE_DIR, "tasks.log")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Flask app ────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=STATIC_DIR)

VALID_PRIORITIES = {"high", "medium", "low"}
VALID_STATUSES = {"todo", "in_progress", "done"}


# ── Storage helpers ──────────────────────────────────────────────────────────
def load_tasks() -> list:
    if not os.path.exists(TASKS_FILE):
        return []
    with open(TASKS_FILE, "r") as f:
        return json.load(f)


def save_tasks(tasks: list) -> None:
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── API routes ───────────────────────────────────────────────────────────────

@app.route("/api/tasks", methods=["GET"])
def get_tasks():
    tasks = load_tasks()
    log.info("GET /api/tasks  returned %d tasks", len(tasks))
    return jsonify(tasks)


@app.route("/api/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "title is required"}), 400

    priority = data.get("priority", "medium")
    if priority not in VALID_PRIORITIES:
        return jsonify({"error": f"priority must be one of {sorted(VALID_PRIORITIES)}"}), 400

    status = data.get("status", "todo")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    task = {
        "id": str(uuid.uuid4()),
        "title": title,
        "description": (data.get("description") or "").strip(),
        "priority": priority,
        "status": status,
        "comments": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    tasks = load_tasks()
    tasks.append(task)
    save_tasks(tasks)
    log.info("CREATE task id=%s title=%r priority=%s status=%s", task["id"], task["title"], task["priority"], task["status"])
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["GET"])
def get_task(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "task not found"}), 404
    return jsonify(task)


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def update_task(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    data = request.get_json(silent=True) or {}

    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            return jsonify({"error": "title cannot be empty"}), 400
        task["title"] = title

    if "description" in data:
        task["description"] = (data["description"] or "").strip()

    if "priority" in data:
        if data["priority"] not in VALID_PRIORITIES:
            return jsonify({"error": f"priority must be one of {sorted(VALID_PRIORITIES)}"}), 400
        task["priority"] = data["priority"]

    if "status" in data:
        if data["status"] not in VALID_STATUSES:
            return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400
        task["status"] = data["status"]

    task["updated_at"] = now_iso()
    save_tasks(tasks)
    log.info("UPDATE task id=%s title=%r priority=%s status=%s", task["id"], task["title"], task["priority"], task["status"])
    return jsonify(task)


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def delete_task(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks(tasks)
    log.info("DELETE task id=%s title=%r", task["id"], task["title"])
    return jsonify({"deleted": task_id})


# ── Comments API ─────────────────────────────────────────────────────────────

@app.route("/api/tasks/<task_id>/comments", methods=["POST"])
def add_comment(task_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    data = request.get_json(silent=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    comment = {
        "id": str(uuid.uuid4()),
        "text": text,
        "created_at": now_iso(),
    }

    if "comments" not in task:
        task["comments"] = []
    task["comments"].append(comment)
    task["updated_at"] = now_iso()
    save_tasks(tasks)
    log.info("COMMENT on task id=%s comment_id=%s", task_id, comment["id"])
    return jsonify(comment), 201


@app.route("/api/tasks/<task_id>/comments/<comment_id>", methods=["DELETE"])
def delete_comment(task_id, comment_id):
    tasks = load_tasks()
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    comments = task.get("comments", [])
    comment = next((c for c in comments if c["id"] == comment_id), None)
    if comment is None:
        return jsonify({"error": "comment not found"}), 404

    task["comments"] = [c for c in comments if c["id"] != comment_id]
    task["updated_at"] = now_iso()
    save_tasks(tasks)
    log.info("DELETE comment id=%s from task id=%s", comment_id, task_id)
    return jsonify({"deleted": comment_id})


# ── Frontend fallback ────────────────────────────────────────────────────────

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_frontend(path):
    static_dir = app.static_folder
    target = os.path.join(static_dir, path) if path else None
    if path and target and os.path.isfile(target):
        return send_from_directory(static_dir, path)
    index = os.path.join(static_dir, "index.html")
    if os.path.isfile(index):
        return send_from_directory(static_dir, "index.html")
    return jsonify({"status": "backend running — frontend not yet deployed"}), 200


# ── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(STATIC_DIR, exist_ok=True)
    if not os.path.exists(TASKS_FILE):
        save_tasks([])
        log.info("Initialised empty tasks.json")
    log.info("Starting Flask server on http://localhost:5051")
    app.run(debug=True, host="0.0.0.0", port=5051)
