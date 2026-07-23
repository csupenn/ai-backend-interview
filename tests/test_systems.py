from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import _systems, app

client = TestClient(app)

# A design doc long enough to pass the stub evaluator's length heuristic.
APPROVABLE_DOC = "This system stores and serves customer policy data. " * 3
SHORT_DOC = "too short"


@pytest.fixture(autouse=True)
def clear_store() -> Iterator[None]:
    _systems.clear()
    yield
    _systems.clear()


def _create_system(name: str = "Billing", content: str = APPROVABLE_DOC) -> dict:
    response = client.post(
        "/systems",
        json={"name": name, "design_doc_content": content},
    )
    assert response.status_code == 201
    return response.json()


def test_create_system_starts_in_development_and_not_evaluated() -> None:
    system = _create_system()

    assert system["id"]
    assert system["name"] == "Billing"
    assert system["status"] == "IN-DEVELOPMENT"
    assert system["design_doc"]["evaluation_status"] == "NOT-EVALUATED"
    assert system["design_doc"]["evaluation_feedback"] is None


def test_get_system_returns_created_system() -> None:
    created = _create_system()

    response = client.get(f"/systems/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("get", "/systems/does-not-exist", None),
        ("put", "/systems/does-not-exist/design-doc", {"content": "anything"}),
        ("post", "/systems/does-not-exist/design-doc/evaluate", None),
        ("post", "/systems/does-not-exist/promote", None),
    ],
)
def test_unknown_system_returns_404(method: str, path: str, body: dict | None) -> None:
    response = client.request(method.upper(), path, json=body)

    assert response.status_code == 404


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "design_doc_content": APPROVABLE_DOC},
        {"name": "Billing", "design_doc_content": ""},
        {"name": "Billing"},
    ],
)
def test_create_system_rejects_invalid_payload(payload: dict) -> None:
    assert client.post("/systems", json=payload).status_code == 422


def test_evaluate_approves_substantial_doc() -> None:
    created = _create_system(content=APPROVABLE_DOC)

    response = client.post(f"/systems/{created['id']}/design-doc/evaluate")

    assert response.status_code == 200
    doc = response.json()["design_doc"]
    assert doc["evaluation_status"] == "APPROVED"
    assert doc["evaluation_feedback"]


def test_evaluate_rejects_short_doc() -> None:
    created = _create_system(content=SHORT_DOC)

    response = client.post(f"/systems/{created['id']}/design-doc/evaluate")

    assert response.status_code == 200
    doc = response.json()["design_doc"]
    assert doc["evaluation_status"] == "REJECTED"
    assert doc["evaluation_feedback"]


def test_promote_succeeds_after_approval() -> None:
    created = _create_system(content=APPROVABLE_DOC)
    client.post(f"/systems/{created['id']}/design-doc/evaluate")

    response = client.post(f"/systems/{created['id']}/promote")

    assert response.status_code == 200
    assert response.json()["status"] == "IN-PRODUCTION"


def test_promote_blocked_without_approval() -> None:
    created = _create_system(content=APPROVABLE_DOC)

    response = client.post(f"/systems/{created['id']}/promote")

    assert response.status_code == 409
    # System remains in development.
    assert client.get(f"/systems/{created['id']}").json()["status"] == "IN-DEVELOPMENT"


def test_promote_blocked_after_rejection() -> None:
    created = _create_system(content=SHORT_DOC)
    client.post(f"/systems/{created['id']}/design-doc/evaluate")

    response = client.post(f"/systems/{created['id']}/promote")

    assert response.status_code == 409


def test_updating_doc_resets_evaluation_and_reblocks_promotion() -> None:
    created = _create_system(content=APPROVABLE_DOC)
    client.post(f"/systems/{created['id']}/design-doc/evaluate")

    response = client.put(
        f"/systems/{created['id']}/design-doc",
        json={"content": "A freshly rewritten design document with more content."},
    )

    assert response.status_code == 200
    doc = response.json()["design_doc"]
    assert doc["evaluation_status"] == "NOT-EVALUATED"
    assert doc["evaluation_feedback"] is None
    # A stale approval must not survive an edit.
    assert client.post(f"/systems/{created['id']}/promote").status_code == 409


def test_rejected_doc_can_be_updated_reevaluated_and_promoted() -> None:
    """The full recovery path: rejection is not a dead end."""
    created = _create_system(content=SHORT_DOC)
    sid = created["id"]

    assert (
        client.post(f"/systems/{sid}/design-doc/evaluate").json()["design_doc"]["evaluation_status"]
        == "REJECTED"
    )
    assert client.post(f"/systems/{sid}/promote").status_code == 409

    client.put(f"/systems/{sid}/design-doc", json={"content": APPROVABLE_DOC})
    approved = client.post(f"/systems/{sid}/design-doc/evaluate").json()
    assert approved["design_doc"]["evaluation_status"] == "APPROVED"

    response = client.post(f"/systems/{sid}/promote")

    assert response.status_code == 200
    assert response.json()["status"] == "IN-PRODUCTION"


# --------------------------------------------------------------------------- #
# Characterization tests: these pin *known limitations*, not desired behavior.
# See docs/notes/01-post-interview-hardening-plan.md.
# --------------------------------------------------------------------------- #
def test_promote_is_idempotent_when_already_in_production() -> None:
    created = _create_system(content=APPROVABLE_DOC)
    client.post(f"/systems/{created['id']}/design-doc/evaluate")
    client.post(f"/systems/{created['id']}/promote")

    response = client.post(f"/systems/{created['id']}/promote")

    assert response.status_code == 200
    assert response.json()["status"] == "IN-PRODUCTION"


def test_in_production_system_can_reach_rejected_doc() -> None:
    """Known limitation: a live system can hold an actively rejected doc.

    Reached by promoting, editing the doc, then re-evaluating. Worse than the
    NOT-EVALUATED case below and reached the same way — nothing but `promote`
    ever reads System.status.
    """
    created = _create_system(content=APPROVABLE_DOC)
    sid = created["id"]
    client.post(f"/systems/{sid}/design-doc/evaluate")
    client.post(f"/systems/{sid}/promote")

    client.put(f"/systems/{sid}/design-doc", json={"content": SHORT_DOC})
    response = client.post(f"/systems/{sid}/design-doc/evaluate")

    assert response.status_code == 200
    assert response.json()["status"] == "IN-PRODUCTION"
    assert response.json()["design_doc"]["evaluation_status"] == "REJECTED"


def test_promote_on_production_system_with_rejected_doc_returns_409() -> None:
    """Known limitation: promote reads the doc, never the system's status.

    So an already-promoted system is told it "cannot be promoted" once its doc
    is no longer APPROVED — the double-promote idempotency only holds while the
    doc stays approved.
    """
    created = _create_system(content=APPROVABLE_DOC)
    sid = created["id"]
    client.post(f"/systems/{sid}/design-doc/evaluate")
    client.post(f"/systems/{sid}/promote")
    client.put(f"/systems/{sid}/design-doc", json={"content": SHORT_DOC})
    client.post(f"/systems/{sid}/design-doc/evaluate")

    response = client.post(f"/systems/{sid}/promote")

    assert response.status_code == 409
    # Still in production — the 409 is about the doc, not the system.
    assert client.get(f"/systems/{sid}").json()["status"] == "IN-PRODUCTION"


def test_editing_doc_after_promotion_leaves_stale_production_system() -> None:
    """Known limitation: a promoted system can end up with an unevaluated doc.

    The real fix is design-doc versioning, pinning the approved revision to the
    release, so an edit creates a new draft instead of invalidating production.
    """
    created = _create_system(content=APPROVABLE_DOC)
    client.post(f"/systems/{created['id']}/design-doc/evaluate")
    client.post(f"/systems/{created['id']}/promote")

    response = client.put(
        f"/systems/{created['id']}/design-doc",
        json={"content": "Rewritten after the system was already promoted."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "IN-PRODUCTION"
    assert response.json()["design_doc"]["evaluation_status"] == "NOT-EVALUATED"
