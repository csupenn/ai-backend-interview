# AI Backend Interview

## Overview

Minimal FastAPI backend scaffolding, kept intentionally generic so it can be
extended quickly once a concrete backend problem is given. It currently
exposes a single `/health` endpoint and includes a working test and lint
setup.

## Project Structure

```
app/
  main.py            FastAPI app initialization and router registration
  api/
    routes.py         HTTP route definitions
  models/
    schemas.py         Pydantic request/response schemas
  services/            Business logic (empty, ready for use)
  repositories/         Data access layer (empty, ready for use)
tests/
  test_health.py       Test for the /health endpoint
requirements.txt
pyproject.toml         Ruff and pytest configuration
.env.example
```

## Environment Setup

Requires Python 3.12.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Running the API

```bash
fastapi dev app/main.py
```

The API will be available at `http://127.0.0.1:8000`. Check `GET /health` for
a `{"status": "ok"}` response.

## Running Tests

```bash
pytest
```

## Running Linting

```bash
ruff check .
ruff format .
```

## Current Limitations

* No database, persistence, or migrations
* No authentication or authorization
* No Docker or deployment configuration
* No business logic — `services/` and `repositories/` are empty scaffolding
* Single `/health` endpoint only
