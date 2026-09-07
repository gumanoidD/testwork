# Guidelines for Claude Code / Agents

## Architecture & layer boundaries
- `app/scraper.py` — HTTP-запросы к `t.me/s/<channel>` и парсинг HTML. Ничего не знает
  про FastAPI, Pydantic-схемы или HTTP-ответы API. На вход — HTML/channel, на выход —
  записи в БД через SQLAlchemy Session.
- `app/api.py` — только HTTP-слой (FastAPI роуты, Pydantic-схемы, сериализация).
  Не парсит HTML и не делает сетевые запросы напрямую.
- `app/models.py` — только ORM-модели (`Post`, `PostMetric`). Никакой бизнес-логики.
- `app/database.py` — engine/session/Base. Не трогать без крайней необходимости —
  меняется вместе с alembic-миграциями.
- `app/cli.py` — точка входа для ручного/крон-запуска сборщика. Тонкая обёртка над
  `scraper.fetch_channel_data`, без своей логики парсинга.

## Что не трогать без ADR
- Схему `posts` + `post_metrics` (см. `docs/adr/001-metrics-storage.md`). Переход на
  другую модель хранения истории `views` — дорогая миграция данных, обсуждать отдельно.
- `UniqueConstraint(channel, message_id)` в `posts` — на нём держится идемпотентность
  `collect`. Убирать/менять только вместе с логикой upsert в `scraper.py`.

## Уже принятые решения (и почему)
- **Медиана вместо абсолютных views** в `/channels/{name}/top` — чтобы маленький канал
  не терялся на фоне канала-миллионника. См. ADR-001.
- **Отдельная таблица `post_metrics`** вместо перезаписи `views` в `posts` — чтобы
  видеть динамику просмотров во времени, а не только последнее значение.
- **SQLite** вместо Postgres — сервис внутренний, объём данных небольшой, не стоит
  усложнять `docker-compose.yml` лишним контейнером БД.
- **Без очередей/Celery** — фоновый сбор реализован простым `asyncio`-циклом в
  `run.py` (`run_scraper_loop`), этого достаточно при текущей частоте опроса.
- **Инкремент = только первая страница `t.me/s/<channel>`.** Осознанное упрощение:
  предполагается, что `collect` без `--backfill` запускается достаточно часто, чтобы
  не пропускать посты. См. раздел "Обмеження рішення" в README.

## Running & Testing
- Установить зависимости: `pip install -r requirements.txt`
- Применить миграции: `alembic upgrade head`
- Запустить тесты: `python -m pytest`
- Запустить сборщик вручную: `python -m app.cli collect` (или `--backfill`)
- Запустить сервер (сервер сам поднимает и фоновый сборщик): `python run.py`
