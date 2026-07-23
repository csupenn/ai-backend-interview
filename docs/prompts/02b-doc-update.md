Follow-on to `02a-mvp-core.md`. Same constraints: everything in `app/main.py`,
in-memory dict, no new layers, no other files touched, no explanation.

## Gap

A rejected design doc has no way to be fixed and re-evaluated. Add the update
path.

## Add

```
PUT /systems/{system_id}/design-doc   -> 200 | 404
```

Body: `{"content": "..."}` (non-empty).

Replacing the content **resets the evaluation**: `evaluation_status` →
`NOT-EVALUATED`, `evaluation_feedback` → `None`. A stale approval must never
survive an edit.

| From | Event | Guard | To | HTTP |
| --- | --- | --- | --- | --- |
| any doc state, any system status | `PUT /design-doc` | — | `NOT-EVALUATED`, feedback cleared | 200 |
| — | unknown id | — | — | 404 |

## Tests

6. reject → update doc → re-evaluate → approve → promote → `IN-PRODUCTION`
7. approve → update doc → doc is back to `NOT-EVALUATED`, and promote → 409

## Verify

`ruff check .` and `pytest -q`.
