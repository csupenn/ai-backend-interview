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

## State Machine

Two orthogonal machines — the doc's evaluation status, and the system's status
gated on it.

```mermaid
stateDiagram-v2
    direction LR
    state "DesignDoc.evaluation_status" as D {
        [*] --> NOT_EVALUATED
        NOT_EVALUATED --> APPROVED: evaluate / pass
        NOT_EVALUATED --> REJECTED: evaluate / fail
        REJECTED --> NOT_EVALUATED: PUT design-doc
        APPROVED --> NOT_EVALUATED: PUT design-doc
    }
    state "System.status" as S {
        [*] --> IN_DEVELOPMENT
        IN_DEVELOPMENT --> IN_PRODUCTION: promote [doc == APPROVED]
    }
```

| From | Event | Guard | To | HTTP |
| --- | --- | --- | --- | --- |
| any doc state | `PUT /design-doc` | — | doc → `NOT-EVALUATED`, feedback cleared | 200 |
| any doc state | `POST /evaluate` | — | `APPROVED` \| `REJECTED` | 200 |
| `IN-DEVELOPMENT` | `POST /promote` | doc `APPROVED` | `IN-PRODUCTION` | 200 |
| `IN-DEVELOPMENT` | `POST /promote` | doc ≠ `APPROVED` | no change | 409 |
| — | any, unknown id | — | — | 404 |

**Invariant:** `status == IN-PRODUCTION` ⇒ `evaluation_status == APPROVED` *at
the moment of promotion* — see Current Limitations.

## API

| Method | Path                                     | Description                                  |
| ------ | ---------------------------------------- | -------------------------------------------- |
| GET    | `/health`                                | Health check → `{"status": "ok"}`            |
| POST   | `/systems`                               | Create a system with a design doc (`201`)    |
| GET    | `/systems/{system_id}`                   | Retrieve a system (`404` if unknown)         |
| PUT    | `/systems/{system_id}/design-doc`        | Replace doc content; resets evaluation (`404` if unknown) |
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
docs/
  prompts/            The prompts used to generate this implementation
  notes/              Session notes: requirements Q&A, state machine, tradeoffs
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

## Documentation

This was built as a time-boxed, AI-assisted exercise. The prompts that produced
the implementation are checked in:

| Document | Contents |
| --- | --- |
| `docs/prompts/01-project-scaffolding.md` | Pre-built scaffold (venv, FastAPI, ruff, `/health`) |
| `docs/prompts/02a-mvp-core.md` | Core MVP: create / retrieve / evaluate / promote + guard |
| `docs/prompts/02b-doc-update.md` | Follow-on: doc update path + evaluation reset |
| `docs/notes/geico-ai-coding-interview-07212026.md` | Session notes — requirements Q&A, state machine, named tradeoffs |
| `docs/notes/post-interview-hardening-plan.md` | The follow-up conformance pass, and why each hole was closed or deferred |

## Current Limitations

Deliberate MVP tradeoffs, not oversights:

- **In-memory storage only** — data is lost on restart, and system ids are
  valid only for the life of the process. A real governance platform needs
  durable storage plus an immutable audit trail of who approved what, when,
  and why.
- **Evaluation is a length-based stub**, not a real LLM call. It sits behind
  the `evaluate_design_doc()` seam so an LLM or policy engine can be swapped in
  without changing the API contract. Productionizing it would need prompt/
  version pinning for reproducible verdicts, stored rationale, human override,
  and prompt-injection defense — the doc is user-supplied text an LLM reads.
- **No authn/authz** — in particular no separation of duties between the
  author, the evaluator, and whoever promotes.
- **Editing a promoted system's doc is not blocked**, so an `IN-PRODUCTION`
  system can end up with a `NOT-EVALUATED` doc. The fix is doc versioning, with
  the approved revision pinned to the release, rather than a guard on the edit.
  Pinned by `test_editing_doc_after_promotion_leaves_stale_production_system`.
- **Double-promote succeeds idempotently** (`200`), rather than returning a
  conflict. Pinned by `test_promote_is_idempotent_when_already_in_production`.
- No database, migrations, or Docker. `services/` and `repositories/` remain
  empty scaffolding.
