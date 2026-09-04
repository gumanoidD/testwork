# Telegram Pulse Service

Сервіс аналітики публічних Telegram-каналів без використання Telegram API tokens.

## Можливості
- Автоматичний парсинг публічних веб-сторінок Telegram (`https://t.me/s/...`).
- Збереження історій переглядів у SQLite.
- REST API для перегляду списку каналів, постів та аналітики за медіаною переглядів.
- Повна автономність у Docker.

## Запуск через Docker Compose
```bash
docker-compose up --build