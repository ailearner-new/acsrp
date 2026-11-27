"""Request ID, authentication, rate limiting, and audit middleware."""

import json
import time
import uuid
from contextvars import ContextVar
from datetime import datetime, timedelta
from typing import Optional, Tuple

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


# =====================================================================
# Rate Limiting
# =====================================================================


def parse_rate_limit(rate_limit: str) -> Tuple[int, int]:
    """Parse rate limit string like '60/minute' into (requests, window_seconds)."""
    parts = rate_limit.split("/")
    if len(parts) != 2:
        return 60, 60  # default: 60 requests per minute
    try:
        requests = int(parts[0])
    except ValueError:
        requests = 60
    window_str = parts[1].lower()
    if window_str in ("second", "seconds"):
        window = 1
    elif window_str in ("minute", "minutes"):
        window = 60
    elif window_str in ("hour", "hours"):
        window = 3600
    elif window_str in ("day", "days"):
        window = 86400
    else:
        window = 60
    return requests, window


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces rate limits using Redis."""

    def __init__(self, app, redis_url: str = "", default_limit: str = "60/minute"):
        super().__init__(app)
        self.redis_url = redis_url
        self.default_limit = default_limit
        self._redis: Optional[redis.Redis] = None

    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis client."""
        if self._redis is None:
            import redis.asyncio as redis
            self._redis = redis.from_url(self.redis_url, decode_responses=True)
        return self._redis

    async def _get_limit_for_request(self, request: Request) -> Tuple[int, int]:
        """Determine rate limit based on user role."""
        from backend.app.core.config import settings

        user = getattr(request.state, "user", None)
        if user:
            role = user.get("role", "").upper()
            if "ADMIN" in role:
                return parse_rate_limit(settings.rate_limit_admin)
            return parse_rate_limit(settings.rate_limit_authenticated)
        return parse_rate_limit(settings.rate_limit_default)

    def _get_client_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting (user ID or IP)."""
        user = getattr(request.state, "user", None)
        if user and user.get("sub"):
            return f"user:{user['sub']}"
        # Fallback to IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"ip:{ip}"

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip rate limiting for health and docs
        path = request.url.path
        if path in ["/api/v1/health", "/docs", "/openapi.json", "/"]:
            return await call_next(request)

        try:
            redis_client = await self._get_redis()
            identifier = self._get_client_identifier(request)
            requests, window = await self._get_limit_for_request(request)

            # Use sliding window with Redis sorted set
            now = time.time()
            window_start = now - window
            key = f"ratelimit:{identifier}"

            pipe = redis_client.pipeline()
            # Remove expired entries
            pipe.zremrangebyscore(key, 0, window_start)
            # Count current requests
            pipe.zcard(key)
            # Add current request
            pipe.zadd(key, {str(now): now})
            # Set expiry
            pipe.expire(key, window + 1)
            results = await pipe.execute()

            current_count = results[1] + 1  # +1 for the request we just added

            if current_count > requests:
                # Rate limited
                retry_after = window
                return JSONResponse(
                    status_code=429,
                    content={
                        "type": "https://api.clouddesk.io/errors/rate-limited",
                        "title": "Rate Limit Exceeded",
                        "status": 429,
                        "detail": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                        "instance": str(request.url),
                    },
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + window)),
                    },
                )

            # Success - add rate limit headers
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(requests)
            response.headers["X-RateLimit-Remaining"] = str(max(0, requests - current_count))
            response.headers["X-RateLimit-Reset"] = str(int(now + window))
            return response

        except Exception:
            # If Redis is unavailable, fail open (allow request)
            return await call_next(request)


# =====================================================================
# Audit Logging
# =====================================================================


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware that logs audit trails for all requests."""

    def __init__(self, app):
        super().__init__(app)
        from backend.app.core.config import settings
        self.excluded_paths = {
            "/api/v1/health",
            "/docs",
            "/openapi.json",
            "/",
        }

    def _should_audit(self, path: str) -> bool:
        """Check if path should be audited."""
        return path not in self.excluded_paths

    def _get_user_info(self, request: Request) -> dict:
        """Extract user information from request."""
        user = getattr(request.state, "user", None)
        if user:
            return {
                "user_id": user.get("sub"),
                "role": user.get("role"),
            }
        return {"user_id": None, "role": None}

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address."""
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        if not self._should_audit(path):
            return await call_next(request)

        request_id = get_request_id()
        start_time = time.perf_counter()
        user_info = self._get_user_info(request)
        client_ip = self._get_client_ip(request)
        method = request.method

        # Log request audit entry
        from backend.app.core.logging import get_logger
        audit_logger = get_logger("audit")

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log successful response
            audit_logger.info(
                "request_audit",
                request_id=request_id,
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
                user_id=user_info["user_id"],
                role=user_info["role"],
                client_ip=client_ip,
                event_type="response",
            )

            return response

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Log exception
            audit_logger.error(
                "request_audit_error",
                request_id=request_id,
                method=method,
                path=path,
                error_type=type(exc).__name__,
                error_message=str(exc),
                duration_ms=round(duration_ms, 2),
                user_id=user_info["user_id"],
                role=user_info["role"],
                client_ip=client_ip,
                event_type="error",
            )
            raise