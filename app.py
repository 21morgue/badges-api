import json
import os
import secrets
from pathlib import Path
from flask import Flask, jsonify, request

APP_DIR = Path(__file__).resolve().parent
DATA_FILE = APP_DIR / "badges.json"
ADMIN_HTML_FILE = APP_DIR / "admin.html"
ADMIN_KEY = "1337"

app = Flask(__name__)


@app.route("/admin", methods=["GET"])
def admin_page():
    try:
        with open(ADMIN_HTML_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "admin.html not found", 404


def _load():
    if not DATA_FILE.exists():
        return {}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _authorized(req):
    if not ADMIN_KEY:
        return False
    return req.headers.get("Authorization", "") == f"Bearer {ADMIN_KEY}"


@app.route("/api/v1/badges", methods=["GET"])
def list_all_badges():
    if not _authorized(request):
        return jsonify({"success": False, "error": "unauthorized"}), 401
    return jsonify({"success": True, "users": _load()})


@app.route("/api/v1/badges/<user_id>", methods=["GET"])
def get_badges(user_id):
    data = _load()
    return jsonify({"success": True, "badges": data.get(user_id, [])})


@app.route("/api/v1/badges/<user_id>", methods=["POST"])
def add_badge(user_id):
    if not _authorized(request):
        return jsonify({"success": False, "error": "unauthorized"}), 401
    payload = request.get_json(force=True, silent=True) or {}
    icon = payload.get("icon")
    name = payload.get("name", "")
    if not icon:
        return jsonify({"success": False, "error": "icon is required"}), 400
    data = _load()
    user_badges = data.setdefault(user_id, [])
    badge = {"id": secrets.token_hex(4), "icon": icon, "name": name}
    user_badges.append(badge)
    _save(data)
    return jsonify({"success": True, "badge": badge})


@app.route("/api/v1/badges/<user_id>/<badge_id>", methods=["DELETE"])
def delete_badge(user_id, badge_id):
    if not _authorized(request):
        return jsonify({"success": False, "error": "unauthorized"}), 401
    data = _load()
    user_badges = data.get(user_id, [])
    remaining = [b for b in user_badges if b.get("id") != badge_id]
    if len(remaining) == len(user_badges):
        return jsonify({"success": False, "error": "badge not found"}), 404
    data[user_id] = remaining
    _save(data)
    return jsonify({"success": True})


@app.route("/api/v1/badges/<user_id>", methods=["DELETE"])
def clear_badges(user_id):
    if not _authorized(request):
        return jsonify({"success": False, "error": "unauthorized"}), 401
    data = _load()
    data.pop(user_id, None)
    _save(data)
    return jsonify({"success": True})


if __name__ == "__main__":
    if not ADMIN_KEY:
        print("[WARNING] BADGES_ADMIN_KEY is not set - badge write endpoints are disabled until you set it.")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port)
