"""Identity bearer authentication at the HTTP boundary."""

from typing import Annotated

from fastapi import Header, Request

from app.bootstrap.container import get_container_from_app
from app.modules.identity.domain.errors import IdentityDomainError, IdentityErrorCode
from app.modules.identity.public import IdentityPrincipal


async def require_identity_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> IdentityPrincipal:
    if authorization is None:
        raise IdentityDomainError(IdentityErrorCode.SESSION_INVALID)
    scheme, separator, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or separator != " " or not token:
        raise IdentityDomainError(IdentityErrorCode.SESSION_INVALID)
    container = get_container_from_app(request.app)
    return await container.identity.service.principal_from_session_token(token)
