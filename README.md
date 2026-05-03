# WolfdaleVPN

Простой VPN-проект с API-управлением и генерацией WireGuard-конфигураций.

## Быстрый старт

1. Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

2. Запустите API-сервер:

```bash
python server.py --host 0.0.0.0 --port 5000
```

3. Подключитесь клиентом к API:

```bash
python client.py connect --username user1 --password password123 --server us-east
```

4. Посмотрите текущий сохранённый VPN-IP:

```bash
python client.py vpn-ip
```

5. Отключитесь:

```bash
python client.py disconnect
```

## Удалённый сервер

Если сервер доступен по публичному IP или домену:

```bash
python client.py --server-url http://<PUBLIC_IP>:5000 connect --username user1 --password password123 --server us-east
```

## WireGuard

Генерация реального WireGuard-конфига (запускайте на сервере, где установлен WireGuard):

```bash
python wireguard_setup.py --public-ip <PUBLIC_IP_OR_DOMAIN> --client-name client1
```

Или получить конфигурацию через API (автоматически):

```bash
python client.py wg-config --server-public-ip <PUBLIC_IP> --connect
```

Затем на сервере:

```bash
sudo cp wireguard-configs/server-wg0.conf /etc/wireguard/wg0.conf
sudo wg-quick up wg0
```

На клиенте:

```bash
sudo wg-quick up wg-client1.conf
```

### Копирование конфигурации с сервера на клиент

Если сервер на Ubuntu, а клиент на Windows/Linux/Mac, используйте SCP (через SSH):

На клиенте (в терминале или PowerShell):

```bash
scp user@server_ip:/path/to/wireguard-configs/client-client1.conf .
```

Или, если у вас есть SSH-доступ:

```bash
scp ubuntu@your-server-ip:~/WolfdaleVPN/wireguard-configs/client-client1.conf .
```

Затем импортируйте файл в WireGuard-приложение на клиенте.

## Важно

- WireGuard нужен только для реального туннеля.
- API-сервер управляет только сессиями.
- Для выхода в интернет через сервер на нём должен быть открыт порт `51820` и включён IP-форвардинг.
