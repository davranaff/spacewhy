"""OpenAPI determinism smoke tests."""

import pytest

from app.bootstrap.app_factory import create_app
from app.core.config.settings import Settings


@pytest.mark.smoke
def test_openapi_schema_is_deterministic_and_documents_problem_details(
    test_settings: Settings,
) -> None:
    """OpenAPI includes stable operation IDs and the shared problem response component."""

    app = create_app(test_settings)

    first_schema = app.openapi()
    second_schema = app.openapi()

    assert first_schema == second_schema
    assert first_schema["paths"]["/health/live"]["get"]["operationId"] == "get_health_live"
    assert "/api/v1/access/me" in first_schema["paths"]
    assert "/api/v1/identity/auth/telegram/challenges" in first_schema["paths"]
    assert "/api/v1/finance/transactions" in first_schema["paths"]
    assert "/api/v1/finance/dashboard/summary" in first_schema["paths"]
    assert "ProblemDetail" in first_schema["components"]["schemas"]
    assert "ProblemDetail" in first_schema["components"]["responses"]
