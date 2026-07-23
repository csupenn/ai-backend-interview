from enum import StrEnum
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.api.routes import router

app = FastAPI(title="AI Backend Interview")

app.include_router(router)


# --------------------------------------------------------------------------- #
# Enums
# --------------------------------------------------------------------------- #
class SystemStatus(StrEnum):
    IN_DEVELOPMENT = "IN-DEVELOPMENT"
    IN_PRODUCTION = "IN-PRODUCTION"


class EvaluationStatus(StrEnum):
    NOT_EVALUATED = "NOT-EVALUATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class DesignDoc(BaseModel):
    content: str
    evaluation_status: EvaluationStatus = EvaluationStatus.NOT_EVALUATED
    evaluation_feedback: str | None = None


class System(BaseModel):
    id: str
    name: str
    status: SystemStatus = SystemStatus.IN_DEVELOPMENT
    design_doc: DesignDoc


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class CreateSystemRequest(BaseModel):
    name: str = Field(min_length=1)
    design_doc_content: str = Field(min_length=1)


class UpdateDesignDocRequest(BaseModel):
    content: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# In-memory storage
# --------------------------------------------------------------------------- #
_systems: dict[str, System] = {}

# Minimum content length for a design doc to be approved by the stub evaluator.
_MIN_APPROVED_DOC_LENGTH = 50


def _get_system_or_404(system_id: str) -> System:
    system = _systems.get(system_id)
    if system is None:
        raise HTTPException(status_code=404, detail="System not found")
    return system


def evaluate_design_doc(content: str) -> tuple[EvaluationStatus, str]:
    """Seam for the LLM bot that evaluates a design doc.

    A real LLM or policy engine substitutes here; callers and the API contract
    are unchanged. The implementation below is a deterministic stub so the flow
    stays testable without external dependencies: a doc with enough substance
    is approved, otherwise it is rejected with feedback.
    """
    if len(content.strip()) >= _MIN_APPROVED_DOC_LENGTH:
        return EvaluationStatus.APPROVED, "Design doc has sufficient detail."
    return (
        EvaluationStatus.REJECTED,
        "Design doc is too short; add more detail before evaluation.",
    )


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@app.post("/systems", response_model=System, status_code=201)
def create_system(request: CreateSystemRequest) -> System:
    system = System(
        id=str(uuid4()),
        name=request.name,
        design_doc=DesignDoc(content=request.design_doc_content),
    )
    _systems[system.id] = system
    return system


@app.get("/systems/{system_id}", response_model=System)
def get_system(system_id: str) -> System:
    return _get_system_or_404(system_id)


@app.put("/systems/{system_id}/design-doc", response_model=System)
def update_design_doc(system_id: str, request: UpdateDesignDocRequest) -> System:
    system = _get_system_or_404(system_id)
    # Editing the doc invalidates any prior evaluation.
    system.design_doc = DesignDoc(content=request.content)
    return system


@app.post("/systems/{system_id}/design-doc/evaluate", response_model=System)
def evaluate_system_design_doc(system_id: str) -> System:
    system = _get_system_or_404(system_id)
    status, feedback = evaluate_design_doc(system.design_doc.content)
    system.design_doc.evaluation_status = status
    system.design_doc.evaluation_feedback = feedback
    return system


@app.post("/systems/{system_id}/promote", response_model=System)
def promote_system(system_id: str) -> System:
    system = _get_system_or_404(system_id)
    if system.design_doc.evaluation_status != EvaluationStatus.APPROVED:
        raise HTTPException(
            status_code=409,
            detail="System cannot be promoted until its design doc is APPROVED.",
        )
    system.status = SystemStatus.IN_PRODUCTION
    return system
