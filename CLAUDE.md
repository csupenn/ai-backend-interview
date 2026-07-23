# AI Backend Interview

FastAPI MVP for a governance exercise: GEICO **systems** and their **design
docs**. A system starts `IN-DEVELOPMENT`, its doc is evaluated by a stubbed LLM
bot, and it can only be promoted to `IN-PRODUCTION` once the doc is `APPROVED`.

Built as a time-boxed, AI-assisted exercise. The prompts that produced the code
are checked in and are treated as the specification.

## Commands

```bash
source .venv/bin/activate
pytest -q                      # 19 tests
ruff check . && ruff format .
fastapi dev app/main.py        # http://127.0.0.1:8000
```

Python 3.12 required.

## Constraints

Deliberate scope limits — do not lift these without being asked:

- All implementation stays in `app/main.py`.
- In-memory `dict` for storage. No database, migrations, or ORM.
- No service layer, no repository layer. `app/services/` and
  `app/repositories/` are intentionally empty scaffolding — leave them empty.
- No authentication or authorization.
- No Docker, no CI config, no new dependencies without asking.
- `app/models/schemas.py` and `app/api/routes.py` are scaffolding from the
  original setup; only `routes.py` (`/health`) is wired up.

## Conventions

- Type hints on public functions; ruff-formatted.
- Tests in `tests/`, named `test_<behavior>`, one behavior per test.
- Status codes: `404` unknown id, `409` blocked transition, `422` validation.

## Traps — read before "fixing" these

- **Characterization tests** at the bottom of `tests/test_systems.py` pin
  *known limitations*, not desired behavior — a promoted system can hold an
  unevaluated doc, and double-promote is idempotent. They sit under a banner
  comment. Do not "fix" the behavior they assert; the reasoning is in
  `docs/notes/03-design-doc-lifecycle.md` and the README limitations.
- **`evaluate_design_doc()`** is the named seam for a real LLM evaluator. The
  name is specified by `docs/prompts/02a-mvp-core.md` — do not rename it, and
  keep the route handler as `evaluate_system_design_doc()`.
- **`docs/notes/` are dated records.** Do not edit them to reflect later
  understanding; add a new note instead.

## Where things are

| Path | Contents | Mutable? |
| --- | --- | --- |
| `docs/prompts/` | The prompts that produced the code — the spec | yes, with the code |
| `docs/notes/` | Session records and design reasoning | no — append only |
| `docs/personal-notes/` | Private working notes (gitignored) | n/a |

When the code and a prompt disagree, assume the code drifted and fix the code.
