"""Deterministic OpenAPI operation IDs and shared error documentation."""

from __future__ import annotations

import re
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

from app.api.problem import ProblemDetail
from app.core.config.settings import Settings
from app.core.constants import PROBLEM_MEDIA_TYPE


def generate_operation_id(route: APIRoute) -> str:
    """Create deterministic IDs from HTTP method and normalized route template."""

    method = sorted(route.methods or {"GET"})[0].lower()
    path = route.path_format.strip("/").replace("{", "").replace("}", "")
    normalized_path = re.sub(r"[^a-zA-Z0-9]+", "_", path).strip("_")
    return f"{method}_{normalized_path or 'root'}"


def configure_openapi(app: FastAPI, settings: Settings) -> None:
    """Install deterministic schema generation with documented Problem Details."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = get_openapi(
            title=settings.api.title,
            version=settings.app.version,
            description=settings.api.description,
            routes=app.routes,
        )
        components = schema.setdefault("components", {})
        schemas = components.setdefault("schemas", {})
        schemas["ProblemDetail"] = ProblemDetail.model_json_schema()
        responses = components.setdefault("responses", {})
        responses["ProblemDetail"] = {
            "description": "RFC 9457-compatible application problem response.",
            "content": {
                PROBLEM_MEDIA_TYPE: {
                    "schema": {"$ref": "#/components/schemas/ProblemDetail"},
                }
            },
        }
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi
