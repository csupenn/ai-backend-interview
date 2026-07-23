Implement the FastAPI models, enums, and endpoints for the MVP below.

## Constraints

- All implementation goes in `app/main.py`. Tests in `tests/test_systems.py`.
- In-memory `dict` for storage. No database, no service/repository layers.
- Do not add: auth, logging config, doc versioning, list/pagination endpoints,
  Docker, CI, or a real LLM call.
- Do not modify any other existing file.
- Implement directly. No explanation or summary in your response.

## Problem

Each GEICO system has a status (`IN-DEVELOPMENT`, `IN-PRODUCTION`) and must have
a system design doc. The doc is evaluated by an LLM bot. A system may transition
to production iff its design doc is approved.

## Data model

```
System      id, name, status: IN-DEVELOPMENT | IN-PRODUCTION, design_doc
DesignDoc   content, evaluation_status: NOT-EVALUATED | APPROVED | REJECTED,
            evaluation_feedback: str | None
```

## State machine

| From | Event | Guard | To | HTTP |
| --- | --- | --- | --- | --- |
| any doc state | evaluate | — | `APPROVED` \| `REJECTED` + feedback | 200 |
| `IN-DEVELOPMENT` | promote | doc `APPROVED` | `IN-PRODUCTION` | 200 |
| `IN-DEVELOPMENT` | promote | doc ≠ `APPROVED` | no change | 409 |
| — | any, unknown id | — | — | 404 |

Validation failures → 422 (default Pydantic behavior is fine).

## API

```
POST /systems                              -> 201, creates with a design doc
GET  /systems/{system_id}                  -> 200
POST /systems/{system_id}/design-doc/evaluate -> 200
POST /systems/{system_id}/promote          -> 200 | 409
```

## Evaluator

Put the evaluation behind a single function:

```python
def evaluate_design_doc(content: str) -> tuple[EvaluationStatus, str]: ...
```

Deterministic placeholder standing in for the LLM bot (e.g. approve if the doc
has enough substance, else reject with feedback). Docstring must say it is a
stub behind a seam that a real LLM or policy engine swaps into unchanged.

## Tests

1. create → 201, status `IN-DEVELOPMENT`, doc `NOT-EVALUATED`
2. promote before evaluation → 409, status unchanged
3. evaluate (approving content) → promote → 200, `IN-PRODUCTION`
4. evaluate (rejecting content) → promote → 409
5. unknown id on get / evaluate / promote → 404

## Verify

Run `ruff check .` and `pytest -q`. Then print a curl sequence for the happy
path against `http://127.0.0.1:8000`.
