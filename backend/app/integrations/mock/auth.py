"""Mock authentication provider integration for testing."""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class User:
    """Mock user record."""
    user_id: str
    email: str
    name: str
    role: str
    active: bool = True
    created_at: str = ""


class MockAuthClient:
    """Mock authentication provider client (Keycloak/Cognito-style)."""

    def __init__(self, issuer: Optional[str] = None):
        """Initialize mock auth client."""
        self.issuer = issuer or "https://auth.example.com"
        self.users: Dict[str, User] = {}
        self.tokens: Dict[str, Dict[str, Any]] = {}

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        user = self.users.get(user_id)
        if not user:
            return None
        return {
            "user_id": user.user_id,
            "email": user.email,
            "name": user.name,
            "role": user.role,
            "active": user.active,
        }

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email."""
        for user in self.users.values():
            if user.email == email:
                return {
                    "user_id": user.user_id,
                    "email": user.email,
                    "name": user.name,
                    "role": user.role,
                    "active": user.active,
                }
        return None

    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify a JWT token."""
        token_data = self.tokens.get(token)

        if not token_data:
            return {
                "valid": False,
                "error": "Token not found",
            }

        if token_data.get("expires_at", 0) < datetime.utcnow().timestamp():
            return {
                "valid": False,
                "error": "Token expired",
            }

        return {
            "valid": True,
            "user_id": token_data.get("user_id"),
            "email": token_data.get("email"),
            "role": token_data.get("role"),
            "tenant_id": token_data.get("tenant_id"),
            "scopes": token_data.get("scopes", []),
        }

    async def generate_token(
        self,
        user_id: str,
        tenant_id: Optional[str] = None,
        role: Optional[str] = None,
        scopes: Optional[List[str]] = None,
        expires_in: int = 3600,
    ) -> Dict[str, Any]:
        """Generate a JWT token for a user.

        Args:
            user_id: User ID
            tenant_id: Optional tenant ID
            role: User role
            scopes: Token scopes
            expires_in: Token expiration in seconds

        Returns:
            Token data
        """
        user = self.users.get(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        token_id = str(uuid.uuid4())
        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        token_data = {
            "user_id": user_id,
            "email": user.email,
            "role": role or user.role,
            "tenant_id": tenant_id,
            "scopes": scopes or ["read", "write"],
            "expires_at": expires_at.timestamp(),
            "iat": datetime.utcnow().timestamp(),
        }
        self.tokens[token_id] = token_data

        return {
            "access_token": token_id,
            "token_type": "Bearer",
            "expires_in": expires_in,
            "expires_at": expires_at.isoformat() + "Z",
        }

    async def introspect_token(self, token: str) -> Dict[str, Any]:
        """Introspect a token (OAuth2 introspection endpoint)."""
        token_data = self.tokens.get(token)

        if not token_data:
            return {
                "active": False,
            }

        return {
            "active": True,
            "user_id": token_data.get("user_id"),
            "username": token_data.get("email"),
            "scope": " ".join(token_data.get("scopes", [])),
            "client_id": "clouddesk-client",
            "iss": self.issuer,
            "sub": token_data.get("user_id"),
            "aud": "clouddesk-api",
            "exp": int(token_data.get("expires_at")),
            "iat": int(token_data.get("iat")),
        }

    def add_user(self, user: User) -> None:
        """Add a user to the mock store."""
        user.created_at = user.created_at or datetime.utcnow().isoformat() + "Z"
        self.users[user.user_id] = user

    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens and return count removed."""
        now = datetime.utcnow().timestamp()
        expired = [t for t, d in self.tokens.items() if d.get("expires_at", 0) < now]
        for t in expired:
            del self.tokens[t]
        return len(expired)