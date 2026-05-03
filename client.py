import argparse
import requests
import sys

API_BASE = "http://127.0.0.1:5000/api/v1"


def request_json(method, path, json=None):
    url = f"{API_BASE}{path}"
    try:
        response = requests.request(method, url, json=json, timeout=10)
    except requests.RequestException as exc:
        print(f"Error connecting to server: {exc}")
        sys.exit(1)

    try:
        payload = response.json()
    except ValueError:
        print(f"Invalid JSON response from server: {response.text}")
        sys.exit(1)

    if response.status_code >= 400 or payload.get("status") == "error":
        print(f"Request failed: {payload.get('message') or response.status_code}")
        sys.exit(1)

    return payload.get("data")


def cmd_health(args):
    data = request_json("GET", "/health")
    print("Server health:")
    print(data)


def cmd_servers(args):
    data = request_json("GET", "/servers")
    print("Available VPN servers:")
    for server in data["servers"]:
        print(f"- {server['id']} ({server['location']}) -> {server['ip']}")


def cmd_connect(args):
    payload = {
        "username": args.username,
        "password": args.password,
        "server_id": args.server,
    }
    data = request_json("POST", "/sessions/connect", json=payload)
    session = data["session"]
    print("Connected VPN session:")
    print(f"session_id: {session['session_id']}")
    print(f"username: {session['username']}")
    print(f"server: {session['server_id']}")
    print(f"assigned_ip: {session['assigned_ip']}")


def cmd_disconnect(args):
    payload = {"session_id": args.session_id}
    data = request_json("POST", "/sessions/disconnect", json=payload)
    session = data["session"]
    print(f"Disconnected session {session['session_id']}")


def cmd_session(args):
    path = f"/sessions/{args.session_id}"
    data = request_json("GET", path)
    session = data["session"]
    print("Session details:")
    for key, value in session.items():
        print(f"{key}: {value}")


def cmd_list(args):
    data = request_json("GET", "/sessions")
    print("All sessions:")
    for session in data["sessions"]:
        print(f"- {session['session_id']} | {session['username']} | {session['status']} | {session['server_id']}")


def main():
    parser = argparse.ArgumentParser(description="VPN API client")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check server health")
    subparsers.add_parser("servers", help="List available VPN servers")
    subparsers.add_parser("list", help="List all VPN sessions")

    connect = subparsers.add_parser("connect", help="Open a VPN session")
    connect.add_argument("--username", required=True, help="VPN username")
    connect.add_argument("--password", required=True, help="VPN password")
    connect.add_argument("--server", required=True, help="Server ID to connect to")

    disconnect = subparsers.add_parser("disconnect", help="Close a VPN session")
    disconnect.add_argument("--session-id", required=True, help="Session ID")

    session = subparsers.add_parser("session", help="Inspect a VPN session")
    session.add_argument("--session-id", required=True, help="Session ID")

    args = parser.parse_args()
    if args.command == "health":
        cmd_health(args)
    elif args.command == "servers":
        cmd_servers(args)
    elif args.command == "connect":
        cmd_connect(args)
    elif args.command == "disconnect":
        cmd_disconnect(args)
    elif args.command == "session":
        cmd_session(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
