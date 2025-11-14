# Repository Guidelines

## Project Structure & Module Organization
- Core app: `app.py` (Flask) with feature blueprints in `*_api.py` (e.g., `multi_timeframe_api.py`, `fibonacci_api.py`).
- Frontend: `templates/` (Jinja/HTML) and `static/` (CSS/JS/assets).
- Scripts: server starters (`start_server.py`, `waitress_server.py`), `gunicorn.conf.py`.
- Data/config: `requirements.txt`, `supported_symbols.json`, optional DB in `bollinger_strategy.db`.
- Tests & demos: root-level `test_*.py` and `test_*.html`; historical snapshots in `versions/`.

## Build, Test, and Development Commands
- Setup (Python 3.11):
  - `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`)
  - `pip install -r requirements.txt`
- Run locally:
  - Dev: `python start_server.py --mode flask-dev`
  - Simple: `python app.py`
  - Waitress (Windows-friendly): `python waitress_server.py`
  - Gunicorn: `gunicorn -c gunicorn.conf.py app:app`
- Tests (server running on :5000):
  - Example: `python test_frontend_integration.py` or `python test_api_signals.py`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indent, 100-char soft wrap, docstrings for public functions.
- Naming: `snake_case` for functions/variables/modules, `CapWords` for classes, constants `UPPER_SNAKE`.
- Blueprints: keep API modules suffixed `_api.py`; group related routes and helpers per module.

## Testing Guidelines
- No framework enforced; tests are executable scripts `test_*.py` that hit local endpoints.
- Keep tests deterministic; mock external APIs when feasible; prefer small, fast checks.
- Naming: mirror feature under test, e.g., `test_multi_timeframe_*.py`.

## Commit & Pull Request Guidelines
- Observed history uses short subjects like `test`, `fix`, and release notes (e.g., `Release v1.3.0: ...`).
- Prefer Conventional Commits going forward: `feat:`, `fix:`, `chore:`, `docs:`, `test:`; scope optional.
- PRs should include: brief description, endpoints/files touched, repro steps, before/after notes; attach screenshots for UI pages in `templates/` when relevant; link issues.

## Security & Configuration Tips
- Environment: `FLASK_ENV`, `PORT`, DB config (`DATABASE_TYPE`, `MYSQL_*`, `SQLITE_PATH`). Default DB is SQLite.
- Do not commit secrets; logs/cache are created at runtime (`logs/`, `cache/`).
- Validate user inputs and external API responses; handle timeouts and retries.

