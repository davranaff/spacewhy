"""RFC 9457-compatible Problem Details response contract."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from starlette.responses import JSONResponse

from app.core.constants import PROBLEM_MEDIA_TYPE


class ProblemDetail(BaseModel):
    """Problem Details plus stable application extension members."""

    model_config = ConfigDict(extra="forbid")

    type: str = Field(description="Stable problem type URI.")
    title: str = Field(description="Human-readable summary of the problem type.")
    status: int = Field(ge=400, le=599)
    detail: str = Field(description="Safe explanation for the client.")
    instance: str = Field(description="Request path that produced the problem.")
    code: str = Field(description="Stable machine-readable error code.")
    request_id: str = Field(description="Opaque request correlation identifier.")


def problem_response(problem: ProblemDetail) -> JSONResponse:
    """Render a consistent application/problem+json response."""

    return JSONResponse(
        content=problem.model_dump(mode="json"),
        media_type=PROBLEM_MEDIA_TYPE,
        status_code=problem.status,
    )
