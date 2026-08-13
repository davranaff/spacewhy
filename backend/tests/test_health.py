import pytest
from django.test import AsyncClient


@pytest.mark.asyncio
async def test_liveness_endpoint_is_reachable_asynchronously() -> None:
    response = await AsyncClient().get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
