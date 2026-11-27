"""Customer API schemas."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr
from typing import Literal

from backend.app.models.enums import CustomerTier


class CustomerCreateRequest(BaseModel):
    """Request schema for creating a customer."""

    external_id: Optional[str] = None
    email: EmailStr
    full_name: Optional[str] = None
    organization: Optional[str] = None
    tier: CustomerTier = CustomerTier.STANDARD
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CustomerUpdateRequest(BaseModel):
    """Request schema for updating a customer."""

    external_id: Optional[str] = None
    full_name: Optional[str] = None
    organization: Optional[str] = None
    tier: Optional[CustomerTier] = None
    metadata: Optional[Dict[str, Any]] = None


class CustomerResponse(BaseModel):
    """Response schema for customer details."""

    id: UUID
    tenant_id: UUID
    external_id: Optional[str] = None
    email: EmailStr
    full_name: Optional[str] = None
    organization: Optional[str] = None
    tier: CustomerTier
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CustomerListResponse(BaseModel):
    """Response schema for paginated customer list."""

    customers: List[CustomerResponse]
    total: int
    limit: int
    offset: int