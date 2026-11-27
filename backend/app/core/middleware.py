"""Request ID and authentication middleware."""

import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta

from fastapi import Request, Response, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

# Context variable to store request ID across async calls
REQUEST_ID_VAR: ContextVar[str] = ContextVar("request_id", default="")

# Context variable to store current user across async calls
CURRENT_USER_VAR: ContextVar[Optional[dict]] = ContextVar("current_user", default=None)


def get_request_id() -> str:
    """Get current request ID from context."""
    return REQUEST_ID_VAR.get()


def get_current_user() -> Optional[dict]:
    """Get current user from context."""
    return CURRENT_USER_VAR.get()


def set_current_user(user: dict):
    """Set current user in context."""
    CURRENT_USER_VAR.set(user)


# Bearer token scheme
security_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    subject: dict | str,
    expires_delta: timedelta | None = None,
    secret_key: str | None = None,
) -> str:
    """Create a JWT access token."""
    if isinstance(subject, dict):
        subject = str(subject)

    if secret_key is None:
        from backend.app.core.config import settings
        secret_key = settings.secret_key

    if expires_delta is None:
        expires_delta = timedelta(hours=1)

    expire = datetime.utcnow() + expires_delta

    to_encode = {"exp": expire, "iat": datetime.utcnow()}
    # Ensure subject is included
    if isinstance(subject, dict):
        to_encode.update(subject)
    else:
        to_encode["sub"] = subject

    encoded = jwt.encode(to_encode, secret_key, algorithm="HS256")
    return encoded


def decode_token(
    token: str,
    secret_key: str | None = None,
) -> dict:
    """Decode and verify a JWT token."""
    if secret_key is None:
        from backend.app.core.config import settings
        secret_key = settings.secret_key

    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        return payload
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Could not validate token: {str(e)}")


async def get_token_from_request(request: Request) -> Optional[str]:
    """Extract bearer token from request authorization header."""
    credentials: HTTPAuthorizationCredentials | None = await security_scheme(
        request
    )
    if credentials is None:
        return None
    if not credentials.scheme == "Bearer":
        return None
    return credentials.credentials


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that authenticates requests via JWT token."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip auth for health endpoint and static paths
        path = request.url.path
        if path in ["/api/v1/health", "/docs", "/openapi.json", "/"]:
            response = await call_next(request)
            return response

        # Extract token
        token = await get_token_from_request(request)
        if not token:
            # Set 401 response
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid authorization header"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Decode token
        try:
            payload = decode_token(token)
        except HTTPException:
            return JSONResponse(
                status_code=401,
                content={"detail": "Could not validate token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Store user info in context
        set_current_user(payload)
        request.state.user = payload

        response = await call_next(request)
        return response


class RoleRequired:
    """Dependency to require specific user roles."""

    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        user: dict = ...  # Will be injected by FastAPI dependency
    ) -> dict:
        """Check if user has required role."""
        if not user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_role = user.get("role", "")
        # Normalize role - could be string or enum
        if isinstance(user_role, str):
            role_value = user_role
        elif hasattr(user_role, 'value'):
            role_value = user_role.value
        else:
            role_value = str(user_role)

        if role_value not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Insufficient permissions. Required roles: {self.allowed_roles}"
            )

        return user


def require_role(*allowed_roles: str):
    """FastAPI dependency factory that requires specific roles."""
    return RoleRequired(list(allowed_roles))