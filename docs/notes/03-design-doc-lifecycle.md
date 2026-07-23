# Design-Doc Lifecycle: Revisions, Releases, and Drift

_2026-07-23. Prompted by a question about the MVP's known limitation: should a
system be allowed to stay `IN-PRODUCTION` while its design doc is
`NOT-EVALUATED`?_

The short answer is that the state is legitimate, the current model can't
justify it, and the reason is a modeling defect rather than a missing guard.
This note works through the defect and the model that resolves it.

Companion to [`02-llm-evaluator-design-brief.md`](02-llm-evaluator-design-brief.md),
which names design-doc versioning as a deferred item; this is that item worked
out.

---

## 1. The question

The MVP allows this sequence:

```
create → evaluate (APPROVED) → promote (IN-PRODUCTION) → PUT design-doc
                                                          ↓
                       system: IN-PRODUCTION, doc: NOT-EVALUATED
```

Pinned by `test_editing_doc_after_promotion_leaves_stale_production_system`,
documented in the README as a limitation. The question is whether it *should* be
a limitation.

It should not — but not for the reason it first appears. That state is reached
by two completely different situations:

- **An author is drafting doc updates for a planned change.** Normal, healthy,
  and constant in any real organization.
- **Production changed, and someone is retroactively updating the paperwork.**
  A governance incident — a change reached production without passing the gate.

The current model produces identical state for both. **That indistinguishability
is the defect.** The missing guard is a symptom of it.

## 2. Both obvious fixes are wrong

**Block the edit (409 on a promoted system).** This says documentation may not
be maintained after release. It is backwards: production systems are exactly the
ones whose docs need updating, because that is where drift accumulates. The rule
would enforce staleness in the name of governance.

**Auto-demote the system.** This confuses the map with the territory.
`IN-PRODUCTION` describes where software is running. Editing a Markdown file
does not change that. Auto-demotion would remove a system from production
because someone fixed a typo.

Both are attempts to preserve an invariant that was stated wrongly in the first
place.

## 3. The invariant was stated wrongly

The MVP's implied invariant:

> An `IN-PRODUCTION` system has an `APPROVED` design doc.

This is a claim about **present state**. Any edit breaks it, which forces the
design into blocking or demoting — the two bad options above.

The correct invariant:

> **Every production release was authorized by an approved revision of the
> design doc.**

This is a claim about **history**. Nothing can break it, because history does
not change. A later edit is simply irrelevant to it.

## 4. Two state machines, one coupling point

The MVP has one state machine where the domain has two:

```
Revision lifecycle
    DRAFT ──evaluate──> EVALUATED ──approve──> APPROVED ──┐  (immutable forever)
                             └────reject────> REJECTED    │
                                    (superseded by a new revision)
                                                          │
System lifecycle                                          │
    IN-DEVELOPMENT ───────────promote [approved revision]──┴──> IN-PRODUCTION
                                                                     │
                                                              DECOMMISSIONED
```

They are independent, and they meet at exactly one point: the release gate.

Because the MVP fused them into a single `evaluation_status` field, every
document event has to mean something about system status — and there is no
sensible thing for it to mean. `PUT /design-doc` is forced to either corrupt the
system's state or be blocked. Separating the machines removes the dilemma
instead of resolving it.

Note also that the revision lifecycle applies to a **revision**, not to a
document. Once a revision is approved it never changes state again. That
immutability is what makes the historical invariant hold continuously.

## 5. The model

```
DesignDoc                     # logical identity; holds no content itself
  system_id
  revisions: [Revision]       # append-only

Revision                      # immutable once approved
  id
  content, content_hash
  created_at, created_by
  change_type: EDITORIAL | MATERIAL
  change_summary
  evaluation: Evaluation | None   # evidence about THIS revision
  approval:   Approval   | None   # decision about THIS revision

System
  id, name
  status: IN-DEVELOPMENT | IN-PRODUCTION | DECOMMISSIONED
  current_release: Release | None

Release
  id
  authorized_by_revision_id   # the approved revision that gated this release
  released_at, released_by
```

Walk the original scenario against it:

1. System is `IN-PRODUCTION` via a release authorized by revision 3.
2. Author edits the doc → **revision 4** is created, `NOT-EVALUATED`.
3. The system stays `IN-PRODUCTION`, because
   `current_release.authorized_by_revision_id == 3`, and revision 3 is still
   approved and always will be.

The invariant holds continuously, with no guard anywhere in the code. The
problem is not solved so much as dissolved — there is no longer a state the
system can reach that violates anything.

## 6. Derived status

Drift becomes a computed property, not stored state:

| Derived state | Condition | Meaning |
| --- | --- | --- |
| `CURRENT` | latest revision == released revision | Documentation matches what was authorized |
| `DRAFT_AHEAD` | unapproved revision newer than released | Normal — someone is drafting |
| `APPROVED_UNRELEASED` | approved revision newer than released | A change is approved and pending deploy |
| `UNDOCUMENTED_DRIFT` | doc updated to describe production, no release in between | **Finding** — an unauthorized change shipped |

None of these gate anything. They are what a governance dashboard reports.

## 7. Four edits that look identical

Every one of these produces the same "bytes changed" event, and they demand
different responses:

| # | What actually happened | Correct handling |
| --- | --- | --- |
| 1 | Typo, formatting, clarification | Editorial revision. No re-evaluation. Release untouched. |
| 2 | Documenting a change **not yet built** | Material revision. Must be approved *before* the change ships. |
| 3 | Documenting a change **already shipped** | Unauthorized change reached production — raise a finding. |
| 4 | The original doc was factually wrong | New revision, plus possible retroactive revocation of the prior approval. |

**Row 3 is the one a governance platform exists to catch**, and the versioned
model detects it structurally rather than by inference: a material revision
exists, it describes current production, and no release was authorized between
it and its predecessor. That is a query against the release history, not a
judgment call.

**Row 4 is why approvals can never be deleted or edited.** A past decision made
on false information is itself a finding; the record needs `revoked_at` and
`superseded_by` so it can say so without erasing what was originally believed.

## 8. Change classification — a better job for the LLM

Classifying a revision as `EDITORIAL` or `MATERIAL` is a substantially better
use of a model than scoring a document's overall quality:

| Property | Doc quality scoring | Change classification |
| --- | --- | --- |
| Input | a wall of prose | a diff between two revisions |
| Question | open-ended and subjective | bounded, with a real answer |
| Rubric | hard to specify crisply | "does this alter trust boundaries, data flows, external dependencies, or data classification?" |
| Verifiable | only against human labels | the diff is right there |

The workflow: **the author declares the change type, the model checks it, and
disagreement escalates.** An author marking a material change as editorial to
skip review is exactly the abuse case worth defending against, and a cheap
second opinion catches it. It also keeps the model advisory — consistent with
the authority split argued in the
[design brief](02-llm-evaluator-design-brief.md) — since the model flags a
disagreement rather than deciding the classification itself.

This mirrors change-impact analysis in regulated design control: ISO 13485,
DO-178C, and ISO 26262 all work by classifying a change first, then letting the
classification determine how much re-verification is required. The pattern is
well-established outside software governance and transfers cleanly.

## 9. Drift is a metric, not a gate

Governance frameworks legitimately require documentation to reflect reality. But
they enforce it through **periodic attestation and measurement**, not through
transition blocking:

- **Re-attestation on a cadence** — the system owner confirms the doc still
  describes the system; the attestation is itself a dated record.
- **A drift SLA** — material revisions unreviewed for more than N days become a
  finding with an owner.
- **A reported metric** — *percentage of production systems with current,
  approved documentation.*

Blocking is the wrong instrument here because the behavior you want to change
operates on a weekly-to-quarterly cadence, not inside a single request. Gating
the request punishes the person doing the right thing (updating docs) while
doing nothing about the person who never updates them at all.

## 10. The minimal version for this repo

Full revision history is the right model and more than this MVP warrants. The
smallest change that makes the invariant correct — roughly fifteen lines — is to
snapshot the approved content at promotion time:

```python
class Release(BaseModel):
    approved_content: str          # exactly what was approved
    approved_content_hash: str
    released_at: datetime


class System(BaseModel):
    id: str
    name: str
    status: SystemStatus = SystemStatus.IN_DEVELOPMENT
    design_doc: DesignDoc          # stays mutable
    release: Release | None = None # immutable once set
```

The current doc stays mutable; the *authorization* becomes immutable. Editing a
promoted system's doc then leaves `IN-PRODUCTION` obviously correct rather than
merely tolerated, and drift is computable for free:

```python
def has_drifted(system: System) -> bool:
    return (
        system.release is not None
        and sha256(system.design_doc.content) != system.release.approved_content_hash
    )
```

That single change converts the current known hole from *unguarded mutation*
into *measurable drift* — which is what it should have been from the start.

---

## Summary

- The state `IN-PRODUCTION` + `NOT-EVALUATED` is legitimate; the model's
  inability to explain **why** it is in that state is not.
- The invariant belongs on release history, not on current document state.
- Document lifecycle and system lifecycle are separate state machines that meet
  only at the release gate.
- Approvals bind to immutable revisions, so later edits cannot invalidate them.
- Drift is measured and escalated, never gated.
- The MVP can get the invariant right with an approved-content snapshot, without
  adopting full revision history.
