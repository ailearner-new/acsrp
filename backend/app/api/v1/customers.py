"""Customer API routes."""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.app.core.middleware import require_role
from backend.app.repositories.customer import CustomerRepository
from backend.app.schemas.customer import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    CustomerResponse,
    CustomerListResponse,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.post(
    "/",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
)
async def create_customer(
    request: CustomerCreateRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER")),
) -> CustomerResponse:
    """
    Create a new customer in the system.

    Requires appropriate role permissions.
    """
    customer_repo = CustomerRepository()

    # Check if customer with email already exists for this tenant
    tenant_id = current_user.get("tenant_id")
    if tenant_id and current_user.get("role") != "SUPER_ADMIN":
        existing = await customer_repo.get_by_email(tenant_id, request.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Customer with this email already exists",
            )

    from backend.app.models.customer import Customer

    customer = Customer(
        tenant_id=tenant_id or UUID("00000000-0000-0000-0000-000000000000"),
        external_id=request.external_id,
        email=request.email,
        full_name=request.full_name,
        organization=request.organization,
        tier=request.tier,
        metadata=request.metadata,
    )

    await customer_repo.create(customer)

    return CustomerResponse(
        id=customer.id,
        tenant_id=customer.tenant_id,
        external_id=customer.external_id,
        email=customer.email,
        full_name=customer.full_name,
        organization=customer.organization,
        tier=customer.tier,
        metadata=customer.metadata,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer details",
)
async def get_customer(
    customer_id: UUID,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> CustomerResponse:
    """
    Get detailed information about a specific customer.
    """
    customer_repo = CustomerRepository()
    customer = await customer_repo.get_by_id(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    return CustomerResponse(
        id=customer.id,
        tenant_id=customer.tenant_id,
        external_id=customer.external_id,
        email=customer.email,
        full_name=customer.full_name,
        organization=customer.organization,
        tier=customer.tier,
        metadata=customer.metadata,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer details",
)
async def update_customer(
    customer_id: UUID,
    request: CustomerUpdateRequest,
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER")),
) -> CustomerResponse:
    """
    Update customer information.

    Only provided fields will be updated.
    """
    customer_repo = CustomerRepository()
    customer = await customer_repo.get_by_id(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found",
        )

    # Update fields if provided
    if request.external_id is not None:
        customer.external_id = request.external_id
    if request.full_name is not None:
        customer.full_name = request.full_name
    if request.organization is not None:
        customer.organization = request.organization
    if request.tier is not None:
        customer.tier = request.tier
    if request.metadata is not None:
        customer.metadata = request.metadata

    await customer_repo.update(customer_id, **request.model_dump(exclude_unset=True))

    # Refresh customer
    customer = await customer_repo.get_by_id(customer_id)

    return CustomerResponse(
        id=customer.id,
        tenant_id=customer.tenant_id,
        external_id=customer.external_id,
        email=customer.email,
        full_name=customer.full_name,
        organization=customer.organization,
        tier=customer.tier,
        metadata=customer.metadata,
        created_at=customer.created_at,
        updated_at=customer.updated_at,
    )


@router.get(
    "/",
    response_model=CustomerListResponse,
    summary="List customers with filtering and pagination",
)
async def list_customers(
    email: Optional[str] = Query(None, description="Filter by email (partial match)"),
    tier: Optional[str] = Query(None, description="Filter by tier"),
    organization: Optional[str] = Query(None, description="Filter by organization"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_role("SUPER_ADMIN", "TENANT_ADMIN", "SUPPORT_MANAGER", "TIER1_AGENT", "TIER2_ENGINEER", "READ_ONLY")),
) -> CustomerListResponse:
    """
    List customers with optional filtering and pagination.

    Supports filtering by email, tier, and organization.
    """
    customer_repo = CustomerRepository()

    filters = {}
    if email:
        filters["email"] = email
    if tier:
        filters["tier"] = tier
    if organization:
        filters["organization"] = organization

    customers, total = await customer_repo.list_customers(filters, limit=limit, offset=offset)

    return CustomerListResponse(
        customers=[
            CustomerResponse(
                id=c.id,
                tenant_id=c.tenant_id,
                external_id=c.external_id,
                email=c.email,
                full_name=c.full_name,
                organization=c.organization,
                tier=c.tier,
                metadata=c.metadata,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in customers
        ],
        total=total,
        limit=limit,
        offset=offset,
    )