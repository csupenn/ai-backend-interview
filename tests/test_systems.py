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


def test_get_unknown_system_returns_404() -> None:
    response = client.get("/systems/does-not-exist")

    assert response.status_code == 404


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


def test_updating_doc_resets_evaluation() -> None:
    created = _create_system(content=APPROVABLE_DOC)
    client.post(f"/systems/{created['id']}/design-doc/evaluate")

    response = client.put(
        f"/systems/{created['id']}/design-doc",
        json={"content": "A freshly rewritten design document with more content."},
    )

    assert response.status_code == 200
    assert response.json()["design_doc"]["evaluation_status"] == "NOT-EVALUATED"
