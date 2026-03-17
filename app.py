"""
app.py — Kanbn Flask application entry point.

Registers blueprints, manages the SQLite connection lifecycle via Flask g,
and serves the static SPA frontend.
"""
import logging
import os

from flask import Flask, g, jsonify, send_from_directory

from db import DB_PATH, get_connection, init_db, migrate_from_json, ensure_default_project

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "tasks.log")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=STATIC_DIR)


# ── Database connection lifecycle ─────────────────────────────────────────────

def get_db():
    """Return the per-request SQLite connection, creating it on first access."""
    if "db" not in g:
        g.db = get_connection()
    return g.db


@app.before_request
def _ensure_db():
    """Lazily open a per-request SQLite connection so route get_db() can return g.db."""
    if "db" not in g:
        g.db = get_connection()


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ── Register blueprints ───────────────────────────────────────────────────────

from routes.projects import bp as projects_bp
from routes.columns import bp as columns_bp
from routes.tasks import bp as tasks_bp
from routes.labels import bp as labels_bp
from routes.subtasks import bp as subtasks_bp
from routes.comments import bp as comments_bp
from routes.analytics import bp as analytics_bp

app.register_blueprint(projects_bp)
app.register_blueprint(columns_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(labels_bp)
app.register_blueprint(subtasks_bp)
app.register_blueprint(comments_bp)
app.register_blueprint(analytics_bp)


# ── Frontend fallback ─────────────────────────────────────────────────────────

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
    return jsonify({"status": "Kanbn backend running — frontend not deployed yet"}), 200


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    os.makedirs(STATIC_DIR, exist_ok=True)

    # Initialise schema (idempotent)
    init_db()

    # One-time migration from tasks.json if it exists
    migrate_from_json()

    # Create default project if DB is empty
    ensure_default_project()

    port = int(os.environ.get("KANBN_PORT", 5051))
    log.info("Starting Kanbn on http://localhost:%d", port)
    app.run(debug=True, host="0.0.0.0", port=port)
