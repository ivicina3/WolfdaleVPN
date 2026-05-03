from datetime import datetime
import ipaddress
import secrets
import subprocess
from pathlib import Path

from flask import Flask, jsonify, request

app = Flask(__name__)

clients = {}
tunnels = {}
next_vpn_address = ipaddress.IPv4Address("10.8.0.2")

WG_CONFIG_DIR = Path("wireguard-configs")
WG_CONFIG_DIR.mkdir(exist_ok=True)


def allocate_vpn_address():
    global next_vpn_address
    vpn_address = str(next_vpn_address)
    next_vpn_address += 1
    return vpn_address


def get_bearer_token():
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.split(" ", 1)[1].strip()
    return None


def find_client_by_token(token):
    for client in clients.values():
        if client["token"] == token:
            return client
    return None


def generate_wg_keys():
    try:
        private_key = subprocess.run(["wg", "genkey"], capture_output=True, text=True, check=True).stdout.strip()
        public_key = subprocess.run(["wg", "pubkey"], input=private_key, text=True, capture_output=True, check=True).stdout.strip()
        return private_key, public_key
    except subprocess.CalledProcessError:
        raise RuntimeError("WireGuard tools not available. Install wireguard-tools.")


def build_client_wg_config(client_private_key, server_public_key, client_vpn_ip, server_public_ip, server_port=51820):
    return f"""[Interface]
PrivateKey = {client_private_key}
Address = {client_vpn_ip}/32
DNS = 1.1.1.1

[Peer]
PublicKey = {server_public_key}
Endpoint = {server_public_ip}:{server_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""


@app.route("/api/register", methods=["POST"])
def register_client():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "Client name is required"}), 400

    client_id = secrets.token_hex(8)
    token = secrets.token_urlsafe(24)
    clients[client_id] = {
        "id": client_id,
        "name": name,
        "token": token,
        "created_at": datetime.utcnow().isoformat() + "Z",
        "last_seen": None,
        "status": "registered",
        "vpn_address": None,
    }

    return jsonify({
        "client_id": client_id,
        "token": token,
        "message": "VPN client registered successfully",
    }), 201


@app.route("/api/vpn-config", methods=["POST"])
def vpn_config():
    token = get_bearer_token()
    client = find_client_by_token(token)
    if client is None:
        return jsonify({"error": "Unauthorized"}), 401

    if client["vpn_address"] is None:
        client["vpn_address"] = allocate_vpn_address()
        tunnels[client["id"]] = {
            "client_id": client["id"],
            "vpn_address": client["vpn_address"],
            "network": "10.8.0.0/24",
            "dns": "10.8.0.1",
            "routes": ["0.0.0.0/0"],
            "pre_shared_key": secrets.token_urlsafe(16),
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

    client["last_seen"] = datetime.utcnow().isoformat() + "Z"
    client["status"] = "configured"

    return jsonify({
        "client_id": client["id"],
        "vpn_address": client["vpn_address"],
        "network": tunnels[client["id"]]["network"],
        "dns": tunnels[client["id"]]["dns"],
        "routes": tunnels[client["id"]]["routes"],
        "pre_shared_key": tunnels[client["id"]]["pre_shared_key"],
    })


@app.route("/api/wireguard-config", methods=["POST"])
def wireguard_config():
    token = get_bearer_token()
    client = find_client_by_token(token)
    if client is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    server_public_ip = data.get("server_public_ip")
    server_port = data.get("server_port", 51820)

    if not server_public_ip:
        return jsonify({"error": "server_public_ip is required"}), 400

    try:
        client_private_key, client_public_key = generate_wg_keys()
        server_private_key, server_public_key = generate_wg_keys()
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 500

    client_vpn_ip = client.get("vpn_address") or allocate_vpn_address()
    client["vpn_address"] = client_vpn_ip

    client_config = build_client_wg_config(client_private_key, server_public_key, client_vpn_ip, server_public_ip, server_port)

    # Save server config for admin
    server_config = f"""[Interface]
Address = 10.8.0.1/24
ListenPort = {server_port}
PrivateKey = {server_private_key}
SaveConfig = true
PostUp = sysctl -w net.ipv4.ip_forward=1; iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = {client_public_key}
AllowedIPs = {client_vpn_ip}/32
"""

    server_config_path = WG_CONFIG_DIR / f"server-{client['id']}.conf"
    server_config_path.write_text(server_config)

    return jsonify({
        "client_config": client_config,
        "server_config_path": str(server_config_path),
        "message": "WireGuard configs generated. Apply server config manually.",
    })


@app.route("/api/status", methods=["POST"])
def update_status():
    token = get_bearer_token()
    client = find_client_by_token(token)
    if client is None:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if not status:
        return jsonify({"error": "status field is required"}), 400

    client["status"] = status
    client["last_seen"] = datetime.utcnow().isoformat() + "Z"

    return jsonify({"message": "Status updated", "client": client})


@app.route("/api/clients", methods=["GET"])
def list_clients():
    return jsonify({"clients": list(clients.values())})


@app.route("/api/disconnect", methods=["POST"])
def disconnect_client():
    token = get_bearer_token()
    client = find_client_by_token(token)
    if client is None:
        return jsonify({"error": "Unauthorized"}), 401

    client["status"] = "disconnected"
    client["last_seen"] = datetime.utcnow().isoformat() + "Z"

    if client["id"] in tunnels:
        del tunnels[client["id"]]

    return jsonify({"message": "Client disconnected", "client_id": client["id"]})


@app.route("/api/ping", methods=["GET"])
def ping():
    return jsonify({"message": "WolfdaleVPN API is alive"})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WolfdaleVPN API server")
    parser.add_argument("--host", default="0.0.0.0", help="Host address to bind")
    parser.add_argument("--port", type=int, default=5000, help="Port to listen on")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    args = parser.parse_args()

    app.run(host=args.host, port=args.port, debug=args.debug)
