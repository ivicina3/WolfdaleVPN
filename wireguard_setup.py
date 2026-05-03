import argparse
import shutil
import subprocess
from pathlib import Path


OUT_DIR = Path("wireguard-configs")


def has_wg_tools() -> bool:
    return shutil.which("wg") is not None


def run_wg_command(args, input_data=None):
    result = subprocess.run(
        args,
        input=input_data,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def generate_keypair():
    if not has_wg_tools():
        raise RuntimeError("WireGuard tools are required to generate keys. Install wireguard-tools.")

    private_key = run_wg_command(["wg", "genkey"])
    public_key = run_wg_command(["wg", "pubkey"], input_data=private_key)
    return private_key, public_key


def build_server_config(server_private_key, server_public_key, client_public_key, args):
    return f"""[Interface]
Address = {args.server_network_address}
ListenPort = {args.listen_port}
PrivateKey = {server_private_key}
SaveConfig = true
PostUp = sysctl -w net.ipv4.ip_forward=1; iptables -A FORWARD -i {args.interface} -j ACCEPT; iptables -A FORWARD -o {args.interface} -j ACCEPT; iptables -t nat -A POSTROUTING -o {args.public_interface} -j MASQUERADE
PostDown = iptables -D FORWARD -i {args.interface} -j ACCEPT; iptables -D FORWARD -o {args.interface} -j ACCEPT; iptables -t nat -D POSTROUTING -o {args.public_interface} -j MASQUERADE

[Peer]
PublicKey = {client_public_key}
AllowedIPs = {args.client_network_address}
"""


def build_client_config(client_private_key, server_public_key, args):
    return f"""[Interface]
PrivateKey = {client_private_key}
Address = {args.client_network_address}
DNS = {args.dns}

[Peer]
PublicKey = {server_public_key}
Endpoint = {args.public_ip}:{args.listen_port}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""


def save_config(path: Path, content: str):
    path.write_text(content, encoding="utf-8")
    print(f"Saved {path}")


def main():
    parser = argparse.ArgumentParser(description="WireGuard config generator for WolfdaleVPN")
    parser.add_argument("--public-ip", required=True, help="Публичный IP или домен сервера для Endpoint")
    parser.add_argument("--listen-port", type=int, default=51820, help="WireGuard порт на сервере")
    parser.add_argument("--client-name", default="client1", help="Имя конфигурации клиента")
    parser.add_argument("--server-network-address", default="10.8.0.1/24", help="VPN адрес сервера")
    parser.add_argument("--client-network-address", default="10.8.0.2/32", help="VPN адрес клиента")
    parser.add_argument("--dns", default="1.1.1.1", help="DNS для клиента")
    parser.add_argument("--interface", default="wg0", help="Имя WireGuard-интерфейса")
    parser.add_argument("--public-interface", default="eth0", help="Сетевой интерфейс сервера, через который идёт выход в интернет")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)

    if not has_wg_tools():
        raise SystemExit(
            "WireGuard tools not found. Установите wireguard-tools и повторите запуск. "
            "На Ubuntu: sudo apt update && sudo apt install wireguard"
        )

    server_private_key, server_public_key = generate_keypair()
    client_private_key, client_public_key = generate_keypair()

    server_conf = build_server_config(server_private_key, server_public_key, client_public_key, args)
    client_conf = build_client_config(client_private_key, server_public_key, args)

    save_config(OUT_DIR / f"server-{args.interface}.conf", server_conf)
    save_config(OUT_DIR / f"client-{args.client_name}.conf", client_conf)

    print("\nWireGuard configs сгенерированы.")
    print("На сервере:")
    print(f"  sudo cp {OUT_DIR / f'server-{args.interface}.conf'} /etc/wireguard/{args.interface}.conf")
    print(f"  sudo wg-quick up {args.interface}")
    print("На клиенте:")
    print(f"  используйте файл {OUT_DIR / f'client-{args.client_name}.conf'}")
    print("  импортируйте его в WireGuard-приложение или запустите wg-quick up client-<name>")
    print("\nПосле запуска на сервере весь клиентский трафик будет идти через сервер.")


if __name__ == "__main__":
    main()
