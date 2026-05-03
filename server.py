from flask import Flask, jsonify, request
from uuid import uuid4
from datetime import datetime

app = Flask(__name__)

VPN_SERVERS = [
    {"id": "us-east", "location": "US East", "ip": "192.168.100.1"},
    {"id": "eu-central", "location": "EU Central", "ip": "192.168.100.2"},
    {"id": "asia-south", "location": "Asia South", "ip": "192.168.100.3"},
]

sessions = {}

VALID_USERS = {
    "user1": "password123",
    "admin": "adminpass",
}


def make_response(status, data=None, message=None, code=200):
    payload = {"status": status}
    if data is not None:
        payload["data"] = data
    if message is not None:
        payload["message"] = message
    return jsonify(payload), code


@app.route("/api/v1/health", methods=["GET"])
def health_check():
    return make_response("ok", {"time": datetime.utcnow().isoformat() + "Z"})


@app.route("/api/v1/servers", methods=["GET"])
def list_servers():
    return make_response("ok", {"servers": VPN_SERVERS})


@app.route("/api/v1/sessions", methods=["GET"])
def list_sessions():
    return make_response("ok", {"sessions": list(sessions.values())})


@app.route("/api/v1/sessions/<session_id>", methods=["GET"])
def get_session(session_id):
    session = sessions.get(session_id)
    if not session:
        return make_response("error", message="Session not found", code=404)
    return make_response("ok", {"session": session})


@app.route("/api/v1/sessions/connect", methods=["POST"])
def connect():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return make_response("error", message="JSON payload required", code=400)

    username = payload.get("username")
    password = payload.get("password")
    server_id = payload.get("server_id")

    if not username or not password or not server_id:
        return make_response("error", message="username, password and server_id are required", code=400)

    expected_password = VALID_USERS.get(username)
    if expected_password != password:
        return make_response("error", message="Invalid username or password", code=401)

    target_server = next((s for s in VPN_SERVERS if s["id"] == server_id), None)
    if not target_server:
        return make_response("error", message="Unknown server_id", code=404)

    session_id = str(uuid4())
    session = {
        "session_id": session_id,
        "username": username,
        "server_id": server_id,
        "server": target_server,
        "status": "connected",
        "assigned_ip": f"10.8.0.{len(sessions) + 10}",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
    }
    sessions[session_id] = session

    return make_response("ok", {"session": session}, message="VPN session connected")


@app.route("/api/v1/sessions/disconnect", methods=["POST"])
def disconnect():
    payload = request.get_json(force=True, silent=True)
    if not payload:
        return make_response("error", message="JSON payload required", code=400)

    session_id = payload.get("session_id")
    if not session_id:
        return make_response("error", message="session_id is required", code=400)

    session = sessions.get(session_id)
    if not session:
        return make_response("error", message="Session not found", code=404)

    session["status"] = "disconnected"
    session["updated_at"] = datetime.utcnow().isoformat() + "Z"
    return make_response("ok", {"session": session}, message="VPN session disconnected")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WolfdaleVPN API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
