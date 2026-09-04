# Guidelines for Claude Code / Agents

## Architecture & Constraints
- Decoupled architecture: CLI collector (`cli.py`), Web API (`app/api.py`), Scraper logic (`app/scraper.py`).
- SQLite database managed strictly via SQLAlchemy 2.x and Alembic migrations.
- No network calls inside unit tests (`pytest`). Use fixtures in `tests/fixtures/`.

## Running & Testing
- Run tests: `python -m pytest`
- Run CLI collector: `python cli.py collect [--backfill]`
- Run server: `python run.py`
- Run migrations: `alembic upgrade head`