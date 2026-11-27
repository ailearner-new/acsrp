"""Mock integrations for testing and development.

These modules provide mock implementations of external services
for use in testing, CI/CD, and development environments.
"""

from backend.app.integrations.mock.billing import MockStripe, MockBillingClient
from backend.app.integrations.mock.email import MockSendGrid, MockEmailClient
from backend.app.integrations.mock.ticketing import MockTicketingClient
from backend.app.integrations.mock.auth import MockAuthClient

__all__ = [
    "MockStripe",
    "MockBillingClient",
    "MockSendGrid",
    "MockEmailClient",
    "MockTicketingClient",
    "MockAuthClient",
]