# AI Backend Interview

## Overview

Minimal FastAPI backend implementing a small MVP: managing **GEICO systems**
and their **design docs**. A system starts in development, its design doc is
evaluated by a (stubbed) LLM bot, and the system can only be promoted to
production once the doc is approved.

Storage is an in-memory dictionary and the entire implementation lives in
`app/main.py` — no database or extra architecture layers.

## Domain

- **System** — `id`, `name`, `status` (`IN-DEVELOPMENT` | `IN-PRODUCTION`),
  and a `design_doc`.
- **DesignDoc** — `content`, `evaluation_status`
  (`NOT-EVALUATED` | `APPROVED` | `REJECTED`), and `evaluation_feedback`.

**Rules**

- A new system starts `IN-DEVELOPMENT` with a `NOT-EVALUATED` doc.
- Evaluation is a deterministic stub standing in for an LLM bot: a doc with
  enough substance (≥ 50 characters) is `APPROVED`, otherwise `REJECTED`.
- Editing the design doc resets its evaluation back to `NOT-EVALUATED`.
- A system can be promoted to `IN-PRODUCTION` **only** when its doc is
  `APPROVED`; otherwise promotion returns `409`.

## API

| Method | Path                                     | Description                                  |
| ------ | ---------------------------------------- | -------------------------------------------- |
| GET    | `/health`                                | Health check → `{"status": "ok"}`            |
| POST   | `/systems`                               | Create a system with a design doc (`201`)    |
| GET    | `/systems/{system_id}`                   | Retrieve a system (`404` if unknown)         |
| PUT    | `/systems/{system_id}/design-doc`        | Replace doc content; resets evaluation       |
| POST   | `/systems/{system_id}/design-doc/evaluate` | Evaluate the doc → `APPROVED` / `REJECTED` |
| POST   | `/systems/{system_id}/promote`           | Promote to production (`409` if not approved)|

### Example

```bash
# Create a system and capture its id
SID=$(curl -s -X POST http://127.0.0.1:8000/systems \
  -H 'Content-Type: application/json' \
  -d '{"name":"Billing","design_doc_content":"This system stores and serves customer policy data with enough detail to pass evaluation."}' \
  | python3 -c 'import sys,json;print(json.load(sys.stdin)["id"])')

curl -s http://127.0.0.1:8000/systems/$SID                              # retrieve
curl -s -X POST http://127.0.0.1:8000/systems/$SID/design-doc/evaluate  # evaluate -> APPROVED
curl -s -X POST http://127.0.0.1:8000/systems/$SID/promote              # promote -> IN-PRODUCTION
```

## Project Structure

```
app/
  main.py             MVP implementation: models, enums, in-memory store, endpoints
  api/
    routes.py         /health route
  models/
    schemas.py        Pydantic schemas (scaffolding, unused by the MVP)
  services/           Empty scaffolding
  repositories/       Empty scaffolding
tests/
  test_health.py      Test for the /health endpoint
  test_systems.py     Tests for the system create/evaluate/promote flow
requirements.txt
pyproject.toml        Ruff and pytest configuration
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

The API is available at `http://127.0.0.1:8000`. Interactive docs are at
`http://127.0.0.1:8000/docs`.

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

- In-memory storage only — data is lost when the server restarts, and system
  ids are valid only for the life of the process.
- Document evaluation is a length-based stub, not a real LLM call.
- No authentication, authorization, database, migrations, or Docker.
- `services/` and `repositories/` remain empty scaffolding.
