"""Finance authentication adapter against the public Identity contract."""

from typing import Annotated

from fastapi import Header, Request

from app.bootstrap.container import get_container_from_app
from app.core.errors.exceptions import AuthenticationError
from app.modules.identity.public import IdentityPrincipal


async def require_finance_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> IdentityPrincipal:
    """Resolve the principal without importing Identity presentation internals."""

    if authorization is None:
        raise AuthenticationError()
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or separator != " " or not token:
        raise AuthenticationError()
    return await get_container_from_app(request.app).identity_access.principal_from_session_token(
        token
    )
