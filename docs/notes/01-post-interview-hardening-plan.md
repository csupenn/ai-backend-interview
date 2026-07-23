# Post-Interview Hardening Plan

_Written 2026-07-23, after the 2026-07-21 exercise. Scope: bring the delivered
artifact into full conformance with the written spec
(`docs/prompts/02a-mvp-core.md`, `02b-doc-update.md`) and the state machine in
`00-geico-ai-coding-interview-07212026.md`._

The interview deliverable was built in ~40 minutes and works. This plan is the
follow-up pass I'd have done with another hour: close the gap between what the
spec says, what the code does, and what the docs claim.

---

## Baseline (measured, not assumed)

`pytest -q` → **10 passed**. I probed the edges directly rather than reasoning
about them:

| Probe | Result |
| --- | --- |
| promote, then promote again | `200`, `200` — idempotent |
| edit design doc after promotion | `200`, system stays `IN-PRODUCTION`, doc → `NOT-EVALUATED` |
| unknown id on evaluate / promote / put-doc | `404` (all three) |
| empty `name` on create | `422` |

**Conclusion: the implementation is correct against the spec.** The 404s and
422 already work — they are simply unasserted. So this is predominantly a
test-coverage and documentation pass, not a bug-fix pass.

---

## Change 1 — Name the evaluator seam properly

`docs/prompts/02a-mvp-core.md` specifies the seam as
`evaluate_design_doc(content) -> tuple[EvaluationStatus, str]`. In
`app/main.py` that name is held by the **route handler**, so the seam itself
was demoted to a private `_evaluate_design_doc` — which reads as an internal
detail at precisely the point where the design intent is "this is the
substitution point for the real LLM bot."

```
_evaluate_design_doc()   ->  evaluate_design_doc()          # the seam, public
evaluate_design_doc()    ->  evaluate_system_design_doc()   # the route handler
```

The docstring changes from describing the stub to stating the contract: a real
LLM or policy engine substitutes here, with callers and the API contract
unchanged.

Runtime behavior is unaffected. The value is legibility — this is the function
to point at when asked "where does the real evaluator go?"

Note the direction of the fix: the prompt is the spec and the code drifted from
it, so the prompt is not edited.

## Change 2 — Close the four test gaps

| Spec item | Current state |
| --- | --- |
| `02a` #5 — 404 on get / evaluate / promote | only **get** is covered |
| `02b` #6 — reject → update → re-evaluate → approve → promote | **missing entirely** |
| `02b` #7 — after update, promote → 409 | reset is asserted; the 409 half is not |
| `02b` table — 404 on `PUT /design-doc` | missing |

The second row is the one that matters. The rejection-recovery round trip is
the exact requirement the interviewer had to prompt me to notice during the
session, and it is the only path in the state machine with no end-to-end test.
`test_updating_doc_resets_evaluation` starts from an *approved* doc, so it is
really half of #7 wearing #6's name.

Planned:

- one parametrized 404 test across all four id-taking endpoints
- the full reject → update → re-evaluate → approve → promote flow
- extend the reset test to assert the follow-on `409`
- one `422` case for empty name / content

## Change 3 — Make the two known holes executable

The README asserts both of these behaviors; nothing currently pins them. Adding
characterization tests, named so they read as limitations rather than
endorsements:

- `test_promote_is_idempotent_when_already_in_production` → `200`
- `test_editing_doc_after_promotion_leaves_stale_production_system` →
  `IN-PRODUCTION` with a `NOT-EVALUATED` doc

**Why test the second rather than fix it.** Guarding the edit with a `409`
would contradict the fix I actually believe in — version the design doc and pin
the approved revision to the release, so an edit creates a new draft instead of
invalidating production — and it is scope neither prompt asked for. Locking in
behavior I have called a hole is uncomfortable, but it is the honest option: it
makes the gap executable and visible in a test name instead of buried in prose,
and it fails loudly if someone later changes the behavior by accident.

In a real governance platform this hole is not acceptable, because an
`IN-PRODUCTION` system whose doc is `NOT-EVALUATED` breaks the very invariant
the platform exists to enforce. It is deferred here, not dismissed.

## Change 4 — Reflect it in the docs

- **README** — add `404` to the `PUT /design-doc` row of the API table; the
  double-promote and stale-edit limitation bullets cite the tests that now
  enforce them.
- **Session notes** — the state-machine table's `IN-PRODUCTION | promote` row
  changes from *undecided* to `200` (a decision, not an accident); the "Known
  holes" section notes both are characterization-tested.
- **Prompts** — unchanged. They are the spec the code is being brought back
  into line with.

---

## Explicitly out of scope

Unchanged from the interview's deferred list: persistence, audit trail,
authn/authz and separation of duties, design-doc versioning, and a real LLM
evaluator. Each is named in the README's limitations with the reasoning.

## Acceptance

`ruff check .` clean, `pytest -q` green, every row of the state-machine
transition table covered by at least one test, and no claim in the README that
is not backed by a test.

_Estimated size: ~2 lines of application code, ~6 tests, ~5 documentation
lines._
