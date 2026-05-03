import argparse
import json
import os
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:5000"
STATE_FILE = Path("vpn_client_state.json")


def save_state(state):
    with STATE_FILE.open("w", encoding="utf-8") as file:
        json.dump(state, file, indent=2)


def load_state():
    if not STATE_FILE.exists():
        return {}
    with STATE_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def request_json(method, path, json_data=None):
    url = f"{BASE_URL}{path}"
    try:
        response = requests.request(method, url, json=json_data)
        response.raise_for_status()
    except requests.RequestException as exc:
        print(f"Error connecting to server: {exc}")
        raise SystemExit(1)

    try:
        payload = response.json()
    except ValueError:
        print(f"Invalid JSON response from server: {response.text}")
        raise SystemExit(1)

    if response.status_code >= 400 or payload.get("status") == "error":
        print(f"Request failed: {payload.get('message') or response.status_code}")
        raise SystemExit(1)

    return payload.get("data")


def cmd_health(args):
    data = request_json("GET", "/api/v1/health")
    print("Server health:")
    print(json.dumps(data, indent=2))


def cmd_servers(args):
    data = request_json("GET", "/api/v1/servers")
    print("Available VPN servers:")
    for server in data["servers"]:
        print(f"- {server['id']} ({server['location']}) -> {server['ip']}")


def cmd_connect(args):
    payload = {
        "username": args.username,
        "password": args.password,
        "server_id": args.server,
    }
    data = request_json("POST", "/api/v1/sessions/connect", json_data=payload)
    session = data["session"]

    state = load_state()
    state["session_id"] = session["session_id"]
    state["vpn_ip"] = session["assigned_ip"]
    state["server_id"] = session["server_id"]
    state["status"] = "connected"
    save_state(state)

    print("Connected VPN session:")
    print(f"  session_id: {session['session_id']}")
    print(f"  username: {session['username']}")
    print(f"  server: {session['server_id']}")
    print(f"  vpn_ip: {session['assigned_ip']}")


def cmd_disconnect(args):
    state = load_state()
    session_id = state.get("session_id") or (args.session_id if hasattr(args, 'session_id') else None)
    if not session_id:
        raise SystemExit("No session found. Use --session-id or connect first.")

    payload = {"session_id": session_id}
    data = request_json("POST", "/api/v1/sessions/disconnect", json_data=payload)
    session = data["session"]

    state["status"] = "disconnected"
    state.pop("vpn_ip", None)
    state.pop("session_id", None)
    save_state(state)

    print(f"Disconnected session {session['session_id']}")


def cmd_session(args):
    state = load_state()
    session_id = state.get("session_id") or (args.session_id if hasattr(args, 'session_id') else None)
    if not session_id:
        raise SystemExit("No session found. Use --session-id or connect first.")

    path = f"/api/v1/sessions/{session_id}"
    data = request_json("GET", path)
    session = data["session"]
    print("Session details:")
    print(json.dumps(session, indent=2))


def cmd_list(args):
    data = request_json("GET", "/api/v1/sessions")
    print("All sessions:")
    for session in data["sessions"]:
        print(f"- {session['session_id']} | {session['username']} | {session['status']} | {session['server_id']}")


def cmd_show_state(args):
    state = load_state()
    if not state:
        print("No client state file found.")
        return
    print(json.dumps(state, indent=2))


def cmd_wireguard_config(args):
    state = load_state()
    token = state.get("token")
    if not token:
        raise SystemExit("Client is not registered. Run 'register' first.")

    payload = {
        "server_public_ip": args.server_public_ip,
        "server_port": args.server_port or 51820,
    }
    data = request_json("POST", "/api/wireguard-config", json_data=payload)

    client_config = data["client_config"]
    config_path = Path(f"wg-{state['name']}.conf")
    config_path.write_text(client_config, encoding="utf-8")

    print(f"WireGuard config saved to {config_path}")
    print("To connect automatically, run: wg-quick up " + str(config_path))

    # Optional: auto-connect if --connect flag
    if args.connect:
        try:
            import subprocess
            result = subprocess.run(["wg-quick", "up", str(config_path)], capture_output=True, text=True)
            if result.returncode == 0:
                print("WireGuard connected successfully!")
            else:
                print(f"Failed to connect: {result.stderr}")
        except FileNotFoundError:
            print("wg-quick not found. Install WireGuard and try again.")


def main():
    parser = argparse.ArgumentParser(description="WolfdaleVPN client API demo")
    parser.add_argument(
        "--server-url",
        default=os.environ.get("WOLFDALEVPN_SERVER_URL", "http://127.0.0.1:5000"),
        help="Remote VPN API server URL (example: http://vpn.example.com:5000)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="Check server health")
    subparsers.add_parser("servers", help="List available VPN servers")
    subparsers.add_parser("list", help="List all VPN sessions")

    connect = subparsers.add_parser("connect", help="Open a VPN session")
    connect.add_argument("--username", required=True, help="VPN username")
    connect.add_argument("--password", required=True, help="VPN password")
    connect.add_argument("--server", required=True, help="Server ID to connect to")

    disconnect = subparsers.add_parser("disconnect", help="Close a VPN session")
    disconnect.add_argument("--session-id", help="Session ID (optional, uses saved state)")

    session = subparsers.add_parser("session", help="Inspect a VPN session")
    session.add_argument("--session-id", help="Session ID (optional, uses saved state)")

    subparsers.add_parser("show", help="Show saved client state")
    subparsers.add_parser("vpn-ip", help="Show your current VPN IP address")

    wg_config = subparsers.add_parser("wg-config", help="Get WireGuard config from server")
    wg_config.add_argument("--server-public-ip", required=True, help="Public IP of the WireGuard server")
    wg_config.add_argument("--server-port", type=int, default=51820, help="WireGuard port")
    wg_config.add_argument("--connect", action="store_true", help="Automatically connect after getting config")

    args = parser.parse_args()
    global BASE_URL
    BASE_URL = args.server_url.rstrip("/")

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
    elif args.command == "show":
        cmd_show_state(args)
    elif args.command == "vpn-ip":
        cmd_vpn_ip(args)
    elif args.command == "wg-config":
        cmd_wireguard_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
