"""Mock Stripe/Billing integration for testing."""

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class Transaction:
    """Mock transaction record."""
    transaction_id: str
    customer_id: str
    amount: float
    type: str  # 'charge', 'refund', 'subscription'
    status: str  # 'success', 'failed', 'pending'
    description: str
    created_at: str


class MockStripe:
    """Mock Stripe API client for testing."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize mock Stripe client."""
        self.api_key = api_key or "sk_test_mock"
        self.transactions: Dict[str, Transaction] = {}

    async def refund(
        self,
        charge_id: str,
        amount: float,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Initiate a refund.

        Args:
            charge_id: Original charge ID
            amount: Refund amount
            reason: Refund reason
            metadata: Optional metadata

        Returns:
            Refund result
        """
        transaction_id = f"txn_{uuid.uuid4().hex[:12]}"

        transaction = Transaction(
            transaction_id=transaction_id,
            customer_id=metadata.get("customer_id", "unknown") if metadata else "unknown",
            amount=amount,
            type="refund",
            status="success",
            description=reason,
            created_at=datetime.utcnow().isoformat() + "Z",
        )
        self.transactions[transaction_id] = transaction

        return {
            "id": transaction_id,
            "object": "refund",
            "amount": int(amount * 100),  # cents
            "currency": "usd",
            "status": "succeeded",
            "reason": reason,
            "metadata": metadata or {},
        }

    async def charge(
        self,
        customer_id: str,
        amount: float,
        description: str,
        payment_method: str = "card",
    ) -> Dict[str, Any]:
        """Create a charge.

        Args:
            customer_id: Customer ID
            amount: Charge amount
            description: Charge description
            payment_method: Payment method type

        Returns:
            Charge result
        """
        transaction_id = f"ch_{uuid.uuid4().hex[:12]}"

        return {
            "id": transaction_id,
            "object": "charge",
            "amount": int(amount * 100),
            "currency": "usd",
            "customer": customer_id,
            "status": "succeeded",
            "description": description,
        }

    async def create_subscription(
        self,
        customer_id: str,
        plan_id: str,
        trial_period_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a subscription.

        Args:
            customer_id: Customer ID
            plan_id: Plan identifier
            trial_period_days: Optional trial period

        Returns:
            Subscription result
        """
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"

        return {
            "id": subscription_id,
            "object": "subscription",
            "customer": customer_id,
            "items": {"data": [{"plan": {"id": plan_id}}]},
            "status": "active",
            "current_period_start": int(datetime.utcnow().timestamp()),
            "current_period_end": int(datetime.utcnow().timestamp()) + 30 * 24 * 60 * 60,
        }

    async def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Get subscription details."""
        return {
            "id": subscription_id,
            "object": "subscription",
            "status": "active",
            "plan": {"id": "professional"},
        }

    def list_transactions(self, customer_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List transactions for a customer."""
        transactions = list(self.transactions.values())
        if customer_id:
            transactions = [t for t in transactions if t.customer_id == customer_id]
        return [vars(t) for t in transactions]


class MockBillingClient:
    """Higher-level billing client with convenience methods."""

    def __init__(self, stripe_client: Optional[MockStripe] = None):
        """Initialize billing client."""
        self.stripe = stripe_client or MockStripe()

    async def issue_refund(
        self,
        ticket_id: str,
        customer_id: str,
        amount: float,
        reason: str,
    ) -> Dict[str, Any]:
        """Issue a refund for a support ticket.

        Args:
            ticket_id: Support ticket ID
            customer_id: Customer ID
            amount: Refund amount
            reason: Refund reason

        Returns:
            Refund result
        """
        metadata = {
            "ticket_id": ticket_id,
            "customer_id": customer_id,
        }

        result = await self.stripe.refund(
            charge_id=f"ch_{uuid.uuid4().hex[:12]}",
            amount=amount,
            reason=reason,
            metadata=metadata,
        )

        return {
            "status": "SUCCESS",
            "transaction_id": result["id"],
            "amount": amount,
            "ticket_id": ticket_id,
            "customer_id": customer_id,
        }

    async def update_subscription(
        self,
        customer_id: str,
        new_plan: str,
        effective_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update customer subscription.

        Args:
            customer_id: Customer ID
            new_plan: New plan name
            effective_date: When change takes effect

        Returns:
            Update result
        """
        result = await self.stripe.create_subscription(
            customer_id=customer_id,
            plan_id=new_plan,
        )

        return {
            "status": "SUCCESS",
            "subscription_id": result["id"],
            "customer_id": customer_id,
            "new_plan": new_plan,
        }

    async def get_customer_balance(self, customer_id: str) -> Dict[str, Any]:
        """Get customer billing balance.

        Args:
            customer_id: Customer ID

        Returns:
            Balance details
        """
        transactions = self.stripe.list_transactions(customer_id)

        credit = sum(t["amount"] for t in transactions if t["type"] == "refund")
        debits = sum(t["amount"] for t in transactions if t["type"] == "charge")

        return {
            "customer_id": customer_id,
            "balance": credit - debits,
            "credit": credit,
            "debits": debits,
            "transactions_count": len(transactions),
        }