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

## Описание API

- `POST /api/v1/sessions/connect` — создать VPN-сессию
- `POST /api/v1/sessions/disconnect` — завершить VPN-сессию
- `GET /api/v1/sessions` — список активных сессий
- `GET /api/v1/sessions/<session_id>` — подробности сессии
- `GET /api/v1/servers` — доступные VPN-серверы
- `GET /api/v1/health` — проверка работоспособности

## Пример пользователя

- Логин: `user1`
- Пароль: `password123`
