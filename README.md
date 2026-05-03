# WolfdaleVPN

Минимальный API для управления VPN-сессиями между сервером и клиентом.

## Установка

1. Установите зависимости:

```bash
python -m pip install -r requirements.txt
```

2. Запустите сервер:

```bash
python server.py
```

3. В другом окне терминала используйте клиент:

```bash
python client.py health
python client.py servers
python client.py connect --username user1 --password password123 --server us-east
python client.py list
python client.py session --session-id <ID>
python client.py disconnect --session-id <ID>
```

### Удалённое подключение

Если сервер запущен на удалённой машине или домене, укажите URL сервера:

```bash
python client.py --server-url http://vpn.example.com:5000 connect --username user1 --password password123 --server us-east
```

Или настройте домен, который резолвится на удалённый сервер, и используйте его:

```bash
python client.py --server-url https://myvpn.example.com connect --username user1 --password password123 --server us-east
```

Если сервер запускается локально на публичном интерфейсе, укажите хост при старте:

```bash
python server.py --host 0.0.0.0 --port 5000
```

## Описание API

- `POST /api/v1/sessions/connect` — создать VPN-сессию и получить VPN-IP
- `POST /api/v1/sessions/disconnect` — завершить VPN-сессию
- `GET /api/v1/sessions` — список активных сессий
- `GET /api/v1/sessions/<session_id>` — подробности сессии
- `GET /api/v1/servers` — доступные VPN-серверы
- `GET /api/v1/health` — проверка работоспособности

## Команды клиента

- `connect` — подключиться к VPN и получить VPN-IP адрес
- `disconnect` — отключиться от VPN
- `vpn-ip` — показать текущий VPN-IP адрес (из локального состояния)
- `show` — показать всё локальное состояние клиента
- `servers` — список доступных серверов
- `list` — список всех сессий на сервере
- `health` — проверить здоровье сервера

## Как использовать

После подключения VPN-IP автоматически сохраняется в локальное состояние:

```bash
python client.py connect --username user1 --password password123 --server us-east
python client.py vpn-ip
python client.py disconnect
```
